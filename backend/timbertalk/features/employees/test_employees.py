# Tests für das Feature „Mitarbeitende“ (F14): Stundenkonto, Urlaubskonto, Rechte.
# Fixtures aus backend/conftest.py: `session` für service.py, `client`/`client_as` für api.py.
# Jeder Test bekommt eine eigene, leere Datenbank. „Heute“ wird festgelegt, damit die Zahlen
# stimmen: Freitag, 6. November 2026.

from collections.abc import Callable
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from timbertalk.features.accounts import service as accounts
from timbertalk.features.employees import service
from timbertalk.features.employees.models import ContractIn
from timbertalk.features.hours import service as hours
from timbertalk.features.hours.models import HoursIn
from timbertalk.features.materials import service as materials
from timbertalk.features.materials.models import CompanyIn
from timbertalk.features.planning import service as planning
from timbertalk.features.planning.models import EntryIn, RequestIn

TODAY = date(2026, 11, 6)  # ein Freitag


@pytest.fixture(autouse=True)
def _betrieb_in_potsdam(session: Session) -> None:
    """Die Rechnungen unten gehen von den Feiertagen in Brandenburg aus (PLZ 14467)."""
    materials.save_company(session, CompanyIn(address="Am Sägewerk 12\n14467 Potsdam"))


def _person(session: Session, username: str, role: str = "journeyman") -> int:
    account, _ = accounts.create_account(session, username, username.title(), role)
    return account.id


def _absent(session: Session, person: int, kind: str, start: date, end: date) -> None:
    planning.create_entry(
        session,
        EntryIn(title=kind, kind=kind, start_date=start, end_date=end, people=[person]),
        created_by=None,
    )


def _book(session: Session, person: int, day: date, amount: str) -> None:
    data = HoursIn(work_date=day, hours=Decimal(amount), title="Carport Berger")
    hours.book(session, data, acting_id=person, may_manage=False)


# --- Stundenkonto --------------------------------------------------------------------


def test_stundenkonto_soll_ohne_urlaub_und_plus(session: Session) -> None:
    max_ = _person(session, "max")
    # Eintritt am Montag, 2. November: Soll für fünf Tage, ein Urlaubstag zählt als erfüllt.
    service.save_contract(
        session,
        max_,
        ContractIn(weekly_hours=Decimal("40"), vacation_days=30, start_date=date(2026, 11, 2)),
    )
    _absent(session, max_, "vacation", date(2026, 11, 5), date(2026, 11, 5))
    for day, amount in [(2, "9"), (3, "8"), (4, "8"), (6, "8")]:
        _book(session, max_, date(2026, 11, day), amount)
    _book(session, max_, date(2026, 10, 30), "8")  # vor dem Eintritt: zählt nicht

    account = service.summary(session, max_, 2026, today=TODAY).hours
    assert account.until == TODAY
    assert account.target_hours == Decimal("32.00")
    assert account.worked_hours == Decimal("33.00")
    assert account.balance_hours == Decimal("1.00")
    assert account.worked_month_hours == Decimal("33.00")


def test_stundenkonto_teilzeit_und_kuenftiges_jahr(session: Session) -> None:
    lena = _person(session, "lena", "apprentice")
    service.save_contract(
        session,
        lena,
        ContractIn(weekly_hours=Decimal("20"), vacation_days=25, start_date=date(2026, 11, 2)),
    )
    # Berufsschule am Dienstag zählt als erfüllt: 4 Tage × 4 Stunden Soll.
    _absent(session, lena, "school", date(2026, 11, 3), date(2026, 11, 3))
    assert service.summary(session, lena, 2026, today=TODAY).hours.balance_hours == Decimal(
        "-16.00"
    )
    assert service.summary(session, lena, 2027, today=TODAY).hours.until is None


# --- Urlaubskonto --------------------------------------------------------------------


def test_urlaubskonto_mit_rest_vorjahr_antrag_und_feiertagen(session: Session) -> None:
    max_ = _person(session, "max")
    service.set_carryover(session, max_, 2026, 3)
    _absent(session, max_, "vacation", date(2026, 11, 5), date(2026, 11, 5))  # vorbei
    # 21.–31.12.: acht Arbeitstage, der 25. ist Feiertag, das Wochenende zählt nicht.
    _absent(session, max_, "vacation", date(2026, 12, 21), date(2026, 12, 31))
    _absent(session, max_, "sick", date(2026, 11, 2), date(2026, 11, 3))
    planning.request_absence(
        session, max_, RequestIn(start_date=date(2026, 12, 1), end_date=date(2026, 12, 3))
    )

    vacation = service.summary(session, max_, 2026, today=TODAY).vacation
    assert (vacation.entitlement, vacation.carryover) == (30, 3)
    assert (vacation.taken, vacation.planned, vacation.requested) == (1, 8, 3)
    assert vacation.remaining == 30 + 3 - 9 - 3
    assert vacation.sick_days == 2
    # Der Rest aus 2026 gehört nicht ins Jahr 2027.
    assert service.summary(session, max_, 2027, today=TODAY).vacation.carryover == 0


