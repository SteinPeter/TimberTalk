# Prüft, dass /api/health Backend und Datenbank meldet und das Frontend mit allen Reitern
# ausgeliefert wird.

import os

# Für den Test eine Datenbank im Speicher, damit keine Datei auf der Platte entsteht.
os.environ["TIMBERTALK_DATABASE_URL"] = "sqlite://"

from fastapi.testclient import TestClient  # noqa: E402

from timbertalk.main import app  # noqa: E402


def test_health_meldet_backend_und_datenbank() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


# Die Reiter in der Reihenfolge der Leiste. Ein neuer Reiter wird hier ergänzt.
TABS = ["start", "kalender", "projekte", "kunden", "buchungen", "einstellungen"]


def test_startseite_laedt_das_geruest() -> None:
    # index.html ist nur das Gerüst; Reiter und Inhalte kommen aus app.js und reiter.js.
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert '<nav class="tabs"' in response.text
    assert '<script type="module" src="app.js">' in response.text


def test_reiter_start_zeigt_dass_timbertalk_laeuft() -> None:
    with TestClient(app) as client:
        response = client.get("/features/start/start.js")
    assert response.status_code == 200
    assert "TimberTalk läuft" in response.text


def test_jeder_reiter_hat_ein_eigenes_modul() -> None:
    # Zu jedem Reiter gehören eine Zeile in reiter.js und eine Datei features/<id>/<id>.js,
    # die genau diese id exportiert.
    with TestClient(app) as client:
        liste = client.get("/reiter.js").text
        for tab in TABS:
            assert f'"./features/{tab}/{tab}.js"' in liste
            modul = client.get(f"/features/{tab}/{tab}.js")
            assert modul.status_code == 200
            assert f'export const id = "{tab}";' in modul.text
