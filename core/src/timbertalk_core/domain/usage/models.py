"""Tabellen für Modellpreise und KI-Verbrauch."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from timbertalk_core.clock import utc_now
from timbertalk_core.db.constraints import unique_active
from timbertalk_core.db.mixins import Entity
from timbertalk_core.db.types import GUID, Money, UtcDateTime


class ModelPrice(Entity):
    """Preis eines Sprachmodells je Million Token; ohne Code-Änderung pflegbar."""

    __tablename__ = "model_prices"
    __table_args__ = (
        unique_active("uq_model_prices_provider_model_valid_from_active", "provider", "model", "valid_from"),
    )

    provider: Mapped[str] = mapped_column(String(60), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    input_per_mtok: Mapped[Decimal] = mapped_column(Money(), nullable=False)
    output_per_mtok: Mapped[Decimal] = mapped_column(Money(), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    valid_from: Mapped[date] = mapped_column(nullable=False)
    note: Mapped[str | None] = mapped_column(String(250), nullable=True)


class LlmUsage(Entity):
    """Ein KI-Aufruf samt Tokenzahlen und errechneten Kosten."""

    __tablename__ = "llm_usage"
    __table_args__ = (
        Index("ix_llm_usage_occurred_at_model", "occurred_at", "model"),
        Index("ix_llm_usage_module_feature", "module", "feature"),
    )

    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False, default=utc_now)
    provider: Mapped[str] = mapped_column(String(60), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    module: Mapped[str] = mapped_column(String(10), nullable=False)
    feature: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True, index=True)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost: Mapped[Decimal] = mapped_column(Money(), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    request_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    model_price_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
