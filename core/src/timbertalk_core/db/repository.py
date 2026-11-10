"""Gemeinsame Grundlage der Repositories: Lesen, Paging, Soft Delete."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from timbertalk_core.clock import utc_now
from timbertalk_core.db.mixins import Entity

MAX_LIMIT = 200
"""Obergrenze für die Seitengröße einer Liste."""


class Repository[ModelT: Entity]:
    """Datenzugriff für eine Tabelle; enthält keine Geschäftsregeln."""

    def __init__(self, session: Session, model: type[ModelT]) -> None:
        self.session = session
        self.model = model

    @property
    def entity_type(self) -> str:
        """Tabellenname der Entität, wie er im Protokoll und in Zusatzfeldern genutzt wird."""
        return str(self.model.__tablename__)

    def base_query(self, *, include_deleted: bool = False) -> Select[ModelT]:
        """Grundabfrage; gelöschte Datensätze werden standardmäßig ausgeblendet."""
        query = select(self.model)
        if not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))
        return query

    def get(self, entity_id: uuid.UUID, *, include_deleted: bool = False) -> ModelT | None:
        """Liest einen Datensatz anhand seiner Kennung."""
        query = self.base_query(include_deleted=include_deleted).where(self.model.id == entity_id)
        return self.session.scalars(query).first()

    def list(
        self,
        *,
        filters: Sequence[Any] = (),
        order_by: Sequence[Any] = (),
        limit: int = 50,
        offset: int = 0,
        include_deleted: bool = False,
    ) -> list[ModelT]:
        """Liest eine Seite von Datensätzen mit Filtern und Sortierung."""
        query = self.base_query(include_deleted=include_deleted)
        for condition in filters:
            query = query.where(condition)
        if order_by:
            query = query.order_by(*order_by)
        query = query.limit(min(limit, MAX_LIMIT)).offset(offset)
        return list(self.session.scalars(query))

    def count(self, *, filters: Sequence[Any] = (), include_deleted: bool = False) -> int:
        """Zählt die Datensätze, die den Filtern entsprechen."""
        query = select(func.count()).select_from(self.model)
        if not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))
        for condition in filters:
            query = query.where(condition)
        return int(self.session.scalar(query) or 0)

    def exists(self, *filters: Any, include_deleted: bool = False) -> bool:
        """Prüft, ob mindestens ein Datensatz den Filtern entspricht."""
        return self.count(filters=filters, include_deleted=include_deleted) > 0

    def add(self, instance: ModelT) -> ModelT:
        """Nimmt einen neuen Datensatz in die Session auf."""
        self.session.add(instance)
        return instance

    def soft_delete(self, instance: ModelT) -> ModelT:
        """Markiert einen Datensatz als gelöscht, ohne ihn zu entfernen."""
        instance.deleted_at = utc_now()
        return instance
