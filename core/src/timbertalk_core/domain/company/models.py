"""Tabellen für Firmendaten, Einstellungen und Steuersätze."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from timbertalk_core.db.constraints import unique_active
from timbertalk_core.db.mixins import Entity
from timbertalk_core.db.types import Quantity


class Company(Entity):
    """Firmendaten des Betriebs; es gibt genau einen aktiven Datensatz."""

    __tablename__ = "company"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    street: Mapped[str | None] = mapped_column(String(200), nullable=True)
    zip: Mapped[str | None] = mapped_column(String(20), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="DE")
    tax_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    vat_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    iban: Mapped[str | None] = mapped_column(String(40), nullable=True)
    bic: Mapped[str | None] = mapped_column(String(20), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    home_lat: Mapped[Decimal | None] = mapped_column(Quantity(), nullable=True)
    home_lon: Mapped[Decimal | None] = mapped_column(Quantity(), nullable=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON(), nullable=False, default=dict)


class Setting(Entity):
    """Frei erweiterbare Einstellung, z. B. Standard-Stundensatz oder Zahlungsziel."""

    __tablename__ = "settings"
    __table_args__ = (unique_active("uq_settings_key_active", "key"),)

    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[dict[str, Any]] = mapped_column(JSON(), nullable=False, default=dict)
    label_de: Mapped[str | None] = mapped_column(String(200), nullable=True)


class TaxRate(Entity):
    """Steuersatz mit Gültigkeitszeitraum (19 %, 7 %, 0 %)."""

    __tablename__ = "tax_rates"
    __table_args__ = (unique_active("uq_tax_rates_code_valid_from_active", "code", "valid_from"),)

    code: Mapped[str] = mapped_column(String(20), nullable=False)
    percent: Mapped[Decimal] = mapped_column(Quantity(), nullable=False)
    label_de: Mapped[str] = mapped_column(String(100), nullable=False)
    valid_from: Mapped[date] = mapped_column(nullable=False)
    valid_to: Mapped[date | None] = mapped_column(nullable=True)
