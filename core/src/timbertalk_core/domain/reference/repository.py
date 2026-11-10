"""Datenzugriff auf die Referenzdaten."""

from __future__ import annotations

from sqlalchemy.orm import Session

from timbertalk_core.db.repository import Repository
from timbertalk_core.domain.reference.models import CostType, CustomFieldDefinition, Unit


class UnitRepository(Repository[Unit]):
    """Datenzugriff auf Einheiten."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Unit)


class CostTypeRepository(Repository[CostType]):
    """Datenzugriff auf Kostenarten."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, CostType)


class CustomFieldDefinitionRepository(Repository[CustomFieldDefinition]):
    """Datenzugriff auf Zusatzfeld-Definitionen."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, CustomFieldDefinition)

    def for_entity_type(self, entity_type: str) -> list[CustomFieldDefinition]:
        """Liefert alle aktiven Zusatzfeld-Definitionen einer Entität."""
        return self.list(
            filters=[
                CustomFieldDefinition.entity_type == entity_type,
                CustomFieldDefinition.active.is_(True),
            ],
            order_by=[CustomFieldDefinition.sort_order, CustomFieldDefinition.key],
            limit=200,
        )
