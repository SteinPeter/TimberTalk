"""Lese-Schemas für das Änderungsprotokoll."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditEventRead(BaseModel):
    """Ein Eintrag des Änderungsprotokolls."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    occurred_at: datetime
    actor_type: str
    actor_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: uuid.UUID
    changes: dict[str, Any]
    source: str
    correlation_id: uuid.UUID
