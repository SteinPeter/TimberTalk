# Tests für das Feature „Änderungsprotokoll“ (F11).
# Fixtures aus backend/conftest.py: `client` (Admin), `client_as("<rolle>")`, `session`.

from collections.abc import Callable

from fastapi.testclient import TestClient

from timbertalk.features.audit import service


def test_angaben_lesbar_ohne_passwoerter_und_lange_werte_gekuerzt() -> None:
    body = b'{"display_name": "Max", "start_password": "geheim", "logo": "' + b"x" * 200 + b'"}'
    text = service.describe_body(body)
    assert text.startswith("display_name: Max · start_password: ••• · logo: xxx")
    assert "geheim" not in text
    assert text.endswith("… (gekürzt)")
    assert service.describe_body(b"kein json") == ""
    assert service.describe_target({"material_id": 3}) == "Nr. 3"


def test_preis_aendern_steht_mit_wer_und_was_im_protokoll(client: TestClient) -> None:
    material_id = client.post(
        "/api/materials/items", json={"name": "KVH C24", "unit": "m³"}
    ).json()["id"]
    client.post(
        f"/api/materials/items/{material_id}/prices",
        json={"unit_price": "520.00", "valid_from": "2026-12-01"},
    )
    client.post("/api/materials/items", json={"name": " ", "unit": "m"})  # abgelehnt: nicht im Log

    events = client.get("/api/audit").json()
    assert [(e["area"], e["action"], e["target"]) for e in events] == [
        ("Material, Fahrten und Preise", "Preis eintragen", f"Nr. {material_id}"),
        ("Material, Fahrten und Preise", "Material anlegen", ""),
    ]
    assert events[0]["details"] == "unit_price: 520.00 · valid_from: 2026-12-01"
    assert events[0]["account_name"] == "Test admin"


def test_konto_anlegen_ohne_startpasswort_im_protokoll(client: TestClient) -> None:
    client.post(
        "/api/accounts",
        json={
            "username": "max",
            "display_name": "Max",
            "role": "journeyman",
            "start_password": "anfang-123",
        },
    )
    event = client.get("/api/audit", params={"area": "Benutzerkonten und Rechte"}).json()[0]
    assert event["action"] == "Konto anlegen"
    assert "anfang-123" not in event["details"]
    assert "Benutzerkonten und Rechte" in client.get("/api/audit/areas").json()


def test_anmelden_und_lesen_stehen_nicht_im_protokoll(
    client: TestClient, client_as: Callable[[str], TestClient]
) -> None:
    client_as("journeyman").get("/api/materials/items")  # anmelden (in client_as) und lesen
    assert client.get("/api/audit").json() == []


def test_protokoll_sieht_nur_der_admin(client_as: Callable[[str], TestClient]) -> None:
    assert client_as("office").get("/api/audit").status_code == 403
    assert client_as("journeyman").get("/api/audit").status_code == 403
