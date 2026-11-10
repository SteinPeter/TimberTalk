"""Art-spezifische Detailfelder einer Buchung samt Registry.

Eine neue Buchungsart braucht genau zwei Dinge: ein Pydantic-Schema und eine
Registrierung über `@register_details`. Weder die Tabelle noch der Service ändern sich.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import time
from typing import Any, Self, TypeVar

from pydantic import Field, model_validator

from timbertalk_core.domain.enums import CostTypeKind, DistanceMethod
from timbertalk_core.errors import ValidationFailed
from timbertalk_core.schemas import BaseSchema, QuantityValue


class BookingDetails(BaseSchema):
    """Grundlage aller Detail-Schemas."""


class LaborDetails(BookingDetails):
    """Details einer Stundenbuchung."""

    start_time: time | None = Field(default=None, description="Beginn der Arbeitszeit")
    end_time: time | None = Field(default=None, description="Ende der Arbeitszeit")
    break_minutes: int = Field(default=0, ge=0, le=1440, description="Pause in Minuten")

    @model_validator(mode="after")
    def _check_times(self) -> Self:
        """Stellt sicher, dass das Ende nach dem Beginn liegt, wenn beides angegeben ist."""
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValueError("Das Ende der Arbeitszeit muss nach dem Beginn liegen.")
        return self


class TravelDetails(BookingDetails):
    """Details einer Fahrtbuchung."""

    from_label: str | None = Field(default=None, max_length=200, description="Startpunkt")
    to_label: str | None = Field(default=None, max_length=200, description="Ziel")
    distance_method: DistanceMethod = Field(default=DistanceMethod.MANUAL, description="manual oder route")
    round_trip: bool = Field(default=False, description="Wahr bei Hin- und Rückfahrt")
    vehicle: str | None = Field(default=None, max_length=100, description="Fahrzeug")


class MaterialDetails(BookingDetails):
    """Details einer Materialbuchung."""

    delivery_note_ref: str | None = Field(default=None, max_length=100, description="Lieferscheinnummer")


class EquipmentDetails(BookingDetails):
    """Details einer Gerätebuchung, z. B. Kran oder Gerüst."""

    equipment_name: str = Field(min_length=1, max_length=150, description="Bezeichnung des Geräts")
    hours_or_days: QuantityValue | None = Field(
        default=None, description="Nutzungsdauer in Stunden oder Tagen"
    )


class OtherDetails(BookingDetails):
    """Details sonstiger Buchungen; ohne Pflichtfelder."""


_REGISTRY: dict[CostTypeKind, type[BookingDetails]] = {}

DetailsT = TypeVar("DetailsT", bound=BookingDetails)


def register_details(kind: CostTypeKind) -> Callable[[type[DetailsT]], type[DetailsT]]:
    """Registriert ein Detail-Schema für eine Buchungsart.

    Parameter:
        kind: Art der Kostenart, für die das Schema gilt.
    """

    def decorator(schema: type[DetailsT]) -> type[DetailsT]:
        if kind in _REGISTRY:
            raise ValueError(f"Für die Art '{kind.value}' ist bereits ein Schema registriert.")
        _REGISTRY[kind] = schema
        return schema

    return decorator


register_details(CostTypeKind.LABOR)(LaborDetails)
register_details(CostTypeKind.TRAVEL)(TravelDetails)
register_details(CostTypeKind.MATERIAL)(MaterialDetails)
register_details(CostTypeKind.EQUIPMENT)(EquipmentDetails)
register_details(CostTypeKind.OTHER)(OtherDetails)


def details_schema(kind: CostTypeKind) -> type[BookingDetails]:
    """Liefert das Detail-Schema einer Buchungsart.

    Parameter:
        kind: Art der Kostenart.
    """
    try:
        return _REGISTRY[kind]
    except KeyError as exc:
        raise ValidationFailed(
            f"Für die Buchungsart '{kind.value}' ist kein Detail-Schema hinterlegt.",
            errors={"details": "unbekannte Buchungsart"},
        ) from exc


def registered_kinds() -> dict[str, str]:
    """Liefert alle registrierten Buchungsarten mit dem Namen ihres Schemas."""
    return {kind.value: schema.__name__ for kind, schema in sorted(_REGISTRY.items())}


def validate_details(kind: CostTypeKind, details: dict[str, Any] | None) -> dict[str, Any]:
    """Prüft die Detailfelder einer Buchung gegen das Schema ihrer Art.

    Parameter:
        kind: Art der Kostenart (`labor`, `material`, `travel`, `equipment`, `other`).
        details: übergebene Detailfelder; `None` wird als leer behandelt.
    """
    schema = details_schema(kind)
    try:
        geprueft = schema.model_validate(details or {})
    except ValueError as exc:
        raise ValidationFailed(
            f"Die Detailfelder für eine Buchung der Art '{kind.value}' sind ungültig: {exc}",
            errors={"details": str(exc)},
        ) from exc
    return geprueft.model_dump(mode="json", exclude_none=True)
