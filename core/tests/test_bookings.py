"""Prüft Buchungen: Regeln, Statusübergänge und Preisermittlung."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from timbertalk_core.context import ActorType, ServiceContext, Source
from timbertalk_core.domain.audit.models import AuditEvent
from timbertalk_core.domain.bookings.details import registered_kinds, validate_details
from timbertalk_core.domain.bookings.schemas import BookingCreate, BookingUpdate
from timbertalk_core.domain.bookings.service import (
    cancel_booking,
    confirm_booking,
    create_booking,
    delete_booking,
    get_booking,
    list_bookings,
    update_booking,
)
from timbertalk_core.domain.catalog.schemas import MaterialItemCreate, PriceCreate
from timbertalk_core.domain.catalog.service import create_material_item, create_price
from timbertalk_core.domain.customers.schemas import CustomerCreate
from timbertalk_core.domain.customers.service import create_customer
from timbertalk_core.domain.enums import (
    BookingStatus,
    CostTypeKind,
    CustomerType,
    EmployeeRole,
    MaterialCategory,
    PriceTargetType,
)
from timbertalk_core.domain.people.schemas import EmployeeCreate
from timbertalk_core.domain.people.service import create_employee
from timbertalk_core.domain.projects.schemas import ProjectCreate, WorkPackageCreate
from timbertalk_core.domain.projects.service import create_project, create_work_package
from timbertalk_core.domain.reference.schemas import CostTypeCreate, UnitCreate
from timbertalk_core.domain.reference.service import create_cost_type, create_unit
from timbertalk_core.errors import InvalidState, NotFound, PermissionDenied, ValidationFailed

LEISTUNGSTAG = date(2026, 5, 4)


@dataclass
class Welt:
    """Zusammengehörige Beispieldaten für Buchungstests."""

    project_id: uuid.UUID
    other_project_id: uuid.UUID
    work_package_id: uuid.UUID
    other_work_package_id: uuid.UUID
    employee_id: uuid.UUID
    labor_id: uuid.UUID
    travel_id: uuid.UUID
    material_id: uuid.UUID
    equipment_id: uuid.UUID
    other_id: uuid.UUID
    material_item_id: uuid.UUID


@pytest.fixture
def welt(ctx: ServiceContext) -> Welt:
    """Legt Stammdaten, ein Projekt mit Arbeitspaket und einen Mitarbeiter an."""
    for code, label, decimals in [
        ("h", "Stunde", 2),
        ("km", "Kilometer", 1),
        ("m3", "Kubikmeter", 3),
        ("stk", "Stück", 0),
        ("tag", "Tag", 2),
        ("pausch", "Pauschal", 2),
    ]:
        create_unit(ctx, UnitCreate(code=code, label_de=label, decimals=decimals))

    arten = {}
    for code, name, kind, unit, preis in [
        ("labor_master", "Lohn Meister", CostTypeKind.LABOR, "h", Decimal("68.5000")),
        ("travel", "Fahrtkosten", CostTypeKind.TRAVEL, "km", Decimal("0.4500")),
        ("material_timber", "Holz", CostTypeKind.MATERIAL, "m3", None),
        ("crane", "Kran", CostTypeKind.EQUIPMENT, "tag", Decimal("480.0000")),
        ("disposal", "Entsorgung", CostTypeKind.OTHER, "pausch", Decimal("150.0000")),
    ]:
        arten[code] = create_cost_type(
            ctx,
            CostTypeCreate(
                code=code,
                name_de=name,
                kind=kind,
                default_unit_code=unit,
                default_unit_price=preis,
                labor_share=kind is CostTypeKind.LABOR,
            ),
        ).id

    employee = create_employee(
        ctx, EmployeeCreate(first_name="Max", last_name="Holz", role=EmployeeRole.MASTER)
    )
    item = create_material_item(
        ctx,
        MaterialItemCreate(
            name="KVH Fichte C24 60×200",
            category=MaterialCategory.TIMBER,
            unit_code="m3",
            cost_type_code="material_timber",
        ),
    )
    customer = create_customer(
        ctx,
        CustomerCreate(
            customer_type=CustomerType.PRIVATE, first_name="Eva", last_name="Reich", city="Berlin"
        ),
    )
    project = create_project(ctx, ProjectCreate(customer_id=customer.id, title="Dachgaube"))
    anderes = create_project(ctx, ProjectCreate(customer_id=customer.id, title="Carport"))
    package = create_work_package(ctx, WorkPackageCreate(project_id=project.id, title="Abbund"))
    anderes_paket = create_work_package(ctx, WorkPackageCreate(project_id=anderes.id, title="Fundament"))
    ctx.session.commit()

    return Welt(
        project_id=project.id,
        other_project_id=anderes.id,
        work_package_id=package.id,
        other_work_package_id=anderes_paket.id,
        employee_id=employee.id,
        labor_id=arten["labor_master"],
        travel_id=arten["travel"],
        material_id=arten["material_timber"],
        equipment_id=arten["crane"],
        other_id=arten["disposal"],
        material_item_id=item.id,
    )


def _stunden(welt: Welt, **overrides: object) -> BookingCreate:
    daten: dict[str, object] = {
        "project_id": welt.project_id,
        "work_package_id": welt.work_package_id,
        "cost_type_id": welt.labor_id,
        "booking_date": LEISTUNGSTAG,
        "quantity": Decimal("8.50"),
        "employee_id": welt.employee_id,
        "details": {"start_time": "07:00", "end_time": "16:00", "break_minutes": 30},
    }
    daten.update(overrides)
    return BookingCreate(**daten)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- Anlegen


def test_stundenbuchung_anlegen(ctx: ServiceContext, welt: Welt) -> None:
    booking = create_booking(ctx, _stunden(welt))
    ctx.session.commit()

    assert booking.status is BookingStatus.DRAFT
    assert booking.unit_code == "h", "Die Vorgabe-Einheit der Kostenart wird übernommen"
    assert booking.cost_type_kind is CostTypeKind.LABOR
    assert booking.quantity == Decimal("8.50")
    assert booking.effective_unit_price == Decimal("68.5000")
    assert booking.amount == Decimal("582.250000")
    assert booking.price_origin == "cost_type_default"
    assert booking.details["break_minutes"] == 30


def test_buchung_aus_ki_ist_entwurf(agent_ctx: ServiceContext, welt: Welt) -> None:
    """Abnahmekriterium: source=agent erzeugt eine Buchung im Status draft."""
    booking = create_booking(agent_ctx, _stunden(welt, source=Source.AGENT, source_ref="transkript-42"))
    agent_ctx.session.commit()
    assert booking.status is BookingStatus.DRAFT
    assert booking.source is Source.AGENT
    assert booking.source_ref == "transkript-42"


def test_arbeitszeit_braucht_mitarbeiter(ctx: ServiceContext, welt: Welt) -> None:
    with pytest.raises(ValidationFailed, match="muss ein Mitarbeiter angegeben"):
        create_booking(ctx, _stunden(welt, employee_id=None))


def test_falsche_einheit_wird_abgelehnt(ctx: ServiceContext, welt: Welt) -> None:
    """Abnahmekriterium: die Einheit muss zur Kostenart passen."""
    with pytest.raises(ValidationFailed, match="passt nicht zur Kostenart"):
        create_booking(ctx, _stunden(welt, unit_code="km"))


def test_unbekannte_einheit_wird_abgelehnt(ctx: ServiceContext, welt: Welt) -> None:
    with pytest.raises(NotFound, match="Einheit"):
        create_booking(ctx, _stunden(welt, unit_code="gibtsnicht"))


def test_zu_viele_nachkommastellen_fuer_einheit(ctx: ServiceContext, welt: Welt) -> None:
    with pytest.raises(ValidationFailed, match="Nachkommastellen"):
        create_booking(ctx, _stunden(welt, quantity=Decimal("8.123")))


def test_artikel_nur_bei_material(ctx: ServiceContext, welt: Welt) -> None:
    with pytest.raises(ValidationFailed, match="nur bei Materialbuchungen"):
        create_booking(ctx, _stunden(welt, material_item_id=welt.material_item_id))


def test_arbeitspaket_muss_zum_projekt_passen(ctx: ServiceContext, welt: Welt) -> None:
    with pytest.raises(ValidationFailed, match="nicht zum angegebenen Projekt"):
        create_booking(ctx, _stunden(welt, work_package_id=welt.other_work_package_id))


def test_unbekanntes_projekt(ctx: ServiceContext, welt: Welt) -> None:
    with pytest.raises(NotFound, match="Projekt"):
        create_booking(ctx, _stunden(welt, project_id=uuid.uuid4(), work_package_id=None))


def test_materialbuchung_nutzt_artikelpreis(ctx: ServiceContext, welt: Welt) -> None:
    create_price(
        ctx,
        PriceCreate(
            target_type=PriceTargetType.MATERIAL_ITEM,
            target_id=welt.material_item_id,
            unit_price=Decimal("489.5000"),
            valid_from=date(2026, 1, 1),
        ),
    )
    ctx.session.commit()

    booking = create_booking(
        ctx,
        BookingCreate(
            project_id=welt.project_id,
            cost_type_id=welt.material_id,
            booking_date=LEISTUNGSTAG,
            quantity=Decimal("2.400"),
            material_item_id=welt.material_item_id,
            details={"delivery_note_ref": "LS-2026-0815"},
        ),
    )
    ctx.session.commit()
    assert booking.effective_unit_price == Decimal("489.5000")
    assert booking.price_origin == "price_material_item"
    assert booking.amount == Decimal("1174.800000")
    assert booking.details["delivery_note_ref"] == "LS-2026-0815"


def test_betrag_wird_gerundet_und_bleibt_lesbar(ctx: ServiceContext, welt: Welt) -> None:
    """Menge mal Preis hat mehr Nachkommastellen als ein Geldbetrag zulässt.

    Ohne Rundung entstünde ein Betrag mit bis zu zwölf Nachkommastellen; das Lese-Schema
    erlaubt sechs. Die Buchung wäre damit nach einer gewöhnlichen Preispflege nicht mehr
    lesbar – auch nicht in der Liste des Projekts.
    """
    booking = create_booking(ctx, _stunden(welt, quantity=Decimal("8.33"), unit_price=Decimal("1.123456")))
    ctx.session.commit()

    # 8.33 × 1.123456 = 9.35838848
    assert booking.amount == Decimal("9.358388")
    assert get_booking(ctx, booking.id).amount == Decimal("9.358388")
    assert list_bookings(ctx, project_id=welt.project_id).items[0].amount == Decimal("9.358388")


def test_spaeterer_preis_macht_buchung_nicht_unlesbar(ctx: ServiceContext, welt: Welt) -> None:
    """Ein neuer Preis mit sechs Nachkommastellen darf bestehende Buchungen nicht sprengen."""
    booking = create_booking(ctx, _stunden(welt, quantity=Decimal("8.33")))
    ctx.session.commit()

    create_price(
        ctx,
        PriceCreate(
            target_type=PriceTargetType.COST_TYPE,
            target_id=welt.labor_id,
            unit_price=Decimal("70.123456"),
            valid_from=date(2026, 1, 1),
        ),
    )
    ctx.session.commit()

    gelesen = get_booking(ctx, booking.id)
    assert gelesen.price_origin == "price_cost_type"
    # 8.33 × 70.123456 = 584.12838848
    assert gelesen.amount == Decimal("584.128388")
    assert list_bookings(ctx, project_id=welt.project_id).total == 1


def test_zu_grosser_betrag_wird_abgelehnt(ctx: ServiceContext, welt: Welt) -> None:
    """Passt Menge mal Preis in keinen Geldbetrag, kommt ein fachlicher Fehler statt 500."""
    with pytest.raises(ValidationFailed, match="zu groß"):
        create_booking(ctx, _stunden(welt, quantity=Decimal("100000000000"), unit_price=Decimal("1000")))


def test_abweichender_preis_hat_vorrang(ctx: ServiceContext, welt: Welt) -> None:
    booking = create_booking(ctx, _stunden(welt, unit_price=Decimal("75.0000")))
    ctx.session.commit()
    assert booking.unit_price == Decimal("75.0000")
    assert booking.effective_unit_price == Decimal("75.0000")
    assert booking.price_origin == "booking"


def test_buchung_ohne_preis_hat_keinen_betrag(ctx: ServiceContext, welt: Welt) -> None:
    booking = create_booking(
        ctx,
        BookingCreate(
            project_id=welt.project_id,
            cost_type_id=welt.material_id,
            booking_date=LEISTUNGSTAG,
            quantity=Decimal("1.000"),
        ),
    )
    ctx.session.commit()
    assert booking.effective_unit_price is None
    assert booking.amount is None
    assert booking.price_origin is None


def test_fahrt_und_geraet_und_pauschale(ctx: ServiceContext, welt: Welt) -> None:
    fahrt = create_booking(
        ctx,
        BookingCreate(
            project_id=welt.project_id,
            cost_type_id=welt.travel_id,
            booking_date=LEISTUNGSTAG,
            quantity=Decimal("42.5"),
            details={
                "from_label": "Werkstatt",
                "to_label": "Baustelle Dachgaube",
                "round_trip": True,
                "vehicle": "Sprinter",
            },
        ),
    )
    kran = create_booking(
        ctx,
        BookingCreate(
            project_id=welt.project_id,
            cost_type_id=welt.equipment_id,
            booking_date=LEISTUNGSTAG,
            quantity=Decimal("1.00"),
            details={"equipment_name": "Autokran 30 t", "hours_or_days": "1"},
        ),
    )
    pauschale = create_booking(
        ctx,
        BookingCreate(
            project_id=welt.project_id,
            cost_type_id=welt.other_id,
            booking_date=LEISTUNGSTAG,
            quantity=Decimal("1.00"),
            description="Containermiete",
        ),
    )
    ctx.session.commit()

    assert fahrt.details["round_trip"] is True
    assert fahrt.details["distance_method"] == "manual"
    assert fahrt.amount == Decimal("19.125000")
    assert kran.details["equipment_name"] == "Autokran 30 t"
    assert pauschale.details == {}
    assert pauschale.amount == Decimal("150.000000")


def test_geraet_ohne_namen_wird_abgelehnt(ctx: ServiceContext, welt: Welt) -> None:
    with pytest.raises(ValidationFailed, match="Detailfelder"):
        create_booking(
            ctx,
            BookingCreate(
                project_id=welt.project_id,
                cost_type_id=welt.equipment_id,
                booking_date=LEISTUNGSTAG,
                quantity=Decimal("1.00"),
                details={},
            ),
        )


def test_unbekanntes_detailfeld_wird_abgelehnt(ctx: ServiceContext, welt: Welt) -> None:
    with pytest.raises(ValidationFailed, match="Detailfelder"):
        create_booking(ctx, _stunden(welt, details={"gibtsnicht": "wert"}))


def test_arbeitszeit_ende_vor_beginn(ctx: ServiceContext, welt: Welt) -> None:
    with pytest.raises(ValidationFailed, match="Detailfelder"):
        create_booking(ctx, _stunden(welt, details={"start_time": "16:00", "end_time": "07:00"}))


def test_details_registry_kennt_alle_arten() -> None:
    assert set(registered_kinds()) == {"labor", "travel", "material", "equipment", "other"}
    assert validate_details(CostTypeKind.OTHER, None) == {}


# --------------------------------------------------------------------------- Status


def test_bestaetigen_durch_menschen(ctx: ServiceContext, welt: Welt) -> None:
    booking = create_booking(ctx, _stunden(welt))
    ctx.session.commit()

    bestaetigt = confirm_booking(ctx, booking.id, expected_version=booking.version)
    ctx.session.commit()
    assert bestaetigt.status is BookingStatus.CONFIRMED
    assert bestaetigt.confirmed_by == ctx.actor_id
    assert bestaetigt.confirmed_at is not None

    # Nochmaliges Bestätigen ändert nichts.
    assert confirm_booking(ctx, booking.id).status is BookingStatus.CONFIRMED


def test_bestaetigen_durch_agent_wird_abgelehnt(agent_ctx: ServiceContext, welt: Welt) -> None:
    """Abnahmekriterium: Bestätigung durch actor_type=agent wird abgelehnt."""
    booking = create_booking(agent_ctx, _stunden(welt, source=Source.AGENT))
    agent_ctx.session.commit()

    assert agent_ctx.actor_type is ActorType.AGENT
    with pytest.raises(PermissionDenied, match="nur durch einen Menschen"):
        confirm_booking(agent_ctx, booking.id)


def test_stornieren(ctx: ServiceContext, welt: Welt) -> None:
    booking = create_booking(ctx, _stunden(welt))
    ctx.session.commit()
    storniert = cancel_booking(ctx, booking.id)
    ctx.session.commit()
    assert storniert.status is BookingStatus.CANCELLED

    with pytest.raises(InvalidState, match="unveränderbar"):
        update_booking(ctx, booking.id, BookingUpdate(quantity=Decimal("1.00")))


def test_stornierte_buchung_kann_nicht_geloescht_werden(ctx: ServiceContext, welt: Welt) -> None:
    """`cancelled` ist unveränderbar: die Stornierung muss nachvollziehbar bleiben."""
    booking = create_booking(ctx, _stunden(welt))
    ctx.session.commit()
    cancel_booking(ctx, booking.id)
    ctx.session.commit()

    with pytest.raises(InvalidState, match="unveränderbar"):
        delete_booking(ctx, booking.id)
    assert get_booking(ctx, booking.id).deleted_at is None


def test_gesperrte_buchung_ist_unveraenderbar(ctx: ServiceContext, welt: Welt) -> None:
    """Abnahmekriterium: locked-Buchungen lassen sich nicht ändern."""
    booking = create_booking(ctx, _stunden(welt))
    ctx.session.commit()
    confirm_booking(ctx, booking.id)
    ctx.session.commit()

    # `locked` setzt später die Rechnung; hier direkt am Datensatz für den Test.
    from timbertalk_core.domain.bookings.repository import BookingRepository

    gespeichert = BookingRepository(ctx.session).get(booking.id)
    assert gespeichert is not None
    gespeichert.status = BookingStatus.LOCKED.value
    ctx.session.commit()

    with pytest.raises(InvalidState, match="unveränderbar"):
        update_booking(ctx, booking.id, BookingUpdate(quantity=Decimal("1.00")))
    with pytest.raises(InvalidState, match="gesperrte Buchung kann nicht storniert"):
        cancel_booking(ctx, booking.id)
    with pytest.raises(InvalidState, match="gesperrte Buchung kann nicht gelöscht"):
        delete_booking(ctx, booking.id)
    assert get_booking(ctx, booking.id).status is BookingStatus.LOCKED


def test_bestaetigte_buchung_kann_nicht_erneut_in_entwurf(ctx: ServiceContext, welt: Welt) -> None:
    booking = create_booking(ctx, _stunden(welt))
    ctx.session.commit()
    cancel_booking(ctx, booking.id)
    ctx.session.commit()
    with pytest.raises(InvalidState, match="Status 'draft'"):
        confirm_booking(ctx, booking.id)


# --------------------------------------------------------------------------- Ändern und Listen


def test_buchung_aendern(ctx: ServiceContext, welt: Welt) -> None:
    booking = create_booking(ctx, _stunden(welt))
    ctx.session.commit()

    geaendert = update_booking(
        ctx,
        booking.id,
        BookingUpdate(
            quantity=Decimal("9.00"),
            description="Abbund fertiggestellt",
            details={"start_time": "07:00", "end_time": "17:00", "break_minutes": 60},
        ),
        expected_version=booking.version,
    )
    ctx.session.commit()
    assert geaendert.quantity == Decimal("9.00")
    assert geaendert.amount == Decimal("616.500000")
    assert geaendert.details["break_minutes"] == 60
    assert geaendert.description == "Abbund fertiggestellt"


def test_bestaetigte_buchung_bleibt_aenderbar(ctx: ServiceContext, welt: Welt) -> None:
    booking = create_booking(ctx, _stunden(welt))
    ctx.session.commit()
    confirm_booking(ctx, booking.id)
    ctx.session.commit()
    geaendert = update_booking(ctx, booking.id, BookingUpdate(quantity=Decimal("7.00")))
    ctx.session.commit()
    assert geaendert.quantity == Decimal("7.00")
    assert geaendert.status is BookingStatus.CONFIRMED


def test_buchungen_filtern(ctx: ServiceContext, welt: Welt) -> None:
    create_booking(ctx, _stunden(welt))
    create_booking(
        ctx,
        BookingCreate(
            project_id=welt.project_id,
            cost_type_id=welt.travel_id,
            booking_date=date(2026, 5, 5),
            quantity=Decimal("30.0"),
        ),
    )
    ctx.session.commit()

    assert list_bookings(ctx, project_id=welt.project_id).total == 2
    assert list_bookings(ctx, cost_type_id=welt.travel_id).total == 1
    assert list_bookings(ctx, employee_id=welt.employee_id).total == 1
    assert list_bookings(ctx, status=BookingStatus.DRAFT).total == 2
    assert list_bookings(ctx, status=BookingStatus.CONFIRMED).total == 0
    assert list_bookings(ctx, date_from=date(2026, 5, 5)).total == 1
    assert list_bookings(ctx, date_to=date(2026, 5, 4)).total == 1
    assert list_bookings(ctx, project_id=welt.other_project_id).total == 0
    # Neueste Leistungstage zuerst
    assert [item.booking_date for item in list_bookings(ctx).items] == [
        date(2026, 5, 5),
        date(2026, 5, 4),
    ]


def test_buchung_loeschen(ctx: ServiceContext, welt: Welt) -> None:
    booking = create_booking(ctx, _stunden(welt))
    ctx.session.commit()
    delete_booking(ctx, booking.id)
    ctx.session.commit()
    assert list_bookings(ctx).total == 0
    with pytest.raises(NotFound):
        get_booking(ctx, booking.id)


def test_statuswechsel_werden_protokolliert(ctx: ServiceContext, welt: Welt) -> None:
    booking = create_booking(ctx, _stunden(welt))
    ctx.session.commit()
    confirm_booking(ctx, booking.id)
    ctx.session.commit()
    cancel_booking(ctx, booking.id)
    ctx.session.commit()

    events = list(
        ctx.session.scalars(
            select(AuditEvent)
            .where(AuditEvent.entity_id == booking.id)
            .order_by(AuditEvent.occurred_at, AuditEvent.id)
        )
    )
    assert [event.action for event in events] == ["create", "confirm", "cancel"]
    assert events[1].changes["status"] == {"old": "draft", "new": "confirmed"}
    assert events[2].changes["status"] == {"old": "confirmed", "new": "cancelled"}
