"""Prüft die Operation-Registry, die später den MCP-Server trägt."""

from __future__ import annotations

import uuid

import pytest
from pydantic import BaseModel

from timbertalk_core import operations as operations_module
from timbertalk_core.context import ServiceContext
from timbertalk_core.operations import (
    all_operations,
    describe_operations,
    get_operation,
    operation,
)
from timbertalk_core.services import import_all_services


class ProbeInput(BaseModel):
    """Eingabe einer Probe-Operation."""

    label: str


class ProbeRead(BaseModel):
    """Ausgabe einer Probe-Operation."""

    id: uuid.UUID
    label: str


@pytest.fixture
def leere_registry() -> object:
    """Registry für den Test leeren und danach wiederherstellen."""
    original = dict(operations_module._REGISTRY)
    operations_module._REGISTRY.clear()
    yield None
    operations_module._REGISTRY.clear()
    operations_module._REGISTRY.update(original)


def test_registrierung_erfasst_schemas(leere_registry: object) -> None:
    @operation(name="probe.create", read_only=False, summary_de="Legt eine Probe an.")
    def create_probe(ctx: ServiceContext, data: ProbeInput) -> ProbeRead:
        """Legt eine Probe an.

        Parameter:
            data: Bezeichnung der Probe.
        """
        return ProbeRead(id=uuid.uuid4(), label=data.label)

    registered = get_operation("probe.create")
    assert registered.read_only is False
    assert registered.summary_de == "Legt eine Probe an."
    assert "Legt eine Probe an." in registered.docstring
    assert registered.output_type is ProbeRead

    eingabe = registered.input_schema()
    assert "ctx" not in str(eingabe)
    assert registered.output_schema()["title"] == "ProbeRead"
    assert all_operations() == [registered]


def test_skalare_parameter_ergeben_ein_eingabemodell(leere_registry: object) -> None:
    @operation(name="probe.list", read_only=True, summary_de="Listet Proben.")
    def list_probes(ctx: ServiceContext, limit: int = 50, offset: int = 0) -> list[ProbeRead]:
        """Listet Proben mit Paging.

        Parameter:
            limit: maximale Anzahl Datensätze.
            offset: Anzahl übersprungener Datensätze.
        """
        return []

    schema = get_operation("probe.list").input_schema()
    assert set(schema["properties"]) == {"limit", "offset"}
    assert schema["properties"]["limit"]["default"] == 50
    assert get_operation("probe.list").output_schema()["type"] == "array"


def test_doppelter_name_wird_abgelehnt(leere_registry: object) -> None:
    @operation(name="probe.doppelt", read_only=True, summary_de="Erste.")
    def erste(ctx: ServiceContext) -> None:
        """Erste Operation."""

    with pytest.raises(ValueError, match="bereits registriert"):

        @operation(name="probe.doppelt", read_only=True, summary_de="Zweite.")
        def zweite(ctx: ServiceContext) -> None:
            """Zweite Operation."""


def test_unbekannte_operation_meldet_fehler(leere_registry: object) -> None:
    with pytest.raises(KeyError, match="nicht registriert"):
        get_operation("gibt.es.nicht")


def test_jede_operation_hat_docstring_und_schemas() -> None:
    """Abnahmekriterium: alle echten Operationen sind vollständig beschrieben."""
    import_all_services()
    for registered in all_operations():
        assert registered.docstring.strip(), f"{registered.name}: Docstring fehlt"
        assert registered.summary_de.strip(), f"{registered.name}: summary_de fehlt"
        assert registered.input_schema()["type"] == "object"
        assert registered.output_schema() is not None
    assert all(isinstance(beschreibung, dict) for beschreibung in describe_operations())
