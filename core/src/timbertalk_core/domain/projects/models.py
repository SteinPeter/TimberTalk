"""Tabellen für Projekte, Arbeitspakete und deren Abhängigkeiten."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from timbertalk_core.db.constraints import unique_active
from timbertalk_core.db.mixins import Entity
from timbertalk_core.db.types import GUID, Quantity


class Project(Entity):
    """Ein Auftrag bzw. eine Baustelle."""

    __tablename__ = "projects"
    __table_args__ = (unique_active("uq_projects_number_active", "number"),)

    customer_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("customers.id"), nullable=False, index=True
    )
    number: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    site_street: Mapped[str | None] = mapped_column(String(200), nullable=True)
    site_zip: Mapped[str | None] = mapped_column(String(20), nullable=True)
    site_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    site_lat: Mapped[Decimal | None] = mapped_column(Quantity(), nullable=True)
    site_lon: Mapped[Decimal | None] = mapped_column(Quantity(), nullable=True)
    planned_start: Mapped[date | None] = mapped_column(nullable=True)
    planned_end: Mapped[date | None] = mapped_column(nullable=True)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON(), nullable=False, default=dict)


class WorkPackage(Entity):
    """Ein Arbeitspaket innerhalb eines Projekts; Grundlage des Gantt-Plans."""

    __tablename__ = "work_packages"

    project_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("projects.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    planned_start: Mapped[date | None] = mapped_column(nullable=True)
    planned_end: Mapped[date | None] = mapped_column(nullable=True)
    planned_hours: Mapped[Decimal | None] = mapped_column(Quantity(), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    cad_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON(), nullable=False, default=dict)


class WorkPackageDependency(Entity):
    """Abhängigkeit zwischen zwei Arbeitspaketen (Vorgänger vor Nachfolger)."""

    __tablename__ = "work_package_dependencies"
    __table_args__ = (
        unique_active(
            "uq_work_package_dependencies_predecessor_successor_active",
            "predecessor_id",
            "successor_id",
        ),
    )

    predecessor_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("work_packages.id"), nullable=False, index=True
    )
    successor_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("work_packages.id"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False, default="finish_to_start")
