"""Gemeinsame Schema-Bausteine: Geld- und Mengentypen sowie Listen-Umschlag."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from timbertalk_core.db.types import MAX_SCALE, to_decimal


def _strict_decimal(value: Any) -> Any:
    """Weist Gleitkommazahlen ab und wandelt Zeichenketten verlustfrei in `Decimal`."""
    if isinstance(value, Decimal | int) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        return to_decimal(value)
    if isinstance(value, float):
        raise ValueError(
            "Gleitkommazahlen sind für Geld und Mengen nicht erlaubt; "
            "bitte als Zeichenkette oder Decimal übergeben."
        )
    return value


MoneyValue = Annotated[
    Decimal,
    BeforeValidator(_strict_decimal),
    Field(max_digits=18, decimal_places=MAX_SCALE),
]
"""Geldbetrag; niemals `float`, höchstens sechs Nachkommastellen."""

QuantityValue = Annotated[
    Decimal,
    BeforeValidator(_strict_decimal),
    Field(max_digits=18, decimal_places=MAX_SCALE),
]
"""Menge; niemals `float`, höchstens sechs Nachkommastellen."""

Attributes = Annotated[dict[str, Any], Field(default_factory=dict)]
"""Zusatzfelder laut `custom_field_definitions`."""


class BaseSchema(BaseModel):
    """Grundlage aller Schemas; liest auch aus ORM-Objekten."""

    model_config = ConfigDict(from_attributes=True, extra="forbid", str_strip_whitespace=True)


class Page[ItemT](BaseModel):
    """Eine Seite einer Liste samt Gesamtzahl."""

    items: list[ItemT]
    total: int = Field(description="Gesamtzahl der Treffer ohne Paging")
    limit: int = Field(description="Maximale Seitengröße")
    offset: int = Field(description="Anzahl übersprungener Datensätze")
