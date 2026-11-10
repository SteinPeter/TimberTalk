"""Datenzugriff auf das Änderungsprotokoll."""

from __future__ import annotations

from sqlalchemy.orm import Session

from timbertalk_core.db.repository import Repository
from timbertalk_core.domain.audit.models import AuditEvent


class AuditEventRepository(Repository[AuditEvent]):
    """Datenzugriff auf Protokolleinträge; es wird nur gelesen."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, AuditEvent)
