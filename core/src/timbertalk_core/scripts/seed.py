"""Beispieldaten einer Zimmerei.

Aufruf: `uv run python -m timbertalk_core.scripts.seed`

Das Skript ist wiederholbar: vorhandene Datensätze werden erkannt und nicht erneut
angelegt. **Alle Preise sind Platzhalter** und als solche in `note` gekennzeichnet.
"""

from __future__ import annotations

import argparse
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from timbertalk_core.config import Settings, get_settings
from timbertalk_core.context import ActorType, ServiceContext, Source
from timbertalk_core.db.session import create_db_engine, create_session_factory
from timbertalk_core.domain.bookings.schemas import BookingCreate
from timbertalk_core.domain.bookings.service import (
    cancel_booking,
    confirm_booking,
    create_booking,
)
from timbertalk_core.domain.catalog.schemas import MaterialItemCreate, PriceCreate
from timbertalk_core.domain.catalog.service import create_material_item, create_price
from timbertalk_core.domain.company.schemas import CompanyUpsert, SettingUpsert, TaxRateCreate
from timbertalk_core.domain.company.service import create_tax_rate, set_company, set_setting
from timbertalk_core.domain.customers.schemas import CustomerCreate
from timbertalk_core.domain.customers.service import create_customer, list_customers
from timbertalk_core.domain.enums import (
    CostTypeKind,
    CustomerType,
    EmployeeRole,
    MaterialCategory,
    PriceSource,
    PriceTargetType,
    ProjectStatus,
    UsageModule,
    WorkPackageStatus,
)
from timbertalk_core.domain.people.schemas import EmployeeCreate
from timbertalk_core.domain.people.service import create_employee, list_employees
from timbertalk_core.domain.projects.schemas import (
    ProjectCreate,
    WorkPackageCreate,
    WorkPackageDependencyCreate,
)
from timbertalk_core.domain.projects.service import (
    create_dependency,
    create_project,
    create_work_package,
    list_projects,
    list_work_packages,
)
from timbertalk_core.domain.reference.schemas import (
    CostTypeCreate,
    CustomFieldDefinitionCreate,
    UnitCreate,
)
from timbertalk_core.domain.reference.service import (
    create_cost_type,
    create_custom_field,
    create_unit,
    get_cost_type_by_code,
    list_custom_fields,
    list_units,
)
from timbertalk_core.domain.usage.schemas import ModelPriceCreate, UsageRecord
from timbertalk_core.domain.usage.service import create_model_price, list_model_prices, record_usage
from timbertalk_core.errors import NotFound

PLATZHALTER = "Platzhalterpreis – vor dem Einsatz durch echte Werte ersetzen"
SEED_AKTEUR = uuid.UUID("00000000-0000-7000-8000-00000000seed".replace("seed", "0001"))
"""Fester Akteur für Seed-Daten, damit das Änderungsprotokoll sie erkennbar ausweist."""

EINHEITEN: list[tuple[str, str, int, int]] = [
    ("h", "Stunde", 2, 10),
    ("km", "Kilometer", 1, 20),
    ("m3", "Kubikmeter", 3, 30),
    ("lfm", "Laufmeter", 2, 40),
    ("m2", "Quadratmeter", 2, 50),
    ("stk", "Stück", 0, 60),
    ("kg", "Kilogramm", 2, 70),
    ("pausch", "Pauschal", 2, 80),
]

KOSTENARTEN: list[tuple[str, str, CostTypeKind, str, Decimal | None, bool, int]] = [
    ("labor_master", "Lohn Meister", CostTypeKind.LABOR, "h", Decimal("68.5000"), True, 10),
    ("labor_journeyman", "Lohn Geselle", CostTypeKind.LABOR, "h", Decimal("58.0000"), True, 20),
    ("labor_apprentice", "Lohn Azubi", CostTypeKind.LABOR, "h", Decimal("32.0000"), True, 30),
    ("travel", "Fahrtkosten", CostTypeKind.TRAVEL, "km", Decimal("0.4500"), False, 40),
    ("material_timber", "Holz", CostTypeKind.MATERIAL, "m3", None, False, 50),
    ("material_fasteners", "Verbindungsmittel", CostTypeKind.MATERIAL, "stk", None, False, 60),
    ("material_insulation", "Dämmung", CostTypeKind.MATERIAL, "m2", None, False, 70),
    ("equipment_crane", "Kran", CostTypeKind.EQUIPMENT, "h", Decimal("180.0000"), False, 80),
    ("disposal", "Entsorgung", CostTypeKind.OTHER, "pausch", Decimal("250.0000"), False, 90),
]

