"""Deklarative Basisklasse mit einheitlicher Namensgebung für Constraints."""

from __future__ import annotations

from typing import Any, ClassVar

from sqlalchemy import JSON, MetaData
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import TypeEngine

NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
"""Feste Benennung aller Constraints, damit Alembic-Migrationen stabil bleiben."""

metadata_obj = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    """Gemeinsame Basis aller Tabellen von TimberTalk."""

    metadata = metadata_obj
    type_annotation_map: ClassVar[dict[Any, TypeEngine[Any] | type[TypeEngine[Any]]]] = {dict[str, Any]: JSON}

    def __repr__(self) -> str:
        identifier = getattr(self, "id", None)
        return f"<{type(self).__name__} id={identifier}>"
