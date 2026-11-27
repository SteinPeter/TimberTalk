# Tests für das Feature „Planung: Kalender je Mitarbeiter“ (F8).
# Fixtures aus backend/conftest.py: `session` für service.py, `client` (Admin) und
# `client_as("<rolle>")` für die Endpunkte. Jeder Test bekommt eine eigene, leere Datenbank.

from collections.abc import Callable
from datetime import date, time, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from timbertalk.features.accounts import service as accounts
from timbertalk.features.notifications import service as notifications
from timbertalk.features.planning import service
from timbertalk.features.planning.models import EntryIn, RequestIn, ResourceIn

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


# --- Mitteilungen -------------------------------------------------------------------


def _texts(session: Session, account_id: int) -> list[str]:
    return [n.text for n in reversed(notifications.list_notifications(session, account_id))]


def test_mitteilungen_beim_einplanen_aendern_und_absagen(session: Session) -> None:
    chef = _person(session, "chef", "Chef", "admin")
    max_ = _person(session, "max", "Max")
    tom = _person(session, "tom", "Tom")
    saved = service.create_entry(
        session, _entry([max_, chef], end_date=TUE, location="Potsdam"), created_by=chef
    )
    entry_id = saved.entry.id
    # Ohne Änderung keine Mitteilung „Geändert“; Tom kommt dazu, Max fällt weg.
    service.update_entry(
        session, entry_id, _entry([tom, chef], end_date=TUE, location="Potsdam"), acting_id=chef
    )
    service.update_entry(
        session, entry_id, _entry([tom, chef], end_date=WED, location="Potsdam"), acting_id=chef
    )
    service.delete_entry(session, entry_id, acting_id=chef)

    assert _texts(session, max_) == [
        "Neu eingeplant: Carport Berger, Mo 30.11.–Di 01.12., Potsdam.",
        "Ausgeplant: Carport Berger, Mo 30.11.–Di 01.12., Potsdam.",
    ]
    assert _texts(session, tom) == [
        "Neu eingeplant: Carport Berger, Mo 30.11.–Di 01.12., Potsdam.",
        "Geändert: Carport Berger, Mo 30.11.–Mi 02.12., Potsdam "
        "(vorher: Carport Berger, Mo 30.11.–Di 01.12., Potsdam).",
        "Abgesagt: Carport Berger, Mo 30.11.–Mi 02.12., Potsdam.",
    ]
    assert _texts(session, chef) == []  # wer plant, bekommt selbst nichts


def test_beschreibung_mit_uhrzeit(session: Session) -> None:
    max_ = _person(session, "max", "Max")
    saved = service.create_entry(
        session, _entry([max_], start_time=time(7, 0), end_time=time(12, 30)), None
    )
    entry = service.get_entry(session, saved.entry.id)
    assert service.describe(entry) == "Carport Berger, Mo 30.11., 07:00–12:30 Uhr"


# --- Fahrzeuge und Maschinen ---------------------------------------------------------


def _resource(session: Session, name: str, category: str = "vehicle") -> int:
    return service.create_resource(session, ResourceIn(name=name, category=category)).id


def test_kran_einplanen_und_doppelt_verplant_melden(session: Session) -> None:
    max_ = _person(session, "max", "Max")
    kran = _resource(session, "Autokran", "machine")
    first = service.create_entry(session, _entry([max_], resources=[kran], end_date=TUE), None)
    assert [r.display_name for r in first.entry.resources] == ["Autokran"]

    # Nur der Kran, ohne Person – z. B. gemietet mit Fahrer.
    second = service.create_entry(
        session, _entry([], title="Dachstuhl Weber", resources=[kran], start_date=TUE), None
    )
    assert second.warnings == ["Autokran ist am 01.12.2026 schon verplant: Carport Berger."]


