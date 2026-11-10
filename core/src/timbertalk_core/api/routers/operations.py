"""Router für den Katalog der Service-Operationen.

Der Katalog ist die Grundlage eines späteren MCP-Servers: er nennt jede Operation
mit Zweck sowie Ein- und Ausgabe-Schema. Dieser Router liest nur aus der Registry
und greift nicht auf die Datenbank zu.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from timbertalk_core.api.deps import ApiKey
from timbertalk_core.operations import all_operations, describe_operations, get_operation

router = APIRouter(prefix="/operations", tags=["Operationen"])


@router.get("", summary="Operationen auflisten")
def list_operations(_key: ApiKey, read_only: bool | None = None) -> list[dict[str, Any]]:
    """Listet alle Service-Operationen mit Zweck und JSON-Schemas.

    Parameter:
        read_only: wenn gesetzt, werden nur lesende bzw. nur schreibende Operationen geliefert.
    """
    if read_only is None:
        return describe_operations()
    return [operation.describe() for operation in all_operations() if operation.read_only is read_only]


@router.get("/{name}", summary="Eine Operation beschreiben")
def describe_operation(_key: ApiKey, name: str) -> dict[str, Any]:
    """Beschreibt eine Operation anhand ihres Namens, z. B. `booking.create`.

    Parameter:
        name: Name der Operation in Punktschreibweise.
    """
    return get_operation(name).describe()
