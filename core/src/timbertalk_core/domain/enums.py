"""Fachliche Wertelisten; in der Datenbank als Zeichenketten, geprüft in Pydantic."""

from __future__ import annotations

from enum import StrEnum


class CostTypeKind(StrEnum):
    """Art einer Kostenart; bestimmt, welche Detailfelder einer Buchung gelten."""

    LABOR = "labor"
    MATERIAL = "material"
    TRAVEL = "travel"
    EQUIPMENT = "equipment"
    OTHER = "other"


class CustomFieldDataType(StrEnum):
    """Datentyp eines Zusatzfeldes in `attributes`."""

    TEXT = "text"
    INT = "int"
    DECIMAL = "decimal"
    DATE = "date"
    BOOL = "bool"
    ENUM = "enum"
