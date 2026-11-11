"""Prüft die REST-API: Lebenszyklus je Domäne, Problem-JSON und OpenAPI."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from conftest import TEST_API_KEY

PROBLEM = "application/problem+json"


def _ok(response: Any, erwartet: int = 200) -> dict[str, Any]:
    assert response.status_code == erwartet, response.text
    daten = response.json()
    assert isinstance(daten, dict)
    return daten


@pytest.fixture
def stammdaten(client: TestClient) -> dict[str, Any]:
    """Legt über die API Einheiten, Kostenarten, einen Kunden und ein Projekt an."""
    for code, label, decimals in [("h", "Stunde", 2), ("m3", "Kubikmeter", 3), ("tag", "Tag", 2)]:
        _ok(
            client.post("/units", json={"code": code, "label_de": label, "decimals": decimals}),
            201,
        )
    lohn = _ok(
        client.post(
            "/cost-types",
            json={
                "code": "labor_master",
                "name_de": "Lohn Meister",
                "kind": "labor",
                "default_unit_code": "h",
                "default_unit_price": "68.5000",
                "labor_share": True,
            },
        ),
        201,
    )
    mitarbeiter = _ok(
        client.post("/employees", json={"first_name": "Max", "last_name": "Holz", "role": "master"}),
        201,
    )
    kunde = _ok(
        client.post(
            "/customers",
            json={
                "customer_type": "private",
                "first_name": "Eva",
                "last_name": "Reich",
                "city": "Berlin",
            },
        ),
        201,
    )
    projekt = _ok(
        client.post("/projects", json={"customer_id": kunde["id"], "title": "Dachgaube"}),
        201,
    )
    return {
        "labor_id": lohn["id"],
        "employee_id": mitarbeiter["id"],
        "customer_id": kunde["id"],
        "project_id": projekt["id"],
    }


# --------------------------------------------------------------------------- Grundlagen


def test_health_braucht_keinen_schluessel(app: Any) -> None:
    with TestClient(app) as roher_client:
        antwort = roher_client.get("/health")
    assert antwort.status_code == 200


def test_ohne_schluessel_abgelehnt(app: Any) -> None:
    with TestClient(app) as roher_client:
        antwort = roher_client.get("/units")
    assert antwort.status_code == 403
    assert antwort.headers["content-type"].startswith(PROBLEM)
    assert antwort.json()["code"] == "permission_denied"


def test_falscher_schluessel_abgelehnt(app: Any) -> None:
    with TestClient(app) as roher_client:
        antwort = roher_client.get("/units", headers={"X-API-Key": "falsch"})
    assert antwort.status_code == 403


def test_openapi_ist_vollstaendig(client: TestClient) -> None:
    schema = _ok(client.get("/openapi.json"))
    pfade = schema["paths"]
    for pfad in [
        "/health",
        "/company",
        "/settings",
        "/tax-rates",
        "/units",
        "/cost-types",
        "/custom-fields",
        "/employees",
        "/customers",
        "/projects",
        "/work-packages",
        "/work-package-dependencies",
        "/material-items",
        "/prices",
        "/bookings",
        "/bookings/detail-schemas",
        "/bookings/{booking_id}/confirm",
        "/bookings/{booking_id}/cancel",
        "/attachments",
        "/model-prices",
        "/usage",
        "/usage/summary",
        "/audit-events",
        "/operations",
    ]:
        assert pfad in pfade, f"{pfad} fehlt in der OpenAPI-Beschreibung"

    # Jede Route hat eine Zusammenfassung und eine Beschreibung.
    for pfad, methoden in pfade.items():
        for methode, beschreibung in methoden.items():
            assert beschreibung.get("summary"), f"{methode.upper()} {pfad}: summary fehlt"
            assert beschreibung.get("description"), f"{methode.upper()} {pfad}: Beschreibung fehlt"


# --------------------------------------------------------------------------- Lebenszyklen


def test_einheit_lebenszyklus(client: TestClient) -> None:
    angelegt = _ok(client.post("/units", json={"code": "km", "label_de": "Kilometer"}), 201)
    unit_id = angelegt["id"]
    assert angelegt["version"] == 1

    assert _ok(client.get(f"/units/{unit_id}"))["code"] == "km"
    assert _ok(client.get("/units/by-code/km"))["id"] == unit_id

    seite = _ok(client.get("/units", params={"limit": 10, "offset": 0}))
    assert seite["total"] == 1
    assert seite["limit"] == 10
    assert seite["offset"] == 0

    geaendert = _ok(
        client.patch(f"/units/{unit_id}", json={"label_de": "km"}, params={"expected_version": 1})
    )
    assert geaendert["label_de"] == "km"
    assert geaendert["version"] == 2

    gelöscht = _ok(client.delete(f"/units/{unit_id}"))
    assert gelöscht["deleted_at"] is not None
    assert _ok(client.get("/units"))["total"] == 0
    assert client.get(f"/units/{unit_id}").status_code == 404


def test_firmendaten_und_einstellungen(client: TestClient) -> None:
    assert client.get("/company").status_code == 404
    angelegt = _ok(client.put("/company", json={"name": "Zimmerei Muster GmbH", "city": "Berlin"}))
    assert angelegt["city"] == "Berlin"
    assert _ok(client.get("/company"))["name"] == "Zimmerei Muster GmbH"

    _ok(
        client.put(
            "/settings",
            json={"key": "default_hourly_rate", "value": {"amount": "68.50"}},
        )
    )
    assert _ok(client.get("/settings/default_hourly_rate"))["value"] == {"amount": "68.50"}
    assert _ok(client.get("/settings"))["total"] == 1
    _ok(client.delete("/settings/default_hourly_rate"))
    assert client.get("/settings/default_hourly_rate").status_code == 404


def test_steuersatz_lebenszyklus(client: TestClient) -> None:
    angelegt = _ok(
        client.post(
            "/tax-rates",
            json={
                "code": "19",
                "percent": "19",
                "label_de": "Umsatzsteuer 19 %",
                "valid_from": "2021-01-01",
            },
        ),
        201,
    )
    assert (
        _ok(client.get("/tax-rates/for-date", params={"code": "19", "on_date": "2026-05-01"}))["id"]
        == angelegt["id"]
    )
    assert (
        client.get("/tax-rates/for-date", params={"code": "19", "on_date": "2020-01-01"}).status_code == 404
    )
    _ok(client.delete(f"/tax-rates/{angelegt['id']}"))


def test_kunde_und_projekt_lebenszyklus(client: TestClient) -> None:
    kunde = _ok(
        client.post(
            "/customers",
            json={"customer_type": "business", "company_name": "Holzbau Nord GmbH"},
        ),
        201,
    )
    assert kunde["display_name"] == "Holzbau Nord GmbH"

    projekt = _ok(client.post("/projects", json={"customer_id": kunde["id"], "title": "Carport"}), 201)
    assert projekt["number"].endswith("-001")
    assert _ok(client.get(f"/projects/by-number/{projekt['number']}"))["id"] == projekt["id"]

    paket = _ok(
        client.post("/work-packages", json={"project_id": projekt["id"], "title": "Fundament"}),
        201,
    )
    zweites = _ok(
        client.post("/work-packages", json={"project_id": projekt["id"], "title": "Aufstellen"}),
        201,
    )
    abhaengigkeit = _ok(
        client.post(
            "/work-package-dependencies",
            json={"predecessor_id": paket["id"], "successor_id": zweites["id"]},
        ),
        201,
    )
    assert _ok(client.get("/work-package-dependencies"))["total"] == 1

    ringschluss = client.post(
        "/work-package-dependencies",
        json={"predecessor_id": zweites["id"], "successor_id": paket["id"]},
    )
    assert ringschluss.status_code == 409
    assert "Ringschluss" in ringschluss.json()["detail"]

    _ok(client.delete(f"/work-package-dependencies/{abhaengigkeit['id']}"))
    _ok(client.patch(f"/projects/{projekt['id']}", json={"status": "active"}))
    assert _ok(client.get("/projects", params={"status": "active"}))["total"] == 1
    _ok(client.delete(f"/projects/{projekt['id']}"))
    assert _ok(client.get("/projects"))["total"] == 0


def test_katalog_und_preise(client: TestClient, stammdaten: dict[str, Any]) -> None:
    _ok(
        client.post(
            "/cost-types",
            json={
                "code": "material_timber",
                "name_de": "Holz",
                "kind": "material",
                "default_unit_code": "m3",
            },
        ),
        201,
    )
    artikel = _ok(
        client.post(
            "/material-items",
            json={
                "name": "KVH Fichte C24 60×200",
                "category": "timber",
                "unit_code": "m3",
                "cost_type_code": "material_timber",
                "sku": "KVH-60200",
            },
        ),
        201,
    )
    _ok(
        client.post(
            "/prices",
            json={
                "target_type": "material_item",
                "target_id": artikel["id"],
                "unit_price": "489.5000",
                "valid_from": "2026-01-01",
                "note": "Platzhalterpreis",
            },
        ),
        201,
    )
    ermittelt = _ok(
        client.get(
            "/prices/resolve",
            params={
                "target_type": "material_item",
                "target_id": artikel["id"],
                "on_date": "2026-05-01",
            },
        )
    )
    assert ermittelt["unit_price"] == "489.5000"
    assert ermittelt["origin"] == "price_material_item"

    ueberlappend = client.post(
        "/prices",
        json={
            "target_type": "material_item",
            "target_id": artikel["id"],
            "unit_price": "500.00",
            "valid_from": "2026-06-01",
        },
    )
    assert ueberlappend.status_code == 409
    assert _ok(client.get("/material-items", params={"search": "kvh"}))["total"] == 1


def test_buchung_lebenszyklus(client: TestClient, stammdaten: dict[str, Any]) -> None:
    buchung = _ok(
        client.post(
            "/bookings",
            json={
                "project_id": stammdaten["project_id"],
                "cost_type_id": stammdaten["labor_id"],
                "booking_date": "2026-05-04",
                "quantity": "8.50",
                "employee_id": stammdaten["employee_id"],
                "details": {"start_time": "07:00", "end_time": "16:00", "break_minutes": 30},
            },
        ),
        201,
    )
    assert buchung["status"] == "draft"
    assert buchung["unit_code"] == "h"
    assert buchung["effective_unit_price"] == "68.5000"
    assert buchung["amount"] == "582.250000"

    bestaetigt = _ok(client.post(f"/bookings/{buchung['id']}/confirm"))
    assert bestaetigt["status"] == "confirmed"
    assert bestaetigt["confirmed_at"] is not None

    storniert = _ok(client.post(f"/bookings/{buchung['id']}/cancel"))
    assert storniert["status"] == "cancelled"

    nicht_mehr = client.patch(f"/bookings/{buchung['id']}", json={"quantity": "1.00"})
    assert nicht_mehr.status_code == 409
    assert nicht_mehr.json()["code"] == "invalid_state"

    assert _ok(client.get("/bookings", params={"status": "cancelled"}))["total"] == 1
    assert _ok(client.get("/bookings/kinds"))["labor"] == "LaborDetails"

    schemas = _ok(client.get("/bookings/detail-schemas"))
    assert set(schemas) == set(_ok(client.get("/bookings/kinds")))
    assert set(schemas["labor"]["properties"]) == {"start_time", "end_time", "break_minutes"}
    assert schemas["equipment"]["required"] == ["equipment_name"]


def test_agent_darf_nicht_bestaetigen(
    client: TestClient, agent_client: TestClient, stammdaten: dict[str, Any]
) -> None:
    """Abnahmekriterium über die API: source=agent ist draft, agent darf nicht bestätigen."""
    buchung = _ok(
        agent_client.post(
            "/bookings",
            json={
                "project_id": stammdaten["project_id"],
                "cost_type_id": stammdaten["labor_id"],
                "booking_date": "2026-05-04",
                "quantity": "4.00",
                "employee_id": stammdaten["employee_id"],
                "source": "agent",
                "source_ref": "transkript-7",
            },
        ),
        201,
    )
    assert buchung["status"] == "draft"
    assert buchung["source"] == "agent"

    abgelehnt = agent_client.post(f"/bookings/{buchung['id']}/confirm")
    assert abgelehnt.status_code == 403
    assert abgelehnt.json()["code"] == "permission_denied"

    # Derselbe Datensatz, aber ein Mensch: erlaubt.
    assert _ok(client.post(f"/bookings/{buchung['id']}/confirm"))["status"] == "confirmed"


def test_ohne_akteur_art_darf_nicht_bestaetigt_werden(
    app: Any, client: TestClient, stammdaten: dict[str, Any]
) -> None:
    """Fehlt `X-Actor-Type`, gilt `system`: Bestätigen bleibt dem Menschen vorbehalten."""
    buchung = _ok(
        client.post(
            "/bookings",
            json={
                "project_id": stammdaten["project_id"],
                "cost_type_id": stammdaten["labor_id"],
                "booking_date": "2026-05-04",
                "quantity": "4.00",
                "employee_id": stammdaten["employee_id"],
            },
        ),
        201,
    )

    with TestClient(app) as roher_client:
        abgelehnt = roher_client.post(
            f"/bookings/{buchung['id']}/confirm", headers={"X-API-Key": TEST_API_KEY}
        )
    assert abgelehnt.status_code == 403
    assert abgelehnt.json()["code"] == "permission_denied"
    assert _ok(client.get(f"/bookings/{buchung['id']}"))["status"] == "draft"


def test_anhaenge_und_verbrauch(client: TestClient, stammdaten: dict[str, Any]) -> None:
    anhang = _ok(
        client.post(
            "/attachments",
            json={
                "entity_type": "projects",
                "entity_id": stammdaten["project_id"],
                "file_path": "attachments/2026/05/foto.jpg",
                "mime_type": "image/jpeg",
                "size_bytes": 1234,
                "sha256": "b" * 64,
                "kind": "photo",
            },
        ),
        201,
    )
    assert _ok(client.get("/attachments", params={"entity_type": "projects"}))["total"] == 1

    heraus = client.post(
        "/attachments",
        json={
            "entity_type": "projects",
            "entity_id": stammdaten["project_id"],
            "file_path": "../../raus.jpg",
            "mime_type": "image/jpeg",
            "size_bytes": 1,
            "sha256": "c" * 64,
            "kind": "photo",
        },
    )
    assert heraus.status_code == 422
    assert "file_path" in heraus.json()["errors"]

    _ok(
        client.post(
            "/model-prices",
            json={
                "provider": "anthropic",
                "model": "claude-opus-5",
                "input_per_mtok": "12.0000",
                "output_per_mtok": "60.0000",
                "valid_from": "2026-01-01",
            },
        ),
        201,
    )
    verbrauch = _ok(
        client.post(
            "/usage",
            json={
                "provider": "anthropic",
                "model": "claude-opus-5",
                "module": "a",
                "feature": "voice_booking",
                "input_tokens": 1500,
                "output_tokens": 800,
                "project_id": stammdaten["project_id"],
                "occurred_at": "2026-05-04T10:00:00Z",
            },
        ),
        201,
    )
    assert verbrauch["cost"] == "0.066000"

    uebersicht = _ok(client.get("/usage/summary", params={"period": "month", "group_by": "model"}))
    assert uebersicht["rows"][0]["period"] == "2026-05"
    assert uebersicht["total_cost"] == "0.066000"
    _ok(client.delete(f"/attachments/{anhang['id']}"))


def test_aenderungsprotokoll_ueber_api(client: TestClient, stammdaten: dict[str, Any]) -> None:
    protokoll = _ok(client.get("/audit-events", params={"entity_type": "projects", "action": "create"}))
    assert protokoll["total"] == 1
    eintrag = protokoll["items"][0]
    assert eintrag["actor_type"] == "user"
    assert eintrag["source"] == "manual"
    assert "title" in eintrag["changes"]
    assert _ok(client.get(f"/audit-events/{eintrag['id']}"))["id"] == eintrag["id"]


def test_operationen_katalog(client: TestClient) -> None:
    alle = client.get("/operations")
    assert alle.status_code == 200
    katalog = alle.json()
    assert len(katalog) >= 80
    namen = {eintrag["name"] for eintrag in katalog}
    assert {"booking.create", "booking.confirm", "price.resolve", "usage.summary"} <= namen

    eine = _ok(client.get("/operations/booking.create"))
    assert eine["read_only"] is False
    assert eine["input_schema"]["type"] == "object"
    assert eine["description_de"]
    nur_lesend = client.get("/operations", params={"read_only": True}).json()
    assert all(eintrag["read_only"] for eintrag in nur_lesend)
    assert client.get("/operations/gibt.es.nicht").status_code == 404


# --------------------------------------------------------------------------- Fehlerform


def test_problem_json_bei_nicht_gefunden(client: TestClient) -> None:
    antwort = client.get(f"/units/{uuid.uuid4()}")
    assert antwort.status_code == 404
    assert antwort.headers["content-type"].startswith(PROBLEM)
    koerper = antwort.json()
    assert koerper["code"] == "not_found"
    assert koerper["status"] == 404
    assert koerper["title"] == "Nicht gefunden"
    assert "nicht gefunden" in koerper["detail"]
    assert koerper["type"].endswith("/not_found")


def test_problem_json_bei_ungueltiger_eingabe(client: TestClient) -> None:
    antwort = client.post("/units", json={"code": "", "label_de": ""})
    assert antwort.status_code == 422
    koerper = antwort.json()
    assert koerper["code"] == "validation_failed"
    assert "code" in koerper["errors"]


def test_problem_json_bei_doppeltem_code(client: TestClient) -> None:
    _ok(client.post("/units", json={"code": "stk", "label_de": "Stück"}), 201)
    antwort = client.post("/units", json={"code": "stk", "label_de": "Stück"})
    assert antwort.status_code == 409
    assert antwort.json()["code"] == "conflict"


def test_versionskonflikt_ueber_api(client: TestClient) -> None:
    angelegt = _ok(client.post("/units", json={"code": "kg", "label_de": "Kilogramm"}), 201)
    antwort = client.patch(
        f"/units/{angelegt['id']}",
        json={"label_de": "Kilo"},
        params={"expected_version": 99},
    )
    assert antwort.status_code == 409
    assert antwort.json()["code"] == "conflict"


def test_unbekannte_akteur_art_wird_abgelehnt(app: Any) -> None:
    with TestClient(app) as roher_client:
        antwort = roher_client.get("/units", headers={"X-API-Key": TEST_API_KEY, "X-Actor-Type": "roboter"})
    assert antwort.status_code == 422
    assert "X-Actor-Type" in antwort.json()["errors"]


def test_fehlerhafte_akteur_kennung_wird_abgelehnt(app: Any) -> None:
    with TestClient(app) as roher_client:
        antwort = roher_client.get("/units", headers={"X-API-Key": TEST_API_KEY, "X-Actor": "keine-uuid"})
    assert antwort.status_code == 422
    assert "X-Actor" in antwort.json()["errors"]


def test_korrelations_kennung_wird_uebernommen(client: TestClient) -> None:
    korrelation = str(uuid.uuid4())
    _ok(
        client.post(
            "/units",
            json={"code": "lfm", "label_de": "Laufmeter"},
            headers={"X-Correlation-Id": korrelation},
        ),
        201,
    )
    protokoll = _ok(client.get("/audit-events", params={"correlation_id": korrelation}))
    assert protokoll["total"] == 1


def test_fehler_verwirft_die_transaktion(client: TestClient) -> None:
    """Nach einem Fehler darf nichts halb geschrieben sein."""
    antwort = client.post(
        "/cost-types",
        json={
            "code": "ohne_einheit",
            "name_de": "Ohne Einheit",
            "kind": "other",
            "default_unit_code": "gibtsnicht",
        },
    )
    assert antwort.status_code == 404
    assert _ok(client.get("/cost-types"))["total"] == 0
    assert _ok(client.get("/audit-events"))["total"] == 0
