"""Mixins für die Pflichtspalten jeder Tabelle: Kennung, Zeitstempel, Soft Delete, Version."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar

from sqlalchemy import JSON, Integer, Table
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from timbertalk_core.clock import utc_now
from timbertalk_core.db.types import GUID, UtcDateTime, new_id


class IdMixin:
    """Primärschlüssel als zeitlich sortierbare UUID (Version 7)."""

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=new_id)


class TimestampMixin:
    """Anlage- und Änderungszeitpunkt, immer zeitzonenbewusst in UTC."""

    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utc_now, onupdate=utc_now
    )


class SoftDeleteMixin:
    """Löschzeitpunkt; Datensätze werden nie wirklich entfernt (Synchronisation)."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        UtcDateTime(), nullable=True, default=None, index=True
    )

    @property
    def is_deleted(self) -> bool:
        """Wahr, wenn der Datensatz als gelöscht markiert ist."""
        return self.deleted_at is not None


class VersionMixin:
    """Zähler für optimistisches Sperren; wird von SQLAlchemy selbst hochgezählt."""

    if TYPE_CHECKING:
        __table__: ClassVar[Table]

    version: Mapped[int] = mapped_column(Integer, nullable=False)

    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, Any]:
        """Verknüpft die `version`-Spalte mit dem optimistischen Sperren von SQLAlchemy."""
        return {"version_id_col": cls.__table__.c.version}


class AttributesMixin:
    """Freie Zusatzfelder; zulässige Schlüssel stehen in `custom_field_definitions`."""

    attributes: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSON()), nullable=False, default=dict
    )


class EntityMixin(IdMixin, TimestampMixin, SoftDeleteMixin, VersionMixin):
    """Pflichtspalten jeder Tabelle: `id`, `created_at`, `updated_at`, `deleted_at`, `version`."""
