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
