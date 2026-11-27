# Tests für das Feature „Stunden buchen“ (F4).
# Fixtures aus backend/conftest.py: `session` für service.py, `client` (Admin) und
# `client_as("<rolle>")` für die Endpunkte. Jeder Test bekommt eine eigene, leere Datenbank.

from collections.abc import Callable
from datetime import date, time
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from timbertalk.features.accounts import service as accounts
from timbertalk.features.hours import service
from timbertalk.features.hours.models import HoursIn
from timbertalk.features.planning import service as planning
from timbertalk.features.planning.models import EntryIn

MON = date(2026, 11, 30)


def _person(session: Session, username: str) -> int:
    return accounts.create_account(session, username, username.title(), "journeyman")[0].id


@pytest.mark.parametrize(
    ("start", "end", "hours"),
    [
        (time(7, 0), time(12, 0), "5.00"),  # bis 6 Stunden keine Pause
        (time(7, 0), time(16, 0), "8.50"),  # 9 Stunden, davon 30 Minuten Pause
        (time(6, 0), time(16, 0), "9.25"),  # 10 Stunden, davon 45 Minuten Pause
    ],
)
def test_arbeitszeit_abzueglich_gesetzlicher_pause(start: time, end: time, hours: str) -> None:
    assert service.to_hours(service.working_minutes(start, end)) == Decimal(hours)


def test_vorschlaege_aus_dem_kalender_und_abends_bestaetigen(session: Session) -> None:
    max_ = _person(session, "max")
    job = planning.create_entry(
        session,
        EntryIn(
            title="Carport Berger",
            start_date=MON,
            end_date=date(2026, 12, 2),
            start_time=time(7, 0),
            end_time=time(16, 0),
            project_id=17,
            people=[max_],
        ),
        None,
    ).entry
    planning.create_entry(
        session, EntryIn(title="Werkstatt", kind="workshop", start_date=MON, people=[max_]), None
    )
    planning.create_entry(
        session, EntryIn(title="Schule", kind="school", start_date=MON, people=[max_]), None
    )

    found = service.suggestions(session, max_, MON)
    assert [(s.title, s.project_id, s.hours, s.time, s.booked) for s in found] == [
        ("Werkstatt", None, Decimal("8.00"), "ganzer Tag", False),
        ("Carport Berger", 17, Decimal("8.50"), "07:00–16:00", False),
    ]

    carport = next(s for s in found if s.calendar_entry_id == job.id)
    booked = service.confirm_day(
        session,
        [
            HoursIn(
                work_date=MON,
                hours=carport.hours,
                project_id=carport.project_id,
                title=carport.title,
                calendar_entry_id=carport.calendar_entry_id,
            )
        ],
        max_,
        may_manage=False,
    )
    assert [(b.title, b.hours, b.project_id) for b in booked] == [
        ("Carport Berger", Decimal("8.50"), 17)
    ]
    assert [s.booked for s in service.suggestions(session, max_, MON)] == [False, True]
    with pytest.raises(ValueError, match="schon gebucht"):
        service.book(
            session,
            HoursIn(work_date=MON, hours=Decimal("1"), project_id=17, calendar_entry_id=job.id),
            max_,
            may_manage=False,
        )


@pytest.mark.parametrize(
    ("fields", "text"),
    [
        ({"hours": Decimal("0")}, "größer als 0"),
        ({"hours": Decimal("17")}, "16 Stunden"),
        ({"project_id": None, "title": " "}, "wofür"),
        ({"project_id": 0}, "positive"),
    ],
)
def test_stunden_eingaben_werden_geprueft(session: Session, fields: dict, text: str) -> None:
    max_ = _person(session, "max")
    values = {"work_date": MON, "hours": Decimal("8"), "project_id": 17} | fields
    with pytest.raises(ValueError, match=text):
        service.book(session, HoursIn(**values), max_, may_manage=False)


def test_fuer_andere_buchen_und_loeschen_nur_mit_recht(session: Session) -> None:
    max_ = _person(session, "max")
    tom = _person(session, "tom")
    data = HoursIn(work_date=MON, hours=Decimal("7.5"), project_id=17, account_id=tom)
    with pytest.raises(PermissionError):
        service.book(session, data, max_, may_manage=False)
    booked = service.book(session, data, max_, may_manage=True)
    assert (booked.person, booked.hours) == ("Tom", Decimal("7.50"))
    with pytest.raises(LookupError):
        service.delete_hours(session, booked.id, max_, may_manage=False)
    service.delete_hours(session, booked.id, tom, may_manage=False)  # die eigene geht
    assert service.list_hours(session, MON, MON, tom, view_all=False) == []


def test_api_geselle_sieht_nur_eigene_stunden(
    client: TestClient, client_as: Callable[[str], TestClient]
) -> None:
    geselle = client_as("journeyman")
    body = {"work_date": "2026-11-30", "hours": "8", "project_id": 17}
    assert geselle.post("/api/hours", json=body).status_code == 201
    chef = client_as("owner")
    assert chef.post("/api/hours", json=body).status_code == 201  # der Chef für sich

    params = {"start": "2026-11-30", "end": "2026-12-06"}
    assert len(geselle.get("/api/hours", params=params).json()) == 1
    assert len(client.get("/api/hours", params=params).json()) == 2  # der Admin sieht alle
    assert geselle.get("/api/hours/suggestions", params={"day": "2026-11-30"}).json() == []
