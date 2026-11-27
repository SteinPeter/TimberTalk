# Projekttabelle und streng geprüfte Eingaben; Kunden bleiben im Kunden-Feature.
import re
from datetime import date
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, StrictInt, StringConstraints
from pydantic import Field as InputField
from sqlalchemy import CheckConstraint
from sqlmodel import Field, SQLModel


class ProjectStatus(StrEnum):
    REQUESTED = "angefragt"
    PLANNED = "geplant"
    IN_PROGRESS = "in_arbeit"
    COMPLETED = "abgeschlossen"
    BILLED = "abgerechnet"


PositiveId = Annotated[StrictInt, InputField(gt=0)]
ProjectName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
SiteName = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]


def check_date(value):
    if type(value) is date or (
        isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)
    ):
        return value
    raise ValueError("Datum bitte als JJJJ-MM-TT angeben.")


InputDate = Annotated[date, BeforeValidator(check_date)]


class Project(SQLModel, table=True):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint("customer_id > 0"),
        CheckConstraint("length(trim(name)) > 0"),
        CheckConstraint("version > 0"),
        CheckConstraint("dauer_tage IS NULL OR dauer_tage > 0"),
        CheckConstraint(
            "status IN ('angefragt','geplant','in_arbeit','abgeschlossen','abgerechnet')"
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=200)
    customer_id: int = Field(index=True, nullable=False)
    baustelle: str = Field(default="", max_length=500)
    status: str = Field(default=ProjectStatus.REQUESTED.value, index=True)
    start: date | None = None
    dauer_tage: int | None = None
    archived: bool = Field(default=False, index=True)
    version: int = Field(default=1, nullable=False)


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateProject(InputModel):
    kunde_id: PositiveId
    name: ProjectName
    baustelle_ort: SiteName = ""
    start: InputDate | None = None
    dauer_tage: Annotated[StrictInt, InputField(gt=0, le=36500)] | None = None


class ProjectFields(InputModel):
    name: ProjectName | None = None
    kunde_id: PositiveId | None = None
    baustelle_ort: SiteName | None = None
    start: InputDate | None = None
    dauer_tage: Annotated[StrictInt, InputField(gt=0, le=36500)] | None = None


class ChangeProject(InputModel):
    projekt_id: PositiveId
    feldern: ProjectFields


class SetStatus(InputModel):
    projekt_id: PositiveId
    status: ProjectStatus


class ArchiveProject(InputModel):
    projekt_id: PositiveId


class SearchProjects(InputModel):
    text: Annotated[str, StringConstraints(max_length=200)] = ""
    kunde_id: PositiveId | None = None
    status: ProjectStatus | None = None


class ToolRequest(InputModel):
    name: str
    args: dict
    quelle: Literal["ui", "ki"] = "ui"
    originaltext: str | None = None
