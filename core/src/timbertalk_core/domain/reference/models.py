"""Tabellen der Referenzdaten; neue Kostenarten sind Daten, kein Code."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from timbertalk_core.db.constraints import unique_active
from timbertalk_core.db.mixins import Entity
from timbertalk_core.db.types import Money


class Unit(Entity):
    """Einheit einer Menge mit Anzeige-Genauigkeit, z. B. `h`, `km`, `m3`."""

    __tablename__ = "units"
    __table_args__ = (unique_active("uq_units_code_active", "code"),)

    code: Mapped[str] = mapped_column(String(20), nullable=False)
    label_de: Mapped[str] = mapped_column(String(100), nullable=False)
    decimals: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)


class CostType(Entity):
    """Kostenart; `kind` bestimmt das Verhalten, alles Weitere sind Daten."""

    __tablename__ = "cost_types"
    __table_args__ = (unique_active("uq_cost_types_code_active", "code"),)

    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name_de: Mapped[str] = mapped_column(String(150), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    default_unit_code: Mapped[str] = mapped_column(String(20), nullable=False)
    default_unit_price: Mapped[Decimal | None] = mapped_column(Money(), nullable=True)
    tax_rate_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    labor_share: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON(), nullable=False, default=dict)


class CustomFieldDefinition(Entity):
    """Beschreibt ein erlaubtes Zusatzfeld in der JSON-Spalte `attributes`."""

    __tablename__ = "custom_field_definitions"
    __table_args__ = (
        unique_active("uq_custom_field_definitions_entity_type_key_active", "entity_type", "key"),
    )

    entity_type: Mapped[str] = mapped_column(String(60), nullable=False)
    key: Mapped[str] = mapped_column(String(60), nullable=False)
    label_de: Mapped[str] = mapped_column(String(150), nullable=False)
    data_type: Mapped[str] = mapped_column(String(20), nullable=False)
    unit_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enum_values: Mapped[list[str] | None] = mapped_column(JSON(), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
