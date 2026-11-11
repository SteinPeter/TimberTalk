"""Prüft die Auslieferung der Entwickler-Oberfläche („Werkbank").

Die Werkbank gehört nur in die lokale Installation. In jeder anderen Umgebung darf
`/dev` nichts preisgeben – auch nicht, dass es den Pfad gäbe.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from conftest import TEST_API_KEY
from timbertalk_core.api.app import create_app
from timbertalk_core.api.dev_ui import DEV_UI_PREFIX, dev_ui_dir
from timbertalk_core.config import Settings


def _client(session_factory: sessionmaker[Session], **einstellungen: object) -> Iterator[TestClient]:
    """Baut einen Client auf einer Anwendung mit abweichenden Einstellungen."""
    settings = Settings(_env_file=None, api_key=TEST_API_KEY, **einstellungen)  # type: ignore[call-arg]
    with TestClient(create_app(settings=settings, session_factory=session_factory)) as test_client:
        yield test_client


@pytest.fixture
def lokal(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    """Client auf einer lokalen Installation."""
    yield from _client(session_factory, environment="local")


def test_werkbank_ist_lokal_erreichbar(lokal: TestClient) -> None:
    """In der lokalen Installation liefert /dev die Oberfläche aus."""
    antwort = lokal.get(f"{DEV_UI_PREFIX}/")
    assert antwort.status_code == 200
    assert antwort.headers["content-type"].startswith("text/html")
    assert "Werkbank" in antwort.text


def test_werkbank_ist_nur_lokal_erreichbar(client: TestClient) -> None:
    """Abnahmekriterium: außerhalb von `local` gibt /dev 404.

    Die Fixture `client` arbeitet mit `environment="test"`.
    """
    assert client.get(f"{DEV_UI_PREFIX}/").status_code == 404
    assert client.get(f"{DEV_UI_PREFIX}/index.html").status_code == 404


@pytest.mark.parametrize(
    ("environment", "dev_ui", "erwartet"),
    [
        ("local", None, 200),
        ("test", None, 404),
        ("production", None, 404),
        ("production", True, 200),
        ("local", False, 404),
    ],
)
def test_einstellung_entscheidet_ueber_die_werkbank(
    session_factory: sessionmaker[Session],
    environment: str,
    dev_ui: bool | None,
    erwartet: int,
) -> None:
    """`TIMBERTALK_DEV_UI` übersteuert die Betriebsart in beide Richtungen."""
    for test_client in _client(session_factory, environment=environment, dev_ui=dev_ui):
        assert test_client.get(f"{DEV_UI_PREFIX}/").status_code == erwartet


def test_werkbank_braucht_keinen_schluessel(lokal: TestClient) -> None:
    """Die Dateien selbst sind ohne `X-API-Key` abrufbar; die Daten dahinter nicht.

    Die Oberfläche muss laden, bevor jemand einen Schlüssel eingeben kann. Jeder
    Datenaufruf aus der Oberfläche heraus geht weiterhin über die Kopfzeile.
    """
    assert "x-api-key" not in {name.lower() for name in lokal.headers}
    assert lokal.get(f"{DEV_UI_PREFIX}/").status_code == 200
    assert lokal.get("/customers").status_code == 403


def test_werkbank_steht_nicht_in_der_openapi_beschreibung(lokal: TestClient) -> None:
    """Ausgelieferte Dateien sind keine API; sie gehören nicht in die Beschreibung."""
    schema = lokal.get("/openapi.json").json()
    assert not [pfad for pfad in schema["paths"] if pfad.startswith(DEV_UI_PREFIX)]


def test_dateien_der_werkbank_liegen_im_paket() -> None:
    """Die Dateien liegen im Paket, damit sie mit einer Installation mitkommen."""
    verzeichnis = dev_ui_dir()
    assert verzeichnis.is_dir()
    assert (verzeichnis / "index.html").is_file()