def test_vorschau_beim_beantragen(session: Session) -> None:
    max_ = _person(session, "max")
    # 21.12.2026 – 5.1.2027: 2026 sind es 21.–24., 28.–31. (8 Tage, der 25. ist Feiertag),
    # 2027 der 4. und 5. (der 1.1. ist Feiertag) – die zählen im Jahr 2027.
    preview = service.vacation_preview(session, max_, date(2026, 12, 21), date(2027, 1, 5), TODAY)
    assert (preview.year, preview.workdays, preview.other_year_days) == (2026, 10, 2)
    assert (preview.remaining_before, preview.remaining_after) == (30, 22)
    with pytest.raises(ValueError, match="vor dem ersten"):
        service.vacation_preview(session, max_, date(2026, 12, 3), date(2026, 12, 1), TODAY)


def test_falsche_angaben_werden_abgelehnt(session: Session) -> None:
    max_ = _person(session, "max")
    with pytest.raises(ValueError, match="Wochenstunden"):
        service.save_contract(
            session, max_, ContractIn(weekly_hours=Decimal("400"), vacation_days=30)
        )
    with pytest.raises(ValueError, match="Urlaubsanspruch"):
        service.save_contract(
            session, max_, ContractIn(weekly_hours=Decimal("40"), vacation_days=-1)
        )
    with pytest.raises(LookupError):
        service.set_carryover(session, 999, 2026, 2)


# --- Endpunkte und Rechte ----------------------------------------------------------------


def test_api_eigene_konten_und_uebersicht_fuer_den_chef(
    client: TestClient, client_as: Callable[[str], TestClient]
) -> None:
    geselle = client_as("journeyman")
    chef = client_as("owner")
    me = geselle.get("/api/accounts/me").json()["id"]

    preview = geselle.get("/api/employees/me/vacation-preview?start=2026-12-14&end=2026-12-16")
    assert preview.json()["workdays"] == 3
    own = geselle.get("/api/employees/me?year=2026")
    assert own.status_code == 200
    assert own.json()["vacation"]["entitlement"] == 30
    assert geselle.get("/api/employees/overview").status_code == 403
    chef_id = chef.get("/api/accounts/me").json()["id"]
    assert geselle.get(f"/api/employees/{chef_id}").status_code == 404  # fremde nicht

    assert {row["account_id"] for row in chef.get("/api/employees/overview").json()} >= {
        me,
        chef_id,
    }
    assert chef.get(f"/api/employees/{me}").status_code == 200

    contract = {"weekly_hours": "38.5", "vacation_days": 28}
    assert geselle.put(f"/api/employees/{me}/contract", json=contract).status_code == 403
    saved = chef.put(f"/api/employees/{me}/contract", json=contract)
    assert saved.status_code == 200
    assert saved.json()["weekly_hours"] == "38.50"
    carried = chef.put(f"/api/employees/{me}/carryover/2026", json={"days": 4})
    assert carried.json()["vacation"]["carryover"] == 4


def test_api_meister_sieht_nur_sich_bis_es_freigegeben_wird(
    client: TestClient, client_as: Callable[[str], TestClient]
) -> None:
    meister = client_as("master")
    geselle = client_as("journeyman")
    geselle_id = geselle.get("/api/accounts/me").json()["id"]
    contract = {"weekly_hours": "40", "vacation_days": 30}

    # Voreinstellung: nur das eigene Zeitkonto.
    assert meister.get("/api/employees/me").status_code == 200
    assert meister.get("/api/employees/overview").status_code == 403
    assert meister.get(f"/api/employees/{geselle_id}").status_code == 404

    # Stufe 1 – sehen: der Admin setzt in „Rollen und Rechte“ das Häkchen für die Rolle Meister.
    see = client.put(
        "/api/accounts/roles/master/permissions/employees.view_all", json={"allowed": True}
    )
    assert see.status_code == 200
    assert meister.get("/api/employees/overview").status_code == 200
    assert meister.get(f"/api/employees/{geselle_id}").status_code == 200
    assert meister.put(f"/api/employees/{geselle_id}/contract", json=contract).status_code == 403

    # Stufe 2 – sehen und pflegen: ein Häkchen bei „pflegen“ genügt, auch ohne „sehen“.
    client.put("/api/accounts/roles/master/permissions/employees.view_all", json={"allowed": False})
    client.put("/api/accounts/roles/master/permissions/employees.manage", json={"allowed": True})
    assert meister.get("/api/employees/overview").status_code == 200
    assert meister.put(f"/api/employees/{geselle_id}/contract", json=contract).status_code == 200
