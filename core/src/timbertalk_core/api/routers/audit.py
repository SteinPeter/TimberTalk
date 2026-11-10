"""Router für das Änderungsprotokoll; nur lesend."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Query

from timbertalk_core.api.deps import ApiKey, Context
from timbertalk_core.domain.audit import service
from timbertalk_core.domain.audit.schemas import AuditEventRead
from timbertalk_core.schemas import Page

router = APIRouter(prefix="/audit-events", tags=["Änderungsprotokoll"])


@router.get("", summary="Protokolleinträge listen")
def list_audit_events(
    ctx: Context,
    _key: ApiKey,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    action: str | None = None,
    actor_id: uuid.UUID | None = None,
    correlation_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page[AuditEventRead]:
    """Listet Einträge des Änderungsprotokolls, neueste zuerst."""
    return service.list_audit_events(
        ctx,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor_id=actor_id,
        correlation_id=correlation_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


@router.get("/{audit_event_id}", summary="Protokolleintrag lesen")
def get_audit_event(ctx: Context, _key: ApiKey, audit_event_id: uuid.UUID) -> AuditEventRead:
    """Liest einen Eintrag des Änderungsprotokolls."""
    return service.get_audit_event(ctx, audit_event_id)
