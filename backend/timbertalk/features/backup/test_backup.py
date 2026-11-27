# Tests für das Feature „Datensicherung, Wiederherstellung und Export“: Einstellungen exportieren
# und importieren.
# Fixtures aus backend/conftest.py: `session` für service.py, `client` für api.py.
# Jeder Test bekommt eine eigene, leere Datenbank.

from collections.abc import Callable
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

from timbertalk.db import IN_MEMORY_URL, make_engine
from timbertalk.features.backup import service
from timbertalk.features.backup.models import SettingsFile
from timbertalk.features.materials import service as materials
from timbertalk.features.materials.models import CompanyIn
from timbertalk.features.planning import service as planning
from timbertalk.features.planning.models import ResourceIn


def _fill(session: Session) -> None:
    """Ein kleiner Betrieb: Firma, ein Stundensatz, ein Material mit zwei Preisen, ein Fahrzeug."""
    materials.save_company(session, CompanyIn(company_name="Zimmerei Schulz", iban="DE02 1203"))
    materials.save_hourly_rate(session, "Geselle", Decimal("58.50"))
    kvh = materials.create_material(session, "KVH 60x120", "Bauholz", "m")
    materials.add_price(session, kvh.id, Decimal("4.20"), date(2026, 1, 1))
    materials.add_price(session, kvh.id, Decimal("4.45"), date(2026, 7, 1))
    van = planning.create_resource(session, ResourceIn(name="Transporter"))
    planning.set_vehicle_rate(session, van.id, Decimal("0.55"))


def test_export_enthaelt_alle_einstellungen(session: Session) -> None:
    _fill(session)
    exported = service.export_settings(session)
    assert exported.company.company_name == "Zimmerei Schulz"
    assert [(r.name, r.rate) for r in exported.hourly_rates] == [("Geselle", Decimal("58.50"))]
    [kvh] = exported.materials
    assert (kvh.name, kvh.category, kvh.unit) == ("KVH 60x120", "Bauholz", "m")
    assert [p.unit_price for p in kvh.prices] == [Decimal("4.20"), Decimal("4.45")]
    assert [(r.name, r.rate_per_km) for r in exported.resources] == [
        ("Transporter", Decimal("0.55"))
    ]


def test_import_in_leeren_betrieb_ergibt_dieselben_einstellungen(session: Session) -> None:
    _fill(session)
    text = service.export_settings(session).model_dump_json()
    # Ein zweiter, leerer Betrieb: eine eigene Datenbank.
    other_engine = make_engine(IN_MEMORY_URL)
    SQLModel.metadata.create_all(other_engine)
    with Session(other_engine) as other:
        result = service.import_settings(other, SettingsFile.model_validate_json(text))
        assert (result.materials_new, result.prices_new, result.resources_new) == (1, 2, 1)
        again = service.export_settings(other)
    original = service.export_settings(session)
    skip = {"exported_at"}
    assert again.model_dump(exclude=skip) == original.model_dump(exclude=skip)


def test_import_ergaenzt_nur_und_ist_wiederholbar(session: Session) -> None:
    _fill(session)
    own = materials.create_material(session, "Schrauben 6x80", "Kleinteile", "Stk")
    data = service.export_settings(session)
    data.materials = [m for m in data.materials if m.name != own.name]  # fehlt in der Datei
    data.materials[0].prices.append(
        data.materials[0].prices[0].model_copy(update={"valid_from": date(2027, 1, 1)})
    )

    result = service.import_settings(session, data)
    assert (result.materials_new, result.prices_new, result.resources_new) == (0, 1, 0)
    names = [m.name for m in materials.list_materials(session)]
    assert names == ["KVH 60x120", "Schrauben 6x80"]  # nichts gelöscht
    second = service.import_settings(session, data)
    assert (second.materials_new, second.prices_new) == (0, 0)  # nichts doppelt


def test_falsche_datei_wird_abgelehnt(session: Session) -> None:
    with pytest.raises(ValueError, match="keine Einstellungs-Datei"):
        service.import_settings(session, SettingsFile(format="etwas-anderes"))
    with pytest.raises(ValueError, match="neueren"):
        service.import_settings(session, SettingsFile(version=99))


def test_api_nur_mit_recht_finanzen_aendern(
    client: TestClient, client_as: Callable[[str], TestClient]
) -> None:
    exported = client.get("/api/backup/settings")
    assert exported.status_code == 200
    assert exported.json()["format"] == "timbertalk-einstellungen"
    assert client.post("/api/backup/settings", json=exported.json()).status_code == 200
    geselle = client_as("journeyman")
    assert geselle.get("/api/backup/settings").status_code == 403
    assert geselle.post("/api/backup/settings", json=exported.json()).status_code == 403
    assert client.post("/api/backup/settings", json={"format": "x"}).status_code == 422