MATERIAL: list[tuple[str, str, str, str, str, int, int, int, str, Decimal]] = [
    (
        "KVH-60200",
        "KVH Fichte C24 60×200",
        "material_timber",
        "Fichte",
        "C24",
        60,
        200,
        5000,
        "m3",
        Decimal("489.5000"),
    ),
    (
        "KVH-80240",
        "KVH Fichte C24 80×240",
        "material_timber",
        "Fichte",
        "C24",
        80,
        240,
        5000,
        "m3",
        Decimal("512.0000"),
    ),
    (
        "BSH-100280",
        "BSH GL24h 100×280",
        "material_timber",
        "Fichte",
        "GL24h",
        100,
        280,
        12000,
        "m3",
        Decimal("845.0000"),
    ),
    (
        "DL-3050",
        "Dachlatte 30×50",
        "material_timber",
        "Fichte",
        "S10",
        30,
        50,
        4000,
        "lfm",
        Decimal("1.2500"),
    ),
]


def _kontext(session: Session) -> ServiceContext:
    """Baut den Aufrufkontext der Beispieldaten; Quelle ist `import`."""
    return ServiceContext(
        session=session,
        actor_id=SEED_AKTEUR,
        actor_type=ActorType.SYSTEM,
        source=Source.IMPORT,
    )


def _menschlicher_kontext(session: Session, mitarbeiter_id: uuid.UUID) -> ServiceContext:
    """Kontext eines Menschen; nur so lassen sich Buchungen bestätigen.

    Parameter:
        session: offene Session.
        mitarbeiter_id: Kennung des bestätigenden Mitarbeiters.
    """
    return ServiceContext(
        session=session,
        actor_id=mitarbeiter_id,
        actor_type=ActorType.USER,
        source=Source.MANUAL,
    )


def _stammdaten(ctx: ServiceContext) -> None:
    """Legt Betrieb, Einstellungen, Steuersätze, Einheiten und Kostenarten an."""
    set_company(
        ctx,
        CompanyUpsert(
            name="Zimmerei Muster GmbH",
            street="Holzweg 7",
            zip="10115",
            city="Berlin",
            country="DE",
            tax_number="11/222/33444",
            vat_id="DE123456789",
            iban="DE02120300000000202051",
            bic="BYLADEM1001",
            phone="030 1234567",
            email="info@zimmerei-muster.example",
            home_lat=Decimal("52.530000"),
            home_lon=Decimal("13.380000"),
        ),
    )
    set_setting(
        ctx,
        SettingUpsert(
            key="default_hourly_rate",
            value={"amount": "68.50", "currency": "EUR", "note": PLATZHALTER},
            label_de="Standard-Stundensatz",
        ),
    )
    set_setting(
        ctx,
        SettingUpsert(
            key="payment_terms_days",
            value={"days": 14},
            label_de="Zahlungsziel in Tagen",
        ),
    )

    vorhandene_steuersaetze = {
        (satz.code, satz.valid_from)
        for satz in (
            __import__("timbertalk_core.domain.company.service", fromlist=["list_tax_rates"])
            .list_tax_rates(ctx, limit=200)
            .items
        )
    }
    for code, prozent, bezeichnung in [
        ("19", Decimal("19"), "Umsatzsteuer 19 %"),
        ("7", Decimal("7"), "Umsatzsteuer 7 %"),
        ("0", Decimal("0"), "Steuerfrei (z. B. § 13b UStG)"),
    ]:
        if (code, date(2021, 1, 1)) in vorhandene_steuersaetze:
            continue
        create_tax_rate(
            ctx,
            TaxRateCreate(
                code=code,
                percent=prozent,
                label_de=bezeichnung,
                valid_from=date(2021, 1, 1),
            ),
        )

    vorhandene_einheiten = {einheit.code for einheit in list_units(ctx, limit=200).items}
    for code, bezeichnung, stellen, reihenfolge in EINHEITEN:
        if code in vorhandene_einheiten:
            continue
        create_unit(
            ctx,
            UnitCreate(code=code, label_de=bezeichnung, decimals=stellen, sort_order=reihenfolge),
        )

    for code, name, art, einheit, preis, lohnanteil, reihenfolge in KOSTENARTEN:
        try:
            get_cost_type_by_code(ctx, code)
            continue
        except NotFound:
            pass
        create_cost_type(
            ctx,
            CostTypeCreate(
                code=code,
                name_de=name,
                kind=art,
                default_unit_code=einheit,
                default_unit_price=preis,
                tax_rate_code="19",
                labor_share=lohnanteil,
                sort_order=reihenfolge,
            ),
        )


