# Tests für das Feature „Planung: Kalender je Mitarbeiter“ (F8).
# Fixtures aus backend/conftest.py: `session` für service.py, `client` (Admin) und
# `client_as("<rolle>")` für die Endpunkte. Jeder Test bekommt eine eigene, leere Datenbank.

from collections.abc import Callable
from datetime import date, time

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from timbertalk.features.accounts import service as accounts
from timbertalk.features.planning import service
from timbertalk.features.planning.models import EntryIn

MON = date(2026, 11, 30)
TUE = date(2026, 12, 1)
WED = date(2026, 12, 2)
SUN = date(2026, 12, 6)


def _person(session: Session, username: str, name: str, role: str = "journeyman") -> int:
    account, _ = accounts.create_account(session, username, name, role)
    return account.id


def _entry(people: list[int], **fields) -> EntryIn:
    values = {"title": "Carport Berger", "start_date": MON, "people": people} | fields
    return EntryIn(**values)


# --- Eintragen und prüfen -------------------------------------------------------


def test_termin_fuer_zwei_personen_ueber_drei_tage(session: Session) -> None:
    max_ = _person(session, "max", "Max Berger")
    tom = _person(session, "tom", "Tom Adler")
    saved = service.create_entry(
        session, _entry([max_, tom], end_date=WED, location="Potsdam"), created_by=None
    )
    assert saved.warnings == []
    assert saved.entry.kind_label == "Baustelle"
    assert [p.display_name for p in saved.entry.people] == ["Max Berger", "Tom Adler"]


def test_ohne_enddatum_ist_es_ein_tag(session: Session) -> None:
    max_ = _person(session, "max", "Max")
    saved = service.create_entry(session, _entry([max_]), created_by=None)
    assert saved.entry.end_date == MON


@pytest.mark.parametrize(
    ("fields", "text"),
    [
        ({"title": "  "}, "worum es geht"),
        ({"kind": "party"}, "Art"),
        ({"end_date": date(2026, 11, 29)}, "vor dem ersten Tag"),
        ({"start_time": time(7, 0)}, "Beginn und Ende"),
        ({"start_time": time(12, 0), "end_time": time(7, 0)}, "vor dem Beginn"),
        ({"end_date": date(2027, 12, 1)}, "ein Jahr"),
        ({"people": []}, "mindestens eine Person"),
        ({"people": [999]}, "gibt es nicht"),
    ],
)
def test_eingaben_werden_geprueft(session: Session, fields: dict, text: str) -> None:
    max_ = _person(session, "max", "Max")
    with pytest.raises(ValueError, match=text):
        people = fields.pop("people", [max_])
        service.create_entry(session, _entry(people, **fields), created_by=None)


def test_gesperrte_person_kann_man_nicht_einplanen(session: Session) -> None:
    admin, _ = accounts.create_account(session, "chef", "Chef", "admin")
    max_ = _person(session, "max", "Max")
    accounts.update_account(session, max_, "Max", "journeyman", None, False, admin)
    with pytest.raises(ValueError, match="gesperrt"):
        service.create_entry(session, _entry([max_]), created_by=None)


# --- Überschneidungen -------------------------------------------------------------


def test_hinweis_wenn_schon_eingeplant_oder_abwesend(session: Session) -> None:
    max_ = _person(session, "max", "Max Berger")
    tom = _person(session, "tom", "Tom Adler")
    service.create_entry(session, _entry([max_], end_date=WED), created_by=None)
    service.create_entry(
        session, _entry([tom], title="Urlaub", kind="vacation", start_date=TUE), created_by=None
    )

    saved = service.create_entry(
        session, _entry([max_, tom], title="Dachgaube Schulz", start_date=TUE), created_by=None
    )

    assert saved.warnings == [
        "Max Berger ist am 01.12.2026 schon eingeplant: Carport Berger.",
        "Tom Adler ist ab 01.12.2026 abwesend: Urlaub.",
    ]
    assert saved.entry.id is not None  # gespeichert wird trotzdem


def test_vormittag_und_nachmittag_ueberschneiden_sich_nicht(session: Session) -> None:
    max_ = _person(session, "max", "Max")
    morning = {"start_time": time(7, 0), "end_time": time(12, 0)}
    service.create_entry(session, _entry([max_], **morning), created_by=None)
    afternoon = {"start_time": time(13, 0), "end_time": time(16, 0)}
    assert service.create_entry(session, _entry([max_], **afternoon), None).warnings == []
    overlap = {"start_time": time(11, 0), "end_time": time(14, 0)}
    assert len(service.create_entry(session, _entry([max_], **overlap), None).warnings) == 2


def test_beim_aendern_zaehlt_der_termin_selbst_nicht(session: Session) -> None:
    max_ = _person(session, "max", "Max")
    saved = service.create_entry(session, _entry([max_], end_date=WED), created_by=None)
    changed = service.update_entry(
        session, saved.entry.id, _entry([max_], title="Carport Berger (neu)", end_date=TUE)
    )
    assert changed.warnings == []
    assert changed.entry.title == "Carport Berger (neu)"
    assert changed.entry.end_date == TUE


