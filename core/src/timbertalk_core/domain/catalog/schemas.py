"""Schemas für Materialkatalog und Preise."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Self

from pydantic import Field, model_validator

from timbertalk_core.domain.enums import MaterialCategory, PriceSource, PriceTargetType
from timbertalk_core.schemas import BaseSchema, MoneyValue


class MaterialItemCreate(BaseSchema):
    """Neuer Artikel im Materialkatalog."""

    name: str = Field(min_length=1, max_length=250, description="Bezeichnung des Artikels")
    category: MaterialCategory = Field(description="timber, fasteners, insulation, membrane oder other")
    unit_code: str = Field(min_length=1, max_length=20, description="Einheit der Menge")
    cost_type_code: str = Field(min_length=1, max_length=50, description="Zugehörige Kostenart")
    sku: str | None = Field(default=None, max_length=60, description="Artikelnummer")
    wood_species: str | None = Field(default=None, max_length=60, description="Holzart")
    grade: str | None = Field(default=None, max_length=60, description="Sortierklasse, z. B. C24")
    width_mm: int | None = Field(default=None, gt=0, description="Breite in Millimetern")
    height_mm: int | None = Field(default=None, gt=0, description="Höhe in Millimetern")
    length_mm: int | None = Field(default=None, gt=0, description="Länge in Millimetern")
    notes: str | None = None
    active: bool = True
    attributes: dict[str, Any] = Field(default_factory=dict)


class MaterialItemUpdate(BaseSchema):
    """Änderung eines Artikels; nur gesetzte Felder werden übernommen."""

    name: str | None = Field(default=None, min_length=1, max_length=250)
    category: MaterialCategory | None = None
    unit_code: str | None = Field(default=None, min_length=1, max_length=20)
    cost_type_code: str | None = Field(default=None, min_length=1, max_length=50)
    sku: str | None = Field(default=None, max_length=60)
    wood_species: str | None = Field(default=None, max_length=60)
    grade: str | None = Field(default=None, max_length=60)
    width_mm: int | None = Field(default=None, gt=0)
    height_mm: int | None = Field(default=None, gt=0)
    length_mm: int | None = Field(default=None, gt=0)
    notes: str | None = None
    active: bool | None = None
    attributes: dict[str, object] | None = None


class MaterialItemRead(BaseSchema):
    """Artikel mit Verwaltungsfeldern."""

    id: uuid.UUID
    sku: str | None
    name: str
    category: MaterialCategory
    wood_species: str | None
    grade: str | None
    width_mm: int | None
    height_mm: int | None
    length_mm: int | None
    unit_code: str
    cost_type_code: str
    notes: str | None
    active: bool
    attributes: dict[str, object]
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int


class PriceCreate(BaseSchema):
    """Neuer Preis mit Gültigkeitszeitraum; Holzpreise ändern sich häufig."""

    target_type: PriceTargetType = Field(description="material_item oder cost_type")
    target_id: uuid.UUID = Field(description="Kennung des Artikels bzw. der Kostenart")
    unit_price: MoneyValue = Field(description="Preis je Einheit")
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    valid_from: date = Field(description="Erster Tag der Gültigkeit")
    valid_to: date | None = Field(default=None, description="Letzter Tag der Gültigkeit; leer bedeutet offen")
    source: PriceSource = PriceSource.MANUAL
    note: str | None = Field(default=None, description="Hinweis, z. B. 'Platzhalterpreis'")

    @model_validator(mode="after")
    def _check_period(self) -> Self:
        """Stellt sicher, dass das Ende der Gültigkeit nicht vor dem Beginn liegt."""
        if self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("Das Ende der Gültigkeit darf nicht vor dem Beginn liegen.")
        return self


class PriceUpdate(BaseSchema):
    """Änderung eines Preises; nur gesetzte Felder werden übernommen."""

    unit_price: MoneyValue | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    valid_from: date | None = None
    valid_to: date | None = None
    source: PriceSource | None = None
    note: str | None = None


class PriceRead(BaseSchema):
    """Preis mit Verwaltungsfeldern."""

    id: uuid.UUID
    target_type: PriceTargetType
    target_id: uuid.UUID
    unit_price: MoneyValue
    currency: str
    valid_from: date
    valid_to: date | None
    source: PriceSource
    note: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int


class ResolvedPrice(BaseSchema):
    """Ergebnis der Preisermittlung samt Herkunft der Angabe."""

    unit_price: MoneyValue = Field(description="Ermittelter Preis je Einheit")
    currency: str
    origin: str = Field(
        description=("Herkunft: `price_material_item`, `price_cost_type` oder `cost_type_default`")
    )
    price_id: uuid.UUID | None = Field(
        default=None, description="Kennung des Preis-Datensatzes, falls einer gegriffen hat"
    )
    on_date: date = Field(description="Stichtag der Ermittlung")
