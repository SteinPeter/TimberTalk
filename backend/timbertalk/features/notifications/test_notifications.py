# Tests für das Feature „Mitteilungen“.
# Fixtures aus backend/conftest.py: `session` für service.py, `client_as` für die Endpunkte.

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlmodel import Session

from timbertalk.features.notifications import service


def test_mitteilung_schicken_lesen_und_als_gelesen_markieren(session: Session) -> None:
    service.notify(session, [1, 2, 1], "Neu eingeplant: Carport Berger")
    service.notify(session, [1], "Geändert: Carport Berger")
    assert service.unread_count(session, 1) == 2
    assert service.unread_count(session, 2) == 1
    assert [n.text for n in service.list_notifications(session, 1)] == [
        "Geändert: Carport Berger",
        "Neu eingeplant: Carport Berger",
    ]
    service.mark_all_read(session, 1)
    assert service.unread_count(session, 1) == 0
    assert service.unread_count(session, 2) == 1  # die anderen bleiben ungelesen


def test_api_jeder_sieht_nur_seine_eigenen(
    engine: Engine, client_as: Callable[[str], TestClient]
) -> None:
    max_ = client_as("journeyman")
    tom = client_as("journeyman")
    max_id = max_.get("/api/accounts/me").json()["id"]
    with Session(engine) as session:
        service.notify(session, [max_id], "Hallo Max")

    assert max_.get("/api/notifications/unread-count").json() == {"unread": 1}
    assert [n["text"] for n in max_.get("/api/notifications").json()] == ["Hallo Max"]
    assert tom.get("/api/notifications").json() == []
    assert max_.post("/api/notifications/read-all").status_code == 204
    assert max_.get("/api/notifications/unread-count").json() == {"unread": 0}


def test_erledigte_aufgabe_verschwindet_bei_allen(session: Session) -> None:
    service.notify(session, [1, 2], "Urlaubsantrag von Max", topic="absence-request:7")
    service.notify(session, [1], "Urlaubsantrag von Tom", topic="absence-request:8")
    service.notify(session, [1], "Neu eingeplant: Carport Berger")
    service.resolve(session, "absence-request:7")
    assert [n.text for n in service.list_notifications(session, 1)] == [
        "Neu eingeplant: Carport Berger",
        "Urlaubsantrag von Tom",
    ]
    assert service.list_notifications(session, 2) == []


def test_api_eigene_mitteilung_entfernen(
    engine: Engine, client_as: Callable[[str], TestClient]
) -> None:
    max_ = client_as("journeyman")
    tom = client_as("journeyman")
    max_id = max_.get("/api/accounts/me").json()["id"]
    with Session(engine) as session:
        service.notify(session, [max_id], "Hallo Max")
    message_id = max_.get("/api/notifications").json()[0]["id"]
    assert tom.delete(f"/api/notifications/{message_id}").status_code == 404  # fremde nicht
    assert max_.delete(f"/api/notifications/{message_id}").status_code == 204
    assert max_.get("/api/notifications").json() == []