# --- Lesen ----------------------------------------------------------------------


def test_woche_lesen_mit_terminen_die_hineinragen(session: Session) -> None:
    max_ = _person(session, "max", "Max")
    service.create_entry(
        session, _entry([max_], title="Vorher", start_date=date(2026, 11, 27), end_date=MON), None
    )
    service.create_entry(
        session, _entry([max_], title="Danach", start_date=date(2026, 12, 7)), None
    )
    week = service.list_entries(session, MON, SUN, viewer_id=max_, view_all=True)
    assert [entry.title for entry in week] == ["Vorher"]


def test_ohne_recht_nur_der_eigene_kalender(session: Session) -> None:
    max_ = _person(session, "max", "Max")
    tom = _person(session, "tom", "Tom")
    service.create_entry(session, _entry([max_], title="Max allein"), None)
    service.create_entry(session, _entry([tom], title="Tom allein"), None)
    service.create_entry(session, _entry([max_, tom], title="Zusammen"), None)

    alle = service.list_entries(session, MON, SUN, viewer_id=max_, view_all=True)
    assert len(alle) == 3
    nur_tom = service.list_entries(session, MON, SUN, viewer_id=max_, view_all=True, account_id=tom)
    assert [entry.title for entry in nur_tom] == ["Tom allein", "Zusammen"]
    # Ohne view_all hilft auch account_id nicht: man sieht nur sich selbst.
    eigene = service.list_entries(session, MON, SUN, viewer_id=max_, view_all=False, account_id=tom)
    assert [entry.title for entry in eigene] == ["Max allein", "Zusammen"]
    assert [p.id for p in service.visible_people(session, max_, view_all=False)] == [max_]


def test_zu_langer_zeitraum_wird_abgelehnt(session: Session) -> None:
    with pytest.raises(ValueError, match="höchstens"):
        service.list_entries(session, MON, date(2027, 3, 1), viewer_id=1, view_all=True)


def test_termin_loeschen(session: Session) -> None:
    max_ = _person(session, "max", "Max")
    saved = service.create_entry(session, _entry([max_]), None)
    service.delete_entry(session, saved.entry.id)
    assert service.list_entries(session, MON, SUN, max_, True) == []
    with pytest.raises(LookupError):
        service.delete_entry(session, saved.entry.id)


# --- Endpunkte -----------------------------------------------------------------------


def _me(browser: TestClient) -> int:
    return browser.get("/api/accounts/me").json()["id"]


def test_api_meister_plant_geselle_sieht(client_as: Callable[[str], TestClient]) -> None:
    meister = client_as("master")
    geselle = client_as("journeyman")
    geselle_id = _me(geselle)

    saved = meister.post(
        "/api/planning/entries",
        json={
            "title": "Carport Berger",
            "start_date": "2026-11-30",
            "end_date": "2026-12-02",
            "start_time": "07:00",
            "end_time": "16:00",
            "people": [geselle_id],
        },
    )
    assert saved.status_code == 201
    assert saved.json()["warnings"] == []

    week = geselle.get("/api/planning/entries", params={"start": "2026-11-30", "end": "2026-12-06"})
    assert [e["title"] for e in week.json()] == ["Carport Berger"]
    assert week.json()[0]["start_time"] == "07:00:00"

    # Der Geselle darf nichts eintragen oder löschen.
    entry_id = saved.json()["entry"]["id"]
    assert geselle.post("/api/planning/entries", json=saved.json()["entry"]).status_code == 403
    assert geselle.delete(f"/api/planning/entries/{entry_id}").status_code == 403
    assert meister.delete(f"/api/planning/entries/{entry_id}").status_code == 204


def test_api_wer_welche_kalender_sieht_stellt_der_chef_ein(
    client: TestClient, client_as: Callable[[str], TestClient]
) -> None:
    geselle = client_as("journeyman")
    client_as("journeyman")  # ein Kollege
    assert len(geselle.get("/api/planning/people").json()) == 3  # mit dem Admin von `client`

    client.put(
        "/api/accounts/roles/journeyman/permissions/calendar.view_all", json={"allowed": False}
    )
    people = geselle.get("/api/planning/people").json()
    assert [p["id"] for p in people] == [_me(geselle)]


def test_api_fehler_mit_deutschem_text(client: TestClient) -> None:
    response = client.post(
        "/api/planning/entries",
        json={"title": "", "start_date": "2026-11-30", "people": [_me(client)]},
    )
    assert response.status_code == 422
    assert "worum es geht" in response.json()["detail"]
    unbekannt = {"title": "x", "start_date": "2026-11-30", "people": [_me(client)]}
    assert client.put("/api/planning/entries/99", json=unbekannt).status_code == 404
    kinds = client.get("/api/planning/kinds").json()
    assert {"kind": "vacation", "label": "Urlaub", "absence": True} in kinds
