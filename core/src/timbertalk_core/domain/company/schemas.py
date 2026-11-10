"""Schemas für Firmendaten, Einstellungen und Steuersätze."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import Field

from timbertalk_core.schemas import BaseSchema, QuantityValue


class CompanyUpsert(BaseSchema):
    """Firmendaten anlegen oder ändern; es gibt genau einen Datensatz."""

    name: str = Field(min_length=1, max_length=200, description="Name des Betriebs")
    street: str | None = Field(default=None, max_length=200)
    zip: str | None = Field(default=None, max_length=20, description="Postleitzahl")
    city: str | None = Field(default=None, max_length=100)
    country: str = Field(default="DE", min_length=2, max_length=2, description="Ländercode ISO 3166-1")
    tax_number: str | None = Field(default=None, max_length=50, description="Steuernummer")
    vat_id: str | None = Field(default=None, max_length=50, description="Umsatzsteuer-Identnummer")
    iban: str | None = Field(default=None, max_length=40)
    bic: str | None = Field(default=None, max_length=20)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=200)
    home_lat: QuantityValue | None = Field(default=None, description="Breitengrad des Betriebssitzes")
    home_lon: QuantityValue | None = Field(default=None, description="Längengrad des Betriebssitzes")
    attributes: dict[str, Any] = Field(default_factory=dict)


class CompanyRead(BaseSchema):
    """Firmendaten mit Verwaltungsfeldern."""

    id: uuid.UUID
    name: str
    street: str | None
    zip: str | None
    city: str | None
    country: str
    tax_number: str | None
    vat_id: str | None
    iban: str | None
    bic: str | None
    phone: str | None
    email: str | None
    home_lat: QuantityValue | None
    home_lon: QuantityValue | None
    attributes: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int


class SettingUpsert(BaseSchema):
    """Einstellung setzen; der Wert ist beliebiges JSON."""

    key: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[a-z][a-z0-9_.]*$",
        description="Schlüssel, z. B. `default_hourly_rate`",
    )
    value: dict[str, Any] = Field(description="Wert als JSON-Objekt")
    label_de: str | None = Field(default=None, max_length=200)


class SettingRead(BaseSchema):
    """Einstellung mit Verwaltungsfeldern."""

    id: uuid.UUID
    key: str
    value: dict[str, Any]
    label_de: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int


class TaxRateCreate(BaseSchema):
    """Neuer Steuersatz mit Gültigkeitsbeginn."""

    code: str = Field(min_length=1, max_length=20, description="Code, z. B. `19`")
    percent: QuantityValue = Field(description="Steuersatz in Prozent, z. B. 19")
    label_de: str = Field(min_length=1, max_length=100)
    valid_from: date = Field(description="Erster Tag der Gültigkeit")
    valid_to: date | None = Field(default=None, description="Letzter Tag der Gültigkeit")


class TaxRateUpdate(BaseSchema):
    """Änderung eines Steuersatzes; nur gesetzte Felder werden übernommen."""

    percent: QuantityValue | None = None
    label_de: str | None = Field(default=None, min_length=1, max_length=100)
    valid_from: date | None = None
    valid_to: date | None = None


class TaxRateRead(BaseSchema):
    """Steuersatz mit Verwaltungsfeldern."""

    id: uuid.UUID
    code: str
    percent: QuantityValue
    label_de: str
    valid_from: date
    valid_to: date | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int