def test_ausgemustertes_fahrzeug_kann_man_nicht_mehr_einplanen(session: Session) -> None:
    max_ = _person(session, "max", "Max")
    alt = _resource(session, "Alter Transporter")
    saved = service.create_entry(session, _entry([max_], resources=[alt]), None)
    service.update_resource(
        session, alt, ResourceIn(name="Alter Transporter", category="vehicle", active=False)
    )
    assert [r.name for r in service.list_resources(session)] == []
    assert [r.name for r in service.list_resources(session, include_inactive=True)] == [
        "Alter Transporter"
    ]
    # Der alte Termin behält ihn, ein neuer nicht.
    week = service.list_entries(session, MON, SUN, max_, True)
    assert week[0].resources[0].display_name == "Alter Transporter"
    assert saved.entry.id == week[0].id
    with pytest.raises(ValueError, match="nicht"):
        service.create_entry(session, _entry([max_], resources=[alt]), None)


@pytest.mark.parametrize(
    ("name", "category", "text"), [(" ", "vehicle", "Namen"), ("X", "boot", "Art")]
)
def test_fahrzeug_eingaben_werden_geprueft(
    session: Session, name: str, category: str, text: str
) -> None:
    with pytest.raises(ValueError, match=text):
        service.create_resource(session, ResourceIn(name=name, category=category))


def test_api_fahrzeuge_pflegt_nur_wer_plant(client_as: Callable[[str], TestClient]) -> None:
    geselle = client_as("journeyman")
    meister = client_as("master")
    body = {"name": "Transporter", "category": "vehicle"}
    assert geselle.post("/api/planning/resources", json=body).status_code == 403
    created = meister.post("/api/planning/resources", json=body)
    assert created.status_code == 201
    assert created.json()["category_label"] == "Fahrzeug"
    assert [r["name"] for r in geselle.get("/api/planning/resources").json()] == ["Transporter"]


# --- Urlaubsanträge -------------------------------------------------------------------


def test_urlaub_beantragen_genehmigen_landet_im_kalender(session: Session) -> None:
    chef = _person(session, "chef", "Chef", "owner")
    _person(session, "admin", "Admin", "admin")  # bekommt keine Mitteilung: entscheidet nicht
    max_ = _person(session, "max", "Max Berger")
    service.create_entry(session, _entry([max_], end_date=TUE), created_by=chef)

    request = service.request_absence(session, max_, RequestIn(start_date=TUE, end_date=SUN))
    assert request.status_label == "Offen" and request.days == 6
    # Der Chef sieht beim Antrag gleich, dass Max am Dienstag eingeplant ist.
    assert request.conflicts == ["Max Berger ist am 01.12.2026 schon eingeplant: Carport Berger."]
    assert _texts(session, chef) == [
        "Urlaubsantrag von Max Berger: Di 01.12.–So 06.12. – bitte auf dem Dashboard entscheiden."
    ]
    assert notifications.list_notifications(session, chef)[0].link == "#start"

    decision = service.decide_request(session, request.id, True, chef)
    assert decision.request.status_label == "Genehmigt"
    assert decision.warnings == request.conflicts
    week = service.list_entries(session, MON, SUN, max_, view_all=False)
    assert [(e.title, e.kind) for e in week] == [
        ("Carport Berger", "job"),
        ("Urlaub", "vacation"),
    ]
    assert _texts(session, max_)[-1] == "Urlaub genehmigt: Di 01.12.–So 06.12."
    assert _texts(session, chef) == []  # „bitte entscheiden“ ist erledigt und verschwindet
    with pytest.raises(ValueError, match="schon entschieden"):
        service.decide_request(session, request.id, False, chef)


