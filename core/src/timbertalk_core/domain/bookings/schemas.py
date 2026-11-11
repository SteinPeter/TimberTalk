"""Schemas der Buchungen."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import Field

from timbertalk_core.context import Source
from timbertalk_core.domain.enums import BookingStatus, CostTypeKind
from timbertalk_core.schemas import BaseSchema, MoneyValue, QuantityValue


class BookingCreate(BaseSchema):
    """Neue Buchung; Einträge aus KI oder Import starten immer als `draft`."""

    project_id: uuid.UUID = Field(description="Kennung des Projekts")
    cost_type_id: uuid.UUID = Field(description="Kennung der Kostenart")
    booking_date: date = Field(description="Tag der Leistung")
    quantity: QuantityValue = Field(description="Menge in der angegebenen Einheit")
    unit_code: str | None = Field(
        default=None,
        max_length=20,
        description="Einheit; ohne Angabe wird die Vorgabe-Einheit der Kostenart genutzt",
    )
    work_package_id: uuid.UUID | None = Field(default=None, description="Kennung des Arbeitspakets")
    unit_price: MoneyValue | None = Field(
        default=None, description="Nur setzen, wenn der Preis von der Preisliste abweicht"
    )
    employee_id: uuid.UUID | None = Field(
        default=None, description="Mitarbeiter; Pflicht bei Arbeitszeit (`labor`)"
    )
    material_item_id: uuid.UUID | None = Field(default=None, description="Artikel; nur bei Material sinnvoll")
    description: str | None = Field(default=None, description="Freitext zur Buchung")
    details: dict[str, Any] = Field(
        default_factory=dict, description="Art-spezifische Felder laut Buchungsart"
    )
    source: Source = Field(default=Source.MANUAL, description="Herkunft der Buchung")
    source_ref: str | None = Field(
        default=None, max_length=200, description="Verweis, z. B. Transkript-Kennung"
    )
    attributes: dict[str, Any] = Field(default_factory=dict)


class BookingUpdate(BaseSchema):
    """Änderung einer Buchung; nur gesetzte Felder werden übernommen."""

    work_package_id: uuid.UUID | None = None
    booking_date: date | None = None
    quantity: QuantityValue | None = None
    unit_code: str | None = Field(default=None, max_length=20)
    unit_price: MoneyValue | None = None
    employee_id: uuid.UUID | None = None
    material_item_id: uuid.UUID | None = None
    description: str | None = None
    details: dict[str, Any] | None = None
    attributes: dict[str, Any] | None = None


class BookingRead(BaseSchema):
    """Buchung mit Verwaltungsfeldern und ermitteltem Betrag."""

    id: uuid.UUID
    project_id: uuid.UUID
    work_package_id: uuid.UUID | None
    cost_type_id: uuid.UUID
    cost_type_code: str = Field(description="Code der Kostenart")
    cost_type_kind: CostTypeKind = Field(description="Art der Kostenart")
    booking_date: date
    quantity: QuantityValue
    unit_code: str
    unit_price: MoneyValue | None = Field(description="Abweichender Preis, falls gesetzt")
    effective_unit_price: MoneyValue | None = Field(
        default=None,
        description="Tatsächlich geltender Preis je Einheit; leer, wenn keiner hinterlegt ist",
    )
    amount: MoneyValue | None = Field(
        default=None,
        description="Menge mal geltender Preis, auf sechs Nachkommastellen gerundet; leer ohne Preis",
    )
    price_origin: str | None = Field(
        default=None, description="Herkunft des Preises, z. B. `booking` oder `price_cost_type`"
    )
    employee_id: uuid.UUID | None
    material_item_id: uuid.UUID | None
    description: str | None
    details: dict[str, Any]
    status: BookingStatus
    source: Source
    source_ref: str | None
    confirmed_by: uuid.UUID | None
    confirmed_at: datetime | None
    attributes: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int
