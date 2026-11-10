"""Prüft die Transaktionsgrenze einer HTTP-Anfrage.

Hintergrund: Code nach einem `yield` in einer FastAPI-Abhängigkeit läuft erst, nachdem
die Antwort gesendet wurde. Ein `commit` an jener Stelle kommt zu spät – die nächste
Anfrage sieht den eigenen Schreibvorgang dann unter Umständen nicht. Darum schließt
`TransactionMiddleware` die Transaktion ab, bevor die Antwort das Backend verlässt.
Dieser Test nagelt genau diese Reihenfolge fest.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, func, select

from timbertalk_core.api.app import create_app
from timbertalk_core.config import Settings
from timbertalk_core.db.metadata import get_metadata
from timbertalk_core.db.session import create_session_factory
from timbertalk_core.domain.audit.models import AuditEvent
from timbertalk_core.domain.reference.models import Unit

API_KEY = "transaktions-schluessel"


@pytest.fixture
def datei_db(tmp_path: Path) -> str:
    """Datenbank als Datei, damit zwei getrennte Verbindungen möglich sind."""
    return f"sqlite+pysqlite:///{tmp_path / 'transaktion.db'}"


@pytest.fixture
def pruef_engine(datei_db: str) -> Iterator[Engine]:
    """Eigene Engine zum Nachsehen; sieht nur festgeschriebene Daten."""
    engine = create_engine(datei_db)
    get_metadata().create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def anwendung(datei_db: str, pruef_engine: Engine) -> FastAPI:
    """Anwendung auf derselben Datei, aber mit eigener Engine."""
    settings = Settings(_env_file=None, api_key=API_KEY, database_url=datei_db)  # type: ignore[call-arg]
    app_engine = create_engine(datei_db)
    return create_app(settings=settings, session_factory=create_session_factory(app_engine))


class AntwortBeobachter:
    """ASGI-Hülle, die beim Senden der Antwort nachsieht, was in der Datenbank steht.

    Sie liegt außerhalb der Anwendung. Läuft der `commit` erst nach dem Senden, sieht
    die Prüfung die Zeile noch nicht – genau der Fehler, den dieser Test ausschließt.
    """

    def __init__(self, app: Any, engine: Engine) -> None:
        self.app = app
        self.engine = engine
        self.einheiten_beim_senden: int | None = None
        self.protokoll_beim_senden: int | None = None

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        async def beobachtendes_send(nachricht: Any) -> None:
            if nachricht["type"] == "http.response.start" and self.einheiten_beim_senden is None:
                with self.engine.connect() as verbindung:
                    self.einheiten_beim_senden = int(
                        verbindung.execute(select(func.count()).select_from(Unit)).scalar() or 0
                    )
                    self.protokoll_beim_senden = int(
                        verbindung.execute(select(func.count()).select_from(AuditEvent)).scalar() or 0
                    )
            await send(nachricht)

        await self.app(scope, receive, beobachtendes_send)


def test_commit_erfolgt_vor_dem_senden_der_antwort(anwendung: FastAPI, pruef_engine: Engine) -> None:
    beobachter = AntwortBeobachter(anwendung, pruef_engine)
    with TestClient(beobachter) as client:
        antwort = client.post(
            "/units",
            json={"code": "h", "label_de": "Stunde"},
            headers={"X-API-Key": API_KEY, "X-Actor-Type": "user"},
        )
    assert antwort.status_code == 201, antwort.text
    assert beobachter.einheiten_beim_senden == 1, (
        "Die Einheit war beim Senden der Antwort noch nicht festgeschrieben; "
        "die Transaktion wird zu spät abgeschlossen."
    )
    assert beobachter.protokoll_beim_senden == 1, (
        "Der Audit-Eintrag war beim Senden der Antwort noch nicht festgeschrieben."
    )


def test_eigener_schreibvorgang_ist_sofort_sichtbar(anwendung: FastAPI, pruef_engine: Engine) -> None:
    """Die nächste Anfrage muss den Schreibvorgang der vorherigen sehen."""
    with TestClient(anwendung) as client:
        kopf = {"X-API-Key": API_KEY, "X-Actor-Type": "user"}
        for runde in range(10):
            einheit = client.post(
                "/units", json={"code": f"e{runde}", "label_de": f"Einheit {runde}"}, headers=kopf
            )
            assert einheit.status_code == 201, einheit.text
            kostenart = client.post(
                "/cost-types",
                json={
                    "code": f"art_{runde}",
                    "name_de": f"Art {runde}",
                    "kind": "other",
                    "default_unit_code": f"e{runde}",
                },
                headers=kopf,
            )
            assert kostenart.status_code == 201, (
                f"Runde {runde}: die soeben angelegte Einheit war nicht sichtbar – {kostenart.text}"
            )


def test_fehler_verwirft_die_transaktion_vor_dem_senden(anwendung: FastAPI, pruef_engine: Engine) -> None:
    """Scheitert eine Anfrage, darf nichts festgeschrieben sein."""
    with TestClient(anwendung) as client:
        kopf = {"X-API-Key": API_KEY, "X-Actor-Type": "user"}
        antwort = client.post(
            "/cost-types",
            json={
                "code": "ohne_einheit",
                "name_de": "Ohne Einheit",
                "kind": "other",
                "default_unit_code": "gibtsnicht",
            },
            headers=kopf,
        )
    assert antwort.status_code == 404
    with pruef_engine.connect() as verbindung:
        assert verbindung.execute(select(func.count()).select_from(AuditEvent)).scalar() == 0


def test_gesundheitsabfrage_oeffnet_keine_session(anwendung: FastAPI) -> None:
    """`/health` braucht keine Datenbank und darf keine Verbindung belegen."""
    with TestClient(anwendung) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/health").status_code == 200
