"""Tabelle der Mitarbeiter."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from timbertalk_core.db.mixins import Entity
from timbertalk_core.db.types import GUID


class Employee(Entity):
    """Ein Mitarbeiter; Login-Benutzer kommen später über `user_id` hinzu."""

    __tablename__ = "employees"

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    default_cost_type_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON(), nullable=False, default=dict)

    @property
    def display_name(self) -> str:
        """Vor- und Nachname für Anzeigen."""
        return f"{self.first_name} {self.last_name}".strip()
