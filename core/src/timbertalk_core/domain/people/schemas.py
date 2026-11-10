"""Schemas der Mitarbeiter."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from timbertalk_core.domain.enums import EmployeeRole
from timbertalk_core.schemas import Attributes, BaseSchema


class EmployeeCreate(BaseSchema):
    """Neuer Mitarbeiter."""

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    role: EmployeeRole = Field(description="owner, master, journeyman, apprentice oder office")
    default_cost_type_code: str | None = Field(
        default=None, max_length=50, description="Vorgabe-Kostenart für Stundenbuchungen"
    )
    email: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=50)
    user_id: uuid.UUID | None = Field(
        default=None, description="Verknüpfung zu einem späteren Login-Benutzer"
    )
    active: bool = True
    attributes: Attributes


class EmployeeUpdate(BaseSchema):
    """Änderung eines Mitarbeiters; nur gesetzte Felder werden übernommen."""

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    role: EmployeeRole | None = None
    default_cost_type_code: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=50)
    user_id: uuid.UUID | None = None
    active: bool | None = None
    attributes: dict[str, object] | None = None


class EmployeeRead(BaseSchema):
    """Mitarbeiter mit Verwaltungsfeldern."""

    id: uuid.UUID
    first_name: str
    last_name: str
    display_name: str
    role: EmployeeRole
    default_cost_type_code: str | None
    email: str | None
    phone: str | None
    user_id: uuid.UUID | None
    active: bool
    attributes: dict[str, object]
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int
