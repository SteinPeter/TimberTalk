# Prüft, dass die Startseite erscheint und /api/health Backend und Datenbank meldet.

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


def test_startseite_zeigt_dass_timbertalk_laeuft() -> None:
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "TimberTalk läuft" in response.text
