"""Schemas für Projekte, Arbeitspakete und Abhängigkeiten."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Self

from pydantic import Field, model_validator

from timbertalk_core.domain.enums import DependencyType, ProjectStatus, WorkPackageStatus
from timbertalk_core.schemas import Attributes, BaseSchema, QuantityValue


class ProjectCreate(BaseSchema):
    """Neues Projekt; ohne `number` vergibt der Service die nächste freie Nummer."""

    customer_id: uuid.UUID = Field(description="Kennung des Kunden")
    title: str = Field(min_length=1, max_length=250)
    number: str | None = Field(
        default=None,
        max_length=30,
        description="Lesbare Projektnummer, z. B. 2026-014; ohne Angabe wird sie vergeben",
    )
    status: ProjectStatus = ProjectStatus.INQUIRY
    site_street: str | None = Field(default=None, max_length=200)
    site_zip: str | None = Field(default=None, max_length=20)
    site_city: str | None = Field(default=None, max_length=100)
    site_lat: QuantityValue | None = Field(default=None, description="Breitengrad der Baustelle")
    site_lon: QuantityValue | None = Field(default=None, description="Längengrad der Baustelle")
    planned_start: date | None = None
    planned_end: date | None = None
    description: str | None = None
    attributes: Attributes

    @model_validator(mode="after")
    def _check_period(self) -> Self:
        """Stellt sicher, dass das geplante Ende nicht vor dem Beginn liegt."""
        if self.planned_start and self.planned_end and self.planned_end < self.planned_start:
            raise ValueError("Das geplante Ende darf nicht vor dem geplanten Beginn liegen.")
        return self


class ProjectUpdate(BaseSchema):
    """Änderung eines Projekts; nur gesetzte Felder werden übernommen."""

    customer_id: uuid.UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=250)
    number: str | None = Field(default=None, max_length=30)
    status: ProjectStatus | None = None
    site_street: str | None = Field(default=None, max_length=200)
    site_zip: str | None = Field(default=None, max_length=20)
    site_city: str | None = Field(default=None, max_length=100)
    site_lat: QuantityValue | None = None
    site_lon: QuantityValue | None = None
    planned_start: date | None = None
    planned_end: date | None = None
    description: str | None = None
    attributes: dict[str, object] | None = None


class ProjectRead(BaseSchema):
    """Projekt mit Verwaltungsfeldern."""

    id: uuid.UUID
    customer_id: uuid.UUID
    number: str
    title: str
    status: ProjectStatus
    site_street: str | None
    site_zip: str | None
    site_city: str | None
    site_lat: QuantityValue | None
    site_lon: QuantityValue | None
    planned_start: date | None
    planned_end: date | None
    description: str | None
    attributes: dict[str, object]
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int


class WorkPackageCreate(BaseSchema):
    """Neues Arbeitspaket innerhalb eines Projekts."""

    project_id: uuid.UUID = Field(description="Kennung des Projekts")
    title: str = Field(min_length=1, max_length=250)
    status: WorkPackageStatus = WorkPackageStatus.PLANNED
    planned_start: date | None = None
    planned_end: date | None = None
    planned_hours: QuantityValue | None = Field(default=None, description="Geplante Stunden")
    sort_order: int = 100
    cad_ref: str | None = Field(
        default=None, max_length=200, description="Verweis in das CAD-Modul (Modul B)"
    )
    description: str | None = None
    attributes: Attributes

    @model_validator(mode="after")
    def _check_period(self) -> Self:
        """Stellt sicher, dass das geplante Ende nicht vor dem Beginn liegt."""
        if self.planned_start and self.planned_end and self.planned_end < self.planned_start:
            raise ValueError("Das geplante Ende darf nicht vor dem geplanten Beginn liegen.")
        return self


class WorkPackageUpdate(BaseSchema):
    """Änderung eines Arbeitspakets; nur gesetzte Felder werden übernommen."""

    title: str | None = Field(default=None, min_length=1, max_length=250)
    status: WorkPackageStatus | None = None
    planned_start: date | None = None
    planned_end: date | None = None
    planned_hours: QuantityValue | None = None
    sort_order: int | None = None
    cad_ref: str | None = Field(default=None, max_length=200)
    description: str | None = None
    attributes: dict[str, object] | None = None


class WorkPackageRead(BaseSchema):
    """Arbeitspaket mit Verwaltungsfeldern."""

    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    status: WorkPackageStatus
    planned_start: date | None
    planned_end: date | None
    planned_hours: QuantityValue | None
    sort_order: int
    cad_ref: str | None
    description: str | None
    attributes: dict[str, object]
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int


class WorkPackageDependencyCreate(BaseSchema):
    """Neue Abhängigkeit: der Vorgänger muss vor dem Nachfolger fertig sein."""

    predecessor_id: uuid.UUID = Field(description="Kennung des vorangehenden Arbeitspakets")
    successor_id: uuid.UUID = Field(description="Kennung des nachfolgenden Arbeitspakets")
    type: DependencyType = DependencyType.FINISH_TO_START


class WorkPackageDependencyRead(BaseSchema):
    """Abhängigkeit mit Verwaltungsfeldern."""

    id: uuid.UUID
    predecessor_id: uuid.UUID
    successor_id: uuid.UUID
    type: DependencyType
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int
