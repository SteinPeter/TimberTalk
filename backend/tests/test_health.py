# Prüft, dass /api/health Backend und Datenbank meldet und das Frontend mit allen Reitern
# ausgeliefert wird. Die Hilfe `client` kommt aus backend/conftest.py.

import re

import pytest
from fastapi.testclient import TestClient

from timbertalk.main import FRONTEND_DIR


def test_health_meldet_backend_und_datenbank(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_startseite_laedt_das_geruest(client: TestClient) -> None:
    # index.html ist nur das Gerüst; Reiter und Inhalte kommen aus app.js und reiter.js.
    response = client.get("/")
    assert response.status_code == 200
    assert '<nav class="tabs"' in response.text
    assert '<script type="module" src="app.js">' in response.text


def test_start_zeigt_dass_timbertalk_laeuft(client: TestClient) -> None:
    # Die Startseite ist das Dashboard (F12). Sein Widget „Systemstatus“ fragt /api/health und
    # erscheint nur, wenn etwas nicht läuft.
    assert client.get("/features/start/start.js").status_code == 200
    response = client.get("/features/start/widgets/status.js")
    assert response.status_code == 200
    assert "/api/health" in response.text


def test_jeder_reiter_ordner_steht_in_reiter_js(client: TestClient) -> None:
    # Die Reiter werden nicht hier aufgezählt, sondern aus den Ordnern unter frontend/features/
    # gelesen. So muss ein neuer Reiter diese Testdatei nicht ändern.
    folders = sorted(p.name for p in (FRONTEND_DIR / "features").iterdir() if p.is_dir())
    liste = client.get("/reiter.js").text
    listed = sorted(re.findall(r'"\./features/([a-z0-9-]+)/\1\.js"', liste))

    assert "start" in folders
    assert listed == folders, (
        "Jeder Ordner unter frontend/features/ braucht eine Zeile in reiter.js"
    )
    for tab in folders:
        modul = client.get(f"/features/{tab}/{tab}.js")
        assert modul.status_code == 200
        assert f'export const id = "{tab}";' in modul.text


@pytest.mark.parametrize("tab", ["settings", "bookings"])
def test_jeder_abschnitt_steht_in_sections_js(client: TestClient, tab: str) -> None:
    # Wie bei den Reitern: Die Abschnitte werden aus den Dateien unter sections/ gelesen. Jede
    # Datei braucht eine Zeile in sections.js und exportiert als id ihren Dateinamen.
    folder = FRONTEND_DIR / "features" / tab / "sections"
    files = sorted(p.stem for p in folder.glob("*.js")) if folder.is_dir() else []
    liste = client.get(f"/features/{tab}/sections.js")
    assert liste.status_code == 200
    listed = sorted(re.findall(r'"\./sections/([a-z0-9-]+)\.js"', liste.text))

    assert listed == files, f"Jede Datei unter {tab}/sections/ braucht eine Zeile in sections.js"
    for section in files:
        modul = client.get(f"/features/{tab}/sections/{section}.js").text
        assert f'export const id = "{section}";' in modul
