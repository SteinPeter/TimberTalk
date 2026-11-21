# Prüft, dass /api/health Backend und Datenbank meldet und das Frontend mit allen Reitern
# ausgeliefert wird. Die Hilfe `client` kommt aus backend/conftest.py.

import re

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


def test_reiter_start_zeigt_dass_timbertalk_laeuft(client: TestClient) -> None:
    response = client.get("/features/start/start.js")
    assert response.status_code == 200
    assert "TimberTalk läuft" in response.text


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
