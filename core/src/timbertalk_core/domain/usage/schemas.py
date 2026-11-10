"""Schemas für Modellpreise und KI-Verbrauch."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import ConfigDict, Field

from timbertalk_core.domain.enums import UsageGrouping, UsageModule, UsagePeriod
from timbertalk_core.schemas import BaseSchema, MoneyValue


class ModelPriceCreate(BaseSchema):
    """Neuer Modellpreis je Million Token."""

    model_config = ConfigDict(from_attributes=True, extra="forbid", protected_namespaces=())

    provider: str = Field(min_length=1, max_length=60, description="Anbieter, z. B. `anthropic`")
    model: str = Field(min_length=1, max_length=120, description="Modellkennung")
    input_per_mtok: MoneyValue = Field(description="Preis je Million Eingabe-Token")
    output_per_mtok: MoneyValue = Field(description="Preis je Million Ausgabe-Token")
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    valid_from: date = Field(description="Erster Tag der Gültigkeit")
    note: str | None = Field(default=None, max_length=250)


class ModelPriceRead(BaseSchema):
    """Modellpreis mit Verwaltungsfeldern."""

    model_config = ConfigDict(from_attributes=True, extra="forbid", protected_namespaces=())

    id: uuid.UUID
    provider: str
    model: str
    input_per_mtok: MoneyValue
    output_per_mtok: MoneyValue
    currency: str
    valid_from: date
    note: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int


class UsageRecord(BaseSchema):
    """Ein zu protokollierender KI-Aufruf; die Kosten errechnet der Service."""

    model_config = ConfigDict(from_attributes=True, extra="forbid", protected_namespaces=())

    provider: str = Field(min_length=1, max_length=60, description="Anbieter des Modells")
    model: str = Field(min_length=1, max_length=120, description="Verwendetes Modell")
    module: UsageModule = Field(description="Modul `a` (Betriebssoftware) oder `b` (CAD)")
    feature: str = Field(min_length=1, max_length=100, description="Funktion, z. B. `voice_booking`")
    input_tokens: int = Field(default=0, ge=0, description="Anzahl Eingabe-Token")
    output_tokens: int = Field(default=0, ge=0, description="Anzahl Ausgabe-Token")
    actor_id: uuid.UUID | None = Field(default=None, description="Auslösender Akteur")
    project_id: uuid.UUID | None = Field(default=None, description="Zugehöriges Projekt")
    request_id: str | None = Field(default=None, max_length=120, description="Anfrage-Kennung")
    success: bool = Field(default=True, description="Falsch, wenn der Aufruf fehlgeschlagen ist")
    occurred_at: datetime | None = Field(default=None, description="Zeitpunkt des Aufrufs; ohne Angabe jetzt")


class UsageRead(BaseSchema):
    """Protokollierter KI-Aufruf mit errechneten Kosten."""

    model_config = ConfigDict(from_attributes=True, extra="forbid", protected_namespaces=())

    id: uuid.UUID
    occurred_at: datetime
    provider: str
    model: str
    module: UsageModule
    feature: str
    actor_id: uuid.UUID | None
    project_id: uuid.UUID | None
    input_tokens: int
    output_tokens: int
    cost: MoneyValue
    currency: str
    request_id: str | None
    success: bool
    model_price_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int


class UsageSummaryRow(BaseSchema):
    """Eine Zeile der Verbrauchsübersicht."""

    period: str = Field(description="Zeitraum, z. B. `2026-05` bei Monatsraster")
    group: str = Field(description="Gruppenschlüssel laut `group_by`")
    calls: int = Field(description="Anzahl der Aufrufe")
    input_tokens: int
    output_tokens: int
    cost: MoneyValue = Field(description="Summe der Kosten")
    currency: str


class UsageSummary(BaseSchema):
    """Verbrauchsübersicht für Handy, PC und Verwaltungs-Tool."""

    period: UsagePeriod
    group_by: UsageGrouping
    rows: list[UsageSummaryRow]
    total_cost: MoneyValue = Field(description="Summe aller Kosten im Zeitraum")
    currency: str