def _zusatzfelder(ctx: ServiceContext) -> None:
    """Zeigt am Beispiel, wie neue Zusatzfelder als Daten entstehen."""
    vorhandene = {(feld.entity_type, feld.key) for feld in list_custom_fields(ctx, limit=200).items}
    for entity_type, key, bezeichnung, datentyp, werte in [
        (
            "customers",
            "referral_source",
            "Wie hat der Kunde uns gefunden?",
            "enum",
            ["empfehlung", "internet", "messe", "stammkunde"],
        ),
        ("projects", "site_access", "Zugang zur Baustelle", "text", None),
    ]:
        if (entity_type, key) in vorhandene:
            continue
        create_custom_field(
            ctx,
            CustomFieldDefinitionCreate(
                entity_type=entity_type,
                key=key,
                label_de=bezeichnung,
                data_type=datentyp,
                enum_values=werte,
            ),
        )


def _mitarbeiter(ctx: ServiceContext) -> dict[str, uuid.UUID]:
    """Legt drei Mitarbeiter an und liefert ihre Kennungen."""
    vorhandene = {
        (person.first_name, person.last_name): person.id for person in list_employees(ctx, limit=200).items
    }
    ergebnis: dict[str, uuid.UUID] = {}
    for schluessel, vorname, nachname, rolle, kostenart in [
        ("meister", "Max", "Holzmann", EmployeeRole.MASTER, "labor_master"),
        ("geselle", "Anna", "Berger", EmployeeRole.JOURNEYMAN, "labor_journeyman"),
        ("azubi", "Tim", "Kiefer", EmployeeRole.APPRENTICE, "labor_apprentice"),
    ]:
        bekannt = vorhandene.get((vorname, nachname))
        if bekannt is not None:
            ergebnis[schluessel] = bekannt
            continue
        ergebnis[schluessel] = create_employee(
            ctx,
            EmployeeCreate(
                first_name=vorname,
                last_name=nachname,
                role=rolle,
                default_cost_type_code=kostenart,
            ),
        ).id
    return ergebnis


def _katalog(ctx: ServiceContext) -> dict[str, uuid.UUID]:
    """Legt den Materialkatalog mit Platzhalterpreisen an."""
    from timbertalk_core.domain.catalog.service import list_material_items

    vorhandene = {artikel.sku: artikel.id for artikel in list_material_items(ctx, limit=200).items}
    ergebnis: dict[str, uuid.UUID] = {}
    for sku, name, kostenart, holzart, guete, breite, hoehe, laenge, einheit, preis in MATERIAL:
        bekannt = vorhandene.get(sku)
        if bekannt is not None:
            ergebnis[sku] = bekannt
            continue
        artikel = create_material_item(
            ctx,
            MaterialItemCreate(
                sku=sku,
                name=name,
                category=MaterialCategory.TIMBER,
                unit_code=einheit,
                cost_type_code=kostenart,
                wood_species=holzart,
                grade=guete,
                width_mm=breite,
                height_mm=hoehe,
                length_mm=laenge,
            ),
        )
        create_price(
            ctx,
            PriceCreate(
                target_type=PriceTargetType.MATERIAL_ITEM,
                target_id=artikel.id,
                unit_price=preis,
                valid_from=date(2026, 1, 1),
                source=PriceSource.MANUAL,
                note=PLATZHALTER,
            ),
        )
        ergebnis[sku] = artikel.id
    return ergebnis


