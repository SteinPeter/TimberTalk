"""Tabellen für Materialkatalog und Preise."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Boolean, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from timbertalk_core.db.constraints import unique_active
from timbertalk_core.db.mixins import Entity
from timbertalk_core.db.types import GUID, Money


class MaterialItem(Entity):
    """Ein Artikel im Materialkatalog, z. B. KVH Fichte C24 60×200."""

    __tablename__ = "material_items"
    __table_args__ = (unique_active("uq_material_items_sku_active", "sku"),)

    sku: Mapped[str | None] = mapped_column(String(60), nullable=True)
    name: Mapped[str] = mapped_column(String(250), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    wood_species: Mapped[str | None] = mapped_column(String(60), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(60), nullable=True)
    width_mm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_mm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    length_mm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit_code: Mapped[str] = mapped_column(String(20), nullable=False)
    cost_type_code: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON(), nullable=False, default=dict)


class Price(Entity):
    """Preis eines Artikels oder einer Kostenart mit Gültigkeitszeitraum."""

    __tablename__ = "prices"
    __table_args__ = (Index("ix_prices_target", "target_type", "target_id", "valid_from"),)

    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Money(), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    valid_from: Mapped[date] = mapped_column(nullable=False)
    valid_to: Mapped[date | None] = mapped_column(nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    note: Mapped[str | None] = mapped_column(Text(), nullable=True)
