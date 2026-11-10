"""Tabelle des Änderungsprotokolls."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from timbertalk_core.clock import utc_now
from timbertalk_core.db.mixins import Entity
from timbertalk_core.db.types import GUID, UtcDateTime


class AuditEvent(Entity):
    """Ein Protokolleintrag je geänderter Entität; wird nur angehängt, nie geändert."""

    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_entity_type_entity_id", "entity_type", "entity_id"),
        Index("ix_audit_events_occurred_at", "occurred_at"),
    )

    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False, default=utc_now)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    changes: Mapped[dict[str, Any]] = mapped_column(JSON(), nullable=False, default=dict)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    correlation_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