def _kunden(ctx: ServiceContext) -> dict[str, uuid.UUID]:
    """Legt einen Privat- und einen Gewerbekunden an."""
    vorhandene = {kunde.display_name: kunde.id for kunde in list_customers(ctx, limit=200).items}
    ergebnis: dict[str, uuid.UUID] = {}

    if "Familie Schmidt" in vorhandene:
        ergebnis["privat"] = vorhandene["Familie Schmidt"]
    else:
        ergebnis["privat"] = create_customer(
            ctx,
            CustomerCreate(
                customer_type=CustomerType.PRIVATE,
                first_name="Familie",
                last_name="Schmidt",
                street="Lindenweg 12",
                zip="14467",
                city="Potsdam",
                phone="0331 998877",
                email="familie.schmidt@example.org",
                attributes={"referral_source": "empfehlung"},
            ),
        ).id

    if "Holzbau Nord GmbH" in vorhandene:
        ergebnis["gewerbe"] = vorhandene["Holzbau Nord GmbH"]
    else:
        ergebnis["gewerbe"] = create_customer(
            ctx,
            CustomerCreate(
                customer_type=CustomerType.BUSINESS,
                company_name="Holzbau Nord GmbH",
                street="Werftstraße 3",
                zip="24103",
                city="Kiel",
                email="einkauf@holzbau-nord.example",
                vat_id="DE987654321",
                is_construction_business=True,
                attributes={"referral_source": "messe"},
            ),
        ).id
    return ergebnis


def _projekte(ctx: ServiceContext, kunden: dict[str, uuid.UUID]) -> dict[str, dict[str, uuid.UUID]]:
    """Legt zwei Projekte samt Arbeitspaketen und einer Abhängigkeit an."""
    vorhandene = {projekt.title: projekt.id for projekt in list_projects(ctx, limit=200).items}
    ergebnis: dict[str, dict[str, uuid.UUID]] = {}

    for schluessel, titel, kunde, ort, plz, stadt, status, pakete in [
        (
            "gaube",
            "Dachgaube Lindenweg",
            kunden["privat"],
            "Lindenweg 12",
            "14467",
            "Potsdam",
            ProjectStatus.ACTIVE,
            [
                ("Abbund in der Halle", Decimal("24.00"), 10, "cad://gaube/abbund"),
                ("Montage auf der Baustelle", Decimal("32.00"), 20, None),
                ("Dachdeckung vorbereiten", Decimal("16.00"), 30, None),
            ],
        ),
        (
            "carport",
            "Carport Werftstraße",
            kunden["gewerbe"],
            "Werftstraße 3",
            "24103",
            "Kiel",
            ProjectStatus.PLANNED,
            [
                ("Fundamente setzen", Decimal("12.00"), 10, None),
                ("Aufstellen und Verankern", Decimal("20.00"), 20, "cad://carport/stiele"),
            ],
        ),
    ]:
        if titel in vorhandene:
            projekt_id = vorhandene[titel]
        else:
            projekt_id = create_project(
                ctx,
                ProjectCreate(
                    customer_id=kunde,
                    title=titel,
                    status=status,
                    site_street=ort,
                    site_zip=plz,
                    site_city=stadt,
                    planned_start=date(2026, 5, 4),
                    planned_end=date(2026, 6, 12),
                    description=f"Beispielprojekt: {titel}",
                    attributes={"site_access": "Zufahrt über den Hof, Tor 2,5 m breit"},
                ),
            ).id

        bekannte_pakete = {
            paket.title: paket.id for paket in list_work_packages(ctx, project_id=projekt_id, limit=200).items
        }
        paket_ids: dict[str, uuid.UUID] = {}
        for paket_titel, stunden, reihenfolge, cad in pakete:
            if paket_titel in bekannte_pakete:
                paket_ids[paket_titel] = bekannte_pakete[paket_titel]
                continue
            paket_ids[paket_titel] = create_work_package(
                ctx,
                WorkPackageCreate(
                    project_id=projekt_id,
                    title=paket_titel,
                    status=WorkPackageStatus.PLANNED,
                    planned_start=date(2026, 5, 4),
                    planned_end=date(2026, 5, 29),
                    planned_hours=stunden,
                    sort_order=reihenfolge,
                    cad_ref=cad,
                ),
            ).id

        ergebnis[schluessel] = {"projekt": projekt_id, **paket_ids}

        # Abhängigkeit: der Abbund muss vor der Montage fertig sein.
        if schluessel == "gaube" and len(paket_ids) >= 2:
            titel_liste = [titel for titel, _, _, _ in pakete]
            from timbertalk_core.domain.projects.service import list_dependencies

            if list_dependencies(ctx, project_id=projekt_id, limit=200).total == 0:
                create_dependency(
                    ctx,
                    WorkPackageDependencyCreate(
                        predecessor_id=paket_ids[titel_liste[0]],
                        successor_id=paket_ids[titel_liste[1]],
                    ),
                )
    return ergebnis