def test_urlaub_ablehnen_mit_grund_und_zurueckziehen(session: Session) -> None:
    chef = _person(session, "chef", "Chef", "admin")
    owner = _person(session, "inhaberin", "Inhaberin", "owner")  # bekommt „bitte entscheiden“
    max_ = _person(session, "max", "Max")
    tom = _person(session, "tom", "Tom")
    first = service.request_absence(session, max_, RequestIn(start_date=MON, end_date=WED))
    service.decide_request(session, first.id, False, chef, " Da ist Abnahme. ")
    assert _texts(session, max_) == ["Urlaub abgelehnt: Mo 30.11.–Mi 02.12. Da ist Abnahme."]
    assert service.list_entries(session, MON, SUN, max_, view_all=False) == []

    second = service.request_absence(session, max_, RequestIn(start_date=SUN, end_date=SUN))
    with pytest.raises(LookupError):
        service.withdraw_request(session, second.id, tom)  # fremde Anträge nicht
    assert len(_texts(session, owner)) == 1
    service.withdraw_request(session, second.id, max_)
    assert _texts(session, owner) == []  # zurückgezogen: nichts mehr zu entscheiden
    assert [r.status for r in service.list_requests(session, max_, may_approve=False)] == [
        "rejected"
    ]
    with pytest.raises(ValueError, match="vor dem ersten"):
        service.request_absence(session, max_, RequestIn(start_date=WED, end_date=MON))


def test_api_urlaub_geselle_beantragt_chef_genehmigt(
    client: TestClient, client_as: Callable[[str], TestClient]
) -> None:
    geselle = client_as("journeyman")
    chef = client_as("owner")
    created = geselle.post(
        "/api/planning/requests", json={"start_date": "2026-12-21", "end_date": "2026-12-23"}
    )
    assert created.status_code == 201
    request_id = created.json()["id"]
    assert geselle.post(f"/api/planning/requests/{request_id}/approve", json={}).status_code == 403
    assert client.post(f"/api/planning/requests/{request_id}/approve", json={}).status_code == 403
    assert len(chef.get("/api/planning/requests").json()) == 1
    approved = chef.post(f"/api/planning/requests/{request_id}/approve", json={})
    assert approved.json()["request"]["status"] == "approved"
    assert geselle.get("/api/planning/requests").json()[0]["status_label"] == "Genehmigt"


# --- Kalender-Abo (iCal) ---------------------------------------------------------------


def test_ical_link_und_kalender_als_text(session: Session) -> None:
    max_ = _person(session, "max", "Max Berger")
    tom = _person(session, "tom", "Tom")
    today = date.today()
    service.create_entry(
        session,
        _entry([max_, tom], title="Carport Berger; Teil 2", start_date=today, location="Potsdam"),
        None,
    )
    service.create_entry(
        session,
        _entry(
            [max_],
            title="Werkstatt",
            kind="workshop",
            start_date=today,
            end_date=today + timedelta(days=2),
            start_time=time(7, 0),
            end_time=time(15, 30),
        ),
        None,
    )
    assert not service.ical_link(session, max_).active
    link = service.new_ical_link(session, max_)
    token = link.path.removeprefix("/api/planning/ical/").removesuffix(".ics")

    text = service.ical_feed(session, token)
    assert text.startswith("BEGIN:VCALENDAR\r\n")
    assert "SUMMARY:Carport Berger\\; Teil 2\r\n" in text
    assert f"DTSTART;VALUE=DATE:{today:%Y%m%d}" in text
    assert f"DTEND;VALUE=DATE:{today + timedelta(days=1):%Y%m%d}" in text
    assert f"DTSTART:{today:%Y%m%d}T070000" in text
    assert "RRULE:FREQ=DAILY;COUNT=3" in text
    assert "Mit: Max Berger\\, Tom" in text
    assert all(len(line.encode()) <= 75 for line in text.split("\r\n"))

    # Ein neuer Link macht den alten ungültig; Löschen auch.
    service.new_ical_link(session, max_)
    with pytest.raises(LookupError):
        service.ical_feed(session, token)
    service.delete_ical_link(session, max_)
    assert not service.ical_link(session, max_).active


def test_api_ical_ohne_anmeldung_nur_mit_schluessel(
    client_as: Callable[[str], TestClient], anonymous_client: TestClient
) -> None:
    geselle = client_as("journeyman")
    path = geselle.post("/api/planning/ical-link").json()["path"]
    feed = anonymous_client.get(path)
    assert feed.status_code == 200
    assert feed.headers["content-type"].startswith("text/calendar")
    assert anonymous_client.get("/api/planning/ical/falsch.ics").status_code == 404
    assert anonymous_client.get("/api/planning/ical-link").status_code == 401
