"""Registry der Service-Operationen; Grundlage für einen späteren MCP-Server.

Jede öffentliche Service-Funktion wird mit `@operation(...)` markiert. Aus der Signatur
wird ein Pydantic-Eingabemodell erzeugt, aus der Rückgabe-Annotation das Ausgabe-Schema.
So lassen sich alle Operationen samt JSON-Schema auflisten, ohne FastAPI zu kennen.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar, cast, get_type_hints

from pydantic import BaseModel, TypeAdapter, create_model

from timbertalk_core.context import ServiceContext
from timbertalk_core.errors import NotFound

F = TypeVar("F", bound=Callable[..., Any])


@dataclass(frozen=True, slots=True)
class Operation:
    """Beschreibung einer Service-Operation für Aufruf und Werkzeug-Katalog."""

    name: str
    read_only: bool
    summary_de: str
    func: Callable[..., Any]
    input_model: type[BaseModel]
    output_type: Any

    @property
    def docstring(self) -> str:
        """Deutscher Docstring der Service-Funktion."""
        return inspect.getdoc(self.func) or ""

    def input_schema(self) -> dict[str, Any]:
        """JSON-Schema der Eingabe (ohne `ServiceContext`)."""
        return TypeAdapter(self.input_model).json_schema()

    def output_schema(self) -> dict[str, Any]:
        """JSON-Schema der Ausgabe."""
        return TypeAdapter(self.output_type).json_schema()

    def describe(self) -> dict[str, Any]:
        """Beschreibt die Operation als Daten (Name, Zweck, Ein- und Ausgabe-Schema)."""
        return {
            "name": self.name,
            "read_only": self.read_only,
            "summary_de": self.summary_de,
            "description_de": self.docstring,
            "input_schema": self.input_schema(),
            "output_schema": self.output_schema(),
        }


_REGISTRY: dict[str, Operation] = {}


def _build_input_model(func: Callable[..., Any], name: str) -> type[BaseModel]:
    """Erzeugt aus der Signatur ein Pydantic-Modell der Eingabeparameter."""
    hints = get_type_hints(func)
    signature = inspect.signature(func)
    fields: dict[str, Any] = {}
    for parameter in signature.parameters.values():
        if parameter.name in {"self", "cls"}:
            continue
        annotation = hints.get(parameter.name, Any)
        if annotation is ServiceContext:
            continue
        default = ... if parameter.default is inspect.Parameter.empty else parameter.default
        fields[parameter.name] = (annotation, default)
    model_name = "".join(part.capitalize() for part in name.replace(".", "_").split("_")) + "Input"
    return cast("type[BaseModel]", create_model(model_name, **fields))


def operation(*, name: str, read_only: bool, summary_de: str) -> Callable[[F], F]:
    """Registriert eine Service-Funktion als benannte Operation.

    Parameter:
        name: eindeutiger Name in Punktschreibweise, z. B. `booking.create`.
        read_only: wahr, wenn die Operation nichts verändert.
        summary_de: ein Satz auf Deutsch, der den Zweck beschreibt.
    """

    def decorator(func: F) -> F:
        if name in _REGISTRY:
            raise ValueError(f"Operation '{name}' ist bereits registriert.")
        hints = get_type_hints(func)
        _REGISTRY[name] = Operation(
            name=name,
            read_only=read_only,
            summary_de=summary_de,
            func=func,
            input_model=_build_input_model(func, name),
            output_type=hints.get("return", type(None)),
        )
        return func

    return decorator


def all_operations() -> list[Operation]:
    """Liefert alle registrierten Operationen, nach Namen sortiert."""
    return [_REGISTRY[key] for key in sorted(_REGISTRY)]


def get_operation(name: str) -> Operation:
    """Liefert eine Operation anhand ihres Namens.

    Parameter:
        name: Name der Operation in Punktschreibweise, z. B. `booking.create`.
    """
    operation_or_none = _REGISTRY.get(name)
    if operation_or_none is None:
        raise NotFound(f"Die Operation '{name}' ist nicht registriert.", operation=name)
    return operation_or_none


def describe_operations() -> list[dict[str, Any]]:
    """Beschreibt alle Operationen als Daten; Grundlage für MCP-Werkzeuge."""
    return [op.describe() for op in all_operations()]