def _buchungen(
    ctx: ServiceContext,
    human_ctx: ServiceContext,
    projekte: dict[str, dict[str, uuid.UUID]],
    mitarbeiter: dict[str, uuid.UUID],
    material: dict[str, uuid.UUID],
) -> None:
    """Legt Buchungen in allen Status an: draft, confirmed, cancelled.

    Parameter:
        ctx: Kontext der Beispieldaten (Quelle `import`).
        human_ctx: Kontext eines Menschen; nur er darf bestätigen.
        projekte: Kennungen der Projekte und ihrer Arbeitspakete.
        mitarbeiter: Kennungen der Mitarbeiter.
        material: Kennungen der Artikel.
    """
    from timbertalk_core.domain.bookings.service import list_bookings

    gaube = projekte["gaube"]
    if list_bookings(ctx, project_id=gaube["projekt"], limit=200).total > 0:
        return

    lohn_meister = get_cost_type_by_code(ctx, "labor_master").id
    holz = get_cost_type_by_code(ctx, "material_timber").id
    fahrt = get_cost_type_by_code(ctx, "travel").id
    kran = get_cost_type_by_code(ctx, "equipment_crane").id
    entsorgung = get_cost_type_by_code(ctx, "disposal").id

    # Entwurf: aus einer Sprachaufnahme übernommen, wartet auf Bestätigung.
    create_booking(
        ctx,
        BookingCreate(
            project_id=gaube["projekt"],
            work_package_id=gaube["Abbund in der Halle"],
            cost_type_id=lohn_meister,
            booking_date=date(2026, 5, 4),
            quantity=Decimal("8.50"),
            employee_id=mitarbeiter["meister"],
            description="Abbund Gaube, Kehlbalken zugeschnitten",
            details={"start_time": "07:00", "end_time": "16:00", "break_minutes": 30},
            source=Source.VOICE,
            source_ref="transkript-2026-05-04-001",
        ),
    )

    # Bestätigt: Material und Fahrt.
    material_buchung = create_booking(
        ctx,
        BookingCreate(
            project_id=gaube["projekt"],
            work_package_id=gaube["Abbund in der Halle"],
            cost_type_id=holz,
            booking_date=date(2026, 5, 4),
            quantity=Decimal("2.400"),
            material_item_id=material["KVH-60200"],
            description="KVH für Gaubenwangen",
            details={"delivery_note_ref": "LS-2026-0815"},
        ),
    )
    confirm_booking(human_ctx, material_buchung.id)

    fahrt_buchung = create_booking(
        ctx,
        BookingCreate(
            project_id=gaube["projekt"],
            cost_type_id=fahrt,
            booking_date=date(2026, 5, 5),
            quantity=Decimal("42.5"),
            description="Werkstatt zur Baustelle und zurück",
            details={
                "from_label": "Werkstatt Berlin",
                "to_label": "Baustelle Potsdam",
                "round_trip": True,
                "vehicle": "Sprinter BE-ZM 123",
            },
        ),
    )
    confirm_booking(human_ctx, fahrt_buchung.id)

    # Gerät und Pauschale.
    kran_buchung = create_booking(
        ctx,
        BookingCreate(
            project_id=gaube["projekt"],
            work_package_id=gaube["Montage auf der Baustelle"],
            cost_type_id=kran,
            booking_date=date(2026, 5, 11),
            quantity=Decimal("4.00"),
            description="Autokran für das Aufsetzen der Gaube",
            details={"equipment_name": "Autokran 30 t", "hours_or_days": "4"},
        ),
    )
    confirm_booking(human_ctx, kran_buchung.id)

    # Storniert: doppelt erfasst.
    storno = create_booking(
        ctx,
        BookingCreate(
            project_id=gaube["projekt"],
            cost_type_id=entsorgung,
            booking_date=date(2026, 5, 12),
            quantity=Decimal("1.00"),
            description="Containermiete – versehentlich doppelt erfasst",
        ),
    )
    cancel_booking(human_ctx, storno.id)


