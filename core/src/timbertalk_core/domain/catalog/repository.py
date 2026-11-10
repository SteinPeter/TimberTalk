"""Datenzugriff auf Materialkatalog und Preise."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from timbertalk_core.db.repository import Repository
from timbertalk_core.domain.catalog.models import MaterialItem, Price


class MaterialItemRepository(Repository[MaterialItem]):
    """Datenzugriff auf Artikel des Materialkatalogs."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, MaterialItem)


class PriceRepository(Repository[Price]):
    """Datenzugriff auf Preise."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Price)

    def for_target(self, target_type: str, target_id: uuid.UUID) -> list[Price]:
        """Liefert alle aktiven Preise eines Ziels, nach Gültigkeitsbeginn sortiert.

        Parameter:
            target_type: `material_item` oder `cost_type`.
            target_id: Kennung des Ziels.
        """
        return self.list(
            filters=[Price.target_type == target_type, Price.target_id == target_id],
            order_by=[Price.valid_from],
            limit=200,
        )
