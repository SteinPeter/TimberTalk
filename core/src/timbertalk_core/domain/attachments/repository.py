"""Datenzugriff auf Datei-Metadaten."""

from __future__ import annotations

from sqlalchemy.orm import Session

from timbertalk_core.db.repository import Repository
from timbertalk_core.domain.attachments.models import Attachment


class AttachmentRepository(Repository[Attachment]):
    """Datenzugriff auf Datei-Metadaten."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Attachment)