def _ki_verbrauch(ctx: ServiceContext, projekte: dict[str, dict[str, uuid.UUID]]) -> None:
    """Legt Modellpreise an und protokolliert Beispiel-Aufrufe."""
    vorhandene = {(preis.provider, preis.model) for preis in list_model_prices(ctx, limit=200).items}
    for anbieter, modell, eingabe, ausgabe in [
        ("anthropic", "claude-opus-5", Decimal("12.0000"), Decimal("60.0000")),
        ("anthropic", "claude-haiku-5-5", Decimal("0.8000"), Decimal("4.0000")),
    ]:
        if (anbieter, modell) in vorhandene:
            continue
        create_model_price(
            ctx,
            ModelPriceCreate(
                provider=anbieter,
                model=modell,
                input_per_mtok=eingabe,
                output_per_mtok=ausgabe,
                valid_from=date(2026, 1, 1),
                note=PLATZHALTER,
            ),
        )

    from timbertalk_core.domain.usage.service import list_usage

    if list_usage(ctx, limit=1).total > 0:
        return
    for modell, modul, feature, eingabe_tokens, ausgabe_tokens, zeitpunkt in [
        ("claude-opus-5", UsageModule.A, "voice_booking", 1500, 800, datetime(2026, 5, 4, 7, 5, tzinfo=UTC)),
        (
            "claude-haiku-5-5",
            UsageModule.A,
            "classify_receipt",
            4200,
            150,
            datetime(2026, 5, 4, 16, 30, tzinfo=UTC),
        ),
        (
            "claude-opus-5",
            UsageModule.B,
            "cad_suggestion",
            3000,
            1200,
            datetime(2026, 5, 11, 9, 0, tzinfo=UTC),
        ),
    ]:
        record_usage(
            ctx,
            UsageRecord(
                provider="anthropic",
                model=modell,
                module=modul,
                feature=feature,
                input_tokens=eingabe_tokens,
                output_tokens=ausgabe_tokens,
                project_id=projekte["gaube"]["projekt"],
                occurred_at=zeitpunkt,
            ),
        )


def seed(session: Session) -> None:
    """Legt die Beispieldaten in einer offenen Session an; wiederholbar.

    Parameter:
        session: offene Session; der Aufrufer schreibt die Transaktion fest.
    """
    ctx = _kontext(session)
    _stammdaten(ctx)
    _zusatzfelder(ctx)
    session.flush()
    mitarbeiter = _mitarbeiter(ctx)
    material = _katalog(ctx)
    kunden = _kunden(ctx)
    session.flush()
    projekte = _projekte(ctx, kunden)
    session.flush()
    human_ctx = _menschlicher_kontext(session, mitarbeiter["meister"])
    _buchungen(ctx, human_ctx, projekte, mitarbeiter, material)
    _ki_verbrauch(ctx, projekte)


def main(argv: list[str] | None = None) -> int:
    """Führt das Seed-Skript gegen die konfigurierte Datenbank aus."""
    parser = argparse.ArgumentParser(description="Legt Beispieldaten einer Zimmerei an.")
    parser.add_argument(
        "--database-url",
        default=None,
        help="Abweichende Datenbank-URL; ohne Angabe die aus der Konfiguration.",
    )
    argumente = parser.parse_args(argv)

    settings: Settings = get_settings()
    if argumente.database_url:
        settings = settings.model_copy(update={"database_url": argumente.database_url})

    engine = create_db_engine(settings)
    factory = create_session_factory(engine)
    try:
        with factory() as session:
            seed(session)
            session.commit()
    finally:
        engine.dispose()

    print(f"Beispieldaten angelegt in {settings.database_url}")
    print("Hinweis: alle Preise sind Platzhalter.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
