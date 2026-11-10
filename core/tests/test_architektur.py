"""Prüft die Architekturregeln aus CLAUDE.md und dem Auftrag.

Diese Tests lesen den Quelltext, statt ihn auszuführen: Sie sollen Verstöße gegen die
Schichtentrennung sofort sichtbar machen, auch wenn der Code funktioniert.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from timbertalk_core.operations import all_operations
from timbertalk_core.services import import_all_services

SRC = Path(__file__).resolve().parents[1] / "src" / "timbertalk_core"
ROUTER_DIR = SRC / "api" / "routers"

VERBOTEN_IN_ROUTERN = {
    "sqlalchemy",
    "timbertalk_core.db",
}
"""Module, die ein Router nicht importieren darf: er greift nie selbst auf die DB zu."""

DB_NAMEN = {"select", "insert", "text", "Session", "sessionmaker", "execute", "scalars"}
"""Bezeichner, die auf direkten Datenbankzugriff hindeuten.

Geprüft werden nur freie Namen, keine Attribute: `router.delete` ist eine HTTP-Methode,
kein SQL.
"""

ERLAUBTE_DOMAENEN_MODULE = (".service", ".schemas", ".details", ".enums")
"""Aus einer Domäne darf ein Router nur diese Module verwenden."""


def _module_dateien(ordner: Path) -> list[Path]:
    return sorted(pfad for pfad in ordner.rglob("*.py") if pfad.name != "__init__.py")


def _importierte_module(baum: ast.Module) -> set[str]:
    module: set[str] = set()
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Import):
            module.update(alias.name for alias in knoten.names)
        elif isinstance(knoten, ast.ImportFrom) and knoten.module:
            module.add(knoten.module)
    return module


@pytest.mark.parametrize("router_datei", _module_dateien(ROUTER_DIR), ids=lambda pfad: pfad.name)
def test_router_enthalten_keine_datenbankzugriffe(router_datei: Path) -> None:
    """Abnahmekriterium: kein Router enthält Datenbankzugriffe."""
    baum = ast.parse(router_datei.read_text(encoding="utf-8"))

    for modul in _importierte_module(baum):
        for verboten in VERBOTEN_IN_ROUTERN:
            assert not (modul == verboten or modul.startswith(f"{verboten}.")), (
                f"{router_datei.name} importiert '{modul}'; Router dürfen nicht auf die "
                "Datenbankschicht zugreifen."
            )

    freie_namen = {knoten.id for knoten in ast.walk(baum) if isinstance(knoten, ast.Name)}
    treffer = freie_namen & DB_NAMEN
    assert not treffer, f"{router_datei.name} nutzt Datenbank-Namen: {sorted(treffer)}"


@pytest.mark.parametrize("router_datei", _module_dateien(ROUTER_DIR), ids=lambda pfad: pfad.name)
def test_router_rufen_nur_services(router_datei: Path) -> None:
    """Router importieren Geschäftslogik ausschließlich aus Service- und Schema-Modulen."""
    baum = ast.parse(router_datei.read_text(encoding="utf-8"))
    for knoten in ast.walk(baum):
        if not isinstance(knoten, ast.ImportFrom) or not knoten.module:
            continue
        if not knoten.module.startswith("timbertalk_core.domain."):
            continue
        for alias in knoten.names:
            vollstaendig = f"{knoten.module}.{alias.name}"
            erlaubt = knoten.module.endswith(ERLAUBTE_DOMAENEN_MODULE) or vollstaendig.endswith(
                ERLAUBTE_DOMAENEN_MODULE
            )
            assert erlaubt, (
                f"{router_datei.name} importiert '{vollstaendig}'; aus einer Domäne darf ein "
                "Router nur service, schemas, details oder enums verwenden, keine Modelle "
                "oder Repositories."
            )


def test_services_kennen_kein_fastapi() -> None:
    """Services müssen ohne FastAPI nutzbar sein, damit ein MCP-Server sie direkt rufen kann."""
    for datei in _module_dateien(SRC / "domain"):
        baum = ast.parse(datei.read_text(encoding="utf-8"))
        for modul in _importierte_module(baum):
            assert not modul.startswith(("fastapi", "starlette")), (
                f"{datei.relative_to(SRC)} importiert '{modul}'; die Service-Schicht darf "
                "FastAPI nicht kennen."
            )


def test_jede_domaene_hat_die_erwarteten_module() -> None:
    """Jede Domäne ist ein eigenes Paket mit Modell, Schema, Repository und Service."""
    ohne_modelle = {"audit"}  # Audit hat Modelle, aber keine schreibenden Services
    for domaene in sorted(pfad for pfad in (SRC / "domain").iterdir() if pfad.is_dir()):
        if domaene.name == "__pycache__":
            continue
        dateien = {pfad.name for pfad in domaene.glob("*.py")}
        assert "models.py" in dateien, f"{domaene.name}: models.py fehlt"
        assert "schemas.py" in dateien, f"{domaene.name}: schemas.py fehlt"
        assert "service.py" in dateien, f"{domaene.name}: service.py fehlt"
        if domaene.name not in ohne_modelle:
            assert "repository.py" in dateien, f"{domaene.name}: repository.py fehlt"


def test_kein_float_fuer_geld_oder_mengen() -> None:
    """Geld und Mengen dürfen nirgends als `float` modelliert sein."""
    for datei in _module_dateien(SRC):
        quelltext = datei.read_text(encoding="utf-8")
        baum = ast.parse(quelltext)
        for knoten in ast.walk(baum):
            if isinstance(knoten, ast.Name) and knoten.id == "Float":
                pytest.fail(f"{datei.relative_to(SRC)} nutzt den Spaltentyp Float")
            if (
                isinstance(knoten, ast.AnnAssign)
                and isinstance(knoten.annotation, ast.Subscript)
                and "float" in ast.unparse(knoten.annotation)
                and "Mapped" in ast.unparse(knoten.annotation)
            ):
                pytest.fail(f"{datei.relative_to(SRC)} bildet eine Spalte auf float ab")


def test_alle_operationen_sind_vollstaendig_beschrieben() -> None:
    """Abnahmekriterium: operations.py listet alle Operationen mit Schemas."""
    import_all_services()
    operationen = all_operations()
    assert len(operationen) >= 80

    for operation in operationen:
        assert operation.docstring.strip(), f"{operation.name}: Docstring fehlt"
        assert operation.summary_de.strip(), f"{operation.name}: summary_de fehlt"
        eingabe = operation.input_schema()
        assert eingabe["type"] == "object"
        assert "ctx" not in eingabe.get("properties", {})
        assert operation.output_schema() is not None

    # Namen sind eindeutig und in Punktschreibweise.
    namen = [operation.name for operation in operationen]
    assert len(namen) == len(set(namen))
    assert all("." in name for name in namen)


def test_schreibende_operationen_sind_als_solche_gekennzeichnet() -> None:
    """Lesende und schreibende Operationen müssen korrekt markiert sein."""
    import_all_services()
    for operation in all_operations():
        schreibend_nach_namen = any(
            teil in operation.name
            for teil in (".create", ".update", ".delete", ".set", ".confirm", ".cancel", ".record")
        )
        if schreibend_nach_namen:
            assert not operation.read_only, f"{operation.name} müsste schreibend sein"
        if operation.name.endswith((".get", ".list", ".summary", ".resolve")):
            assert operation.read_only, f"{operation.name} müsste lesend sein"
