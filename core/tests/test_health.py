"""Prüft den Gesundheitsendpunkt."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_antwortet_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_openapi_wird_erzeugt(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "/health" in response.json()["paths"]
