"""Prüft die Beispieldaten der Zimmerei."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from timbertalk_core.context import ActorType, ServiceContext, Source
from timbertalk_core.domain.audit.models import AuditEvent
from timbertalk_core.domain.bookings.service import list_bookings
from timbertalk_core.domain.catalog.service import list_material_items
from timbertalk_core.domain.company.service import get_company, get_setting, list_tax_rates
from timbertalk_core.domain.customers.service import list_customers
from timbertalk_core.domain.enums import (
    BookingStatus,
    PriceTargetType,
    UsageGrouping,
    UsagePeriod,
)
from timbertalk_core.domain.people.service import list_employees
from timbertalk_core.domain.projects.service import (
    list_dependencies,
    list_projects,
    list_work_packages,
)
from timbertalk_core.domain.reference.service import list_cost_types, list_units
from timbertalk_core.domain.usage.service import usage_summary
from timbertalk_core.scripts.seed import seed


def _lese_kontext(session: Session) -> ServiceContext:
    return ServiceContext(session=session, actor_type=ActorType.USER, source=Source.MANUAL)


def test_seed_legt_die_beispielzimmerei_an(session: Session) -> None:
    seed(session)
    session.commit()
    ctx = _lese_kontext(session)

    assert get_company(ctx).name == "Zimmerei Muster GmbH"
    assert get_company(ctx).city == "Berlin"
    assert get_setting(ctx, "default_hourly_rate").value["amount"] == "68.50"
    assert get_setting(ctx, "payment_terms_days").value["days"] == 14
    assert list_tax_rates(ctx).total == 3

    einheiten = {einheit.code for einheit in list_units(ctx, limit=50).items}
    assert einheiten == {"h", "km", "m3", "lfm", "m2", "stk", "kg", "pausch"}

    kostenarten = {art.code: art for art in list_cost_types(ctx, limit=50).items}
    assert len(kostenarten) == 9
    assert kostenarten["labor_master"].labor_share is True
    assert kostenarten["labor_journeyman"].labor_share is True
    assert kostenarten["labor_apprentice"].labor_share is True
    assert kostenarten["travel"].default_unit_code == "km"
    assert kostenarten["material_timber"].default_unit_code == "m3"
    assert kostenarten["equipment_crane"].kind.value == "equipment"
    assert kostenarten["disposal"].default_unit_code == "pausch"

    assert list_employees(ctx).total == 3
    assert list_customers(ctx).total == 2
    assert {kunde.customer_type.value for kunde in list_customers(ctx).items} == {
        "private",
        "business",
    }

    artikel = {eintrag.sku: eintrag for eintrag in list_material_items(ctx, limit=50).items}
    assert set(artikel) == {"KVH-60200", "KVH-80240", "BSH-100280", "DL-3050"}
    assert artikel["KVH-60200"].grade == "C24"
    assert artikel["BSH-100280"].grade == "GL24h"


def test_seed_preise_sind_als_platzhalter_gekennzeichnet(session: Session) -> None:
    seed(session)
    session.commit()
    ctx = _lese_kontext(session)

    from timbertalk_core.domain.catalog.service import list_prices

    preise = list_prices(ctx, limit=50).items
    assert len(preise) == 4
    for preis in preise:
        assert preis.note is not None
        assert "Platzhalter" in preis.note
        assert preis.currency == "EUR"
        assert preis.target_type is PriceTargetType.MATERIAL_ITEM


def test_seed_projekte_mit_abhaengigkeit(session: Session) -> None:
    seed(session)
    session.commit()
    ctx = _lese_kontext(session)

    projekte = {projekt.title: projekt for projekt in list_projects(ctx, limit=50).items}
    assert set(projekte) == {"Dachgaube Lindenweg", "Carport Werftstraße"}
    gaube = projekte["Dachgaube Lindenweg"]
    assert gaube.status.value == "active"
    assert gaube.attributes["site_access"].startswith("Zufahrt")

    pakete = list_work_packages(ctx, project_id=gaube.id, limit=50).items
    assert [paket.title for paket in pakete] == [
        "Abbund in der Halle",
        "Montage auf der Baustelle",
        "Dachdeckung vorbereiten",
    ]
    assert pakete[0].cad_ref == "cad://gaube/abbund"
    assert pakete[0].planned_hours == Decimal("24.00")

    abhaengigkeiten = list_dependencies(ctx, project_id=gaube.id).items
    assert len(abhaengigkeiten) == 1
    assert abhaengigkeiten[0].predecessor_id == pakete[0].id
    assert abhaengigkeiten[0].successor_id == pakete[1].id


def test_seed_buchungen_in_allen_status(session: Session) -> None:
    seed(session)
    session.commit()
    ctx = _lese_kontext(session)

    buchungen = list_bookings(ctx, limit=50).items
    assert len(buchungen) == 5
    status = {buchung.status for buchung in buchungen}
    assert status == {BookingStatus.DRAFT, BookingStatus.CONFIRMED, BookingStatus.CANCELLED}

    entwurf = next(b for b in buchungen if b.status is BookingStatus.DRAFT)
    assert entwurf.source is Source.VOICE, "Sprachbuchungen müssen als Entwurf starten"
    assert entwurf.source_ref is not None
    assert entwurf.amount == Decimal("582.250000")

    material = next(b for b in buchungen if b.material_item_id is not None)
    assert material.price_origin == "price_material_item"
    assert material.effective_unit_price == Decimal("489.5000")

    bestaetigt = [b for b in buchungen if b.status is BookingStatus.CONFIRMED]
    assert len(bestaetigt) == 3
    for buchung in bestaetigt:
        assert buchung.confirmed_by is not None
        assert buchung.confirmed_at is not None


def test_seed_ki_verbrauch(session: Session) -> None:
    seed(session)
    session.commit()
    ctx = _lese_kontext(session)

    uebersicht = usage_summary(ctx, period=UsagePeriod.MONTH, group_by=UsageGrouping.MODULE)
    assert {zeile.group for zeile in uebersicht.rows} == {"a", "b"}
    assert uebersicht.total_cost > Decimal("0")
    assert uebersicht.currency == "EUR"


def test_seed_ist_wiederholbar(session: Session) -> None:
    """Ein zweiter Lauf darf keine Datensätze verdoppeln."""
    seed(session)
    session.commit()
    ctx = _lese_kontext(session)
    vorher = {
        "units": list_units(ctx, limit=100).total,
        "cost_types": list_cost_types(ctx, limit=100).total,
        "employees": list_employees(ctx, limit=100).total,
        "customers": list_customers(ctx, limit=100).total,
        "projects": list_projects(ctx, limit=100).total,
        "work_packages": list_work_packages(ctx, limit=100).total,
        "material_items": list_material_items(ctx, limit=100).total,
        "bookings": list_bookings(ctx, limit=100).total,
        "dependencies": list_dependencies(ctx, limit=100).total,
    }
    protokoll_vorher = session.scalar(select(func.count()).select_from(AuditEvent))

    seed(session)
    session.commit()

    nachher = {
        "units": list_units(ctx, limit=100).total,
        "cost_types": list_cost_types(ctx, limit=100).total,
        "employees": list_employees(ctx, limit=100).total,
        "customers": list_customers(ctx, limit=100).total,
        "projects": list_projects(ctx, limit=100).total,
        "work_packages": list_work_packages(ctx, limit=100).total,
        "material_items": list_material_items(ctx, limit=100).total,
        "bookings": list_bookings(ctx, limit=100).total,
        "dependencies": list_dependencies(ctx, limit=100).total,
    }
    assert nachher == vorher
    assert session.scalar(select(func.count()).select_from(AuditEvent)) == protokoll_vorher


def test_seed_protokolliert_akteure_richtig(session: Session) -> None:
    """Stammdaten kommen aus dem Import, Bestätigungen von einem Menschen."""
    seed(session)
    session.commit()

    eintraege = list(session.scalars(select(AuditEvent)))
    nach_aktion: dict[str, set[tuple[str, str]]] = {}
    for eintrag in eintraege:
        nach_aktion.setdefault(eintrag.action, set()).add((eintrag.actor_type, eintrag.source))

    assert nach_aktion["create"] == {(ActorType.SYSTEM.value, Source.IMPORT.value)}
    assert nach_aktion["confirm"] == {(ActorType.USER.value, Source.MANUAL.value)}
    assert nach_aktion["cancel"] == {(ActorType.USER.value, Source.MANUAL.value)}


def test_seed_laeuft_ueber_die_session_fabrik(session_factory: sessionmaker[Session]) -> None:
    """Der Seed arbeitet mit einer frisch erzeugten Session, wie im Skript."""
    with session_factory() as eigene_session:
        seed(eigene_session)
        eigene_session.commit()
        ctx = _lese_kontext(eigene_session)
        assert get_company(ctx).name == "Zimmerei Muster GmbH"
