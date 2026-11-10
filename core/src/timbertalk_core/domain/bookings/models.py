"""Tabelle der Buchungen: eine Zeile für jeden Kostenfaktor."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, String, Text
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column

from timbertalk_core.db.mixins import Entity
from timbertalk_core.db.types import GUID, Money, Quantity, UtcDateTime


class Booking(Entity):
    """Eine Buchung: Stunden, Material, Fahrt, Gerät oder Pauschale.

    Welche Felder in `details` gelten, bestimmt die Art (`kind`) der Kostenart.
    """

    __tablename__ = "bookings"
    __table_args__ = (
        Index("ix_bookings_project_booking_date", "project_id", "booking_date"),
        Index("ix_bookings_status_booking_date", "status", "booking_date"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("projects.id"), nullable=False, index=True
    )
    work_package_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("work_packages.id"), nullable=True, index=True
    )
    cost_type_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("cost_types.id"), nullable=False, index=True
    )
    booking_date: Mapped[date] = mapped_column(nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Quantity(), nullable=False)
    unit_code: Mapped[str] = mapped_column(String(20), nullable=False)
    unit_price: Mapped[Decimal | None] = mapped_column(Money(), nullable=True)
    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("employees.id"), nullable=True, index=True
    )
    material_item_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("material_items.id"), nullable=True, index=True
    )
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSON()), nullable=False, default=dict
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    source_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON(), nullable=False, default=dict)
