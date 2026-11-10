"""Lesender Zugriff auf das Änderungsprotokoll.

Protokolleinträge werden zentral beim Flush erzeugt (siehe `db/audit.py`) und hier
nur gelesen. Es gibt bewusst keine Operation zum Anlegen, Ändern oder Löschen.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from timbertalk_core.context import ServiceContext
from timbertalk_core.domain.audit.models import AuditEvent
from timbertalk_core.domain.audit.repository import AuditEventRepository
from timbertalk_core.domain.audit.schemas import AuditEventRead
from timbertalk_core.operations import operation
from timbertalk_core.schemas import Page
from timbertalk_core.service_support import build_page, require_found


@operation(name="audit.list", read_only=True, summary_de="Listet Einträge des Änderungsprotokolls.")
def list_audit_events(
    ctx: ServiceContext,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    action: str | None = None,
    actor_id: uuid.UUID | None = None,
    correlation_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[AuditEventRead]:
    """Listet Protokolleinträge mit Paging, neueste zuerst.

    Parameter:
        entity_type: Tabellenname der Entität, z. B. `bookings`.
        entity_id: Kennung des Datensatzes.
        action: Aktion, z. B. `create`, `update`, `confirm`, `cancel`, `delete`.
        actor_id: Kennung des Akteurs.
        correlation_id: Korrelations-Kennung eines Vorgangs.
        date_from: frühester Tag.
        date_to: spätester Tag.
        limit: maximale Anzahl Datensätze (höchstens 200).
        offset: Anzahl übersprungener Datensätze.
    """
    filters = []
    if entity_type is not None:
        filters.append(AuditEvent.entity_type == entity_type)
    if entity_id is not None:
        filters.append(AuditEvent.entity_id == entity_id)
    if action is not None:
        filters.append(AuditEvent.action == action)
    if actor_id is not None:
        filters.append(AuditEvent.actor_id == actor_id)
    if correlation_id is not None:
        filters.append(AuditEvent.correlation_id == correlation_id)
    if date_from is not None:
        filters.append(AuditEvent.occurred_at >= datetime.combine(date_from, datetime.min.time(), tzinfo=UTC))
    if date_to is not None:
        filters.append(
            AuditEvent.occurred_at
            < datetime.combine(date_to + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
        )
    return build_page(
        AuditEventRepository(ctx.session),
        AuditEventRead,
        filters=filters,
        order_by=[AuditEvent.occurred_at.desc(), AuditEvent.id.desc()],
        limit=limit,
        offset=offset,
    )


@operation(name="audit.get", read_only=True, summary_de="Liest einen Protokolleintrag.")
def get_audit_event(ctx: ServiceContext, audit_event_id: uuid.UUID) -> AuditEventRead:
    """Liest einen Eintrag des Änderungsprotokolls.

    Parameter:
        audit_event_id: Kennung des Protokolleintrags.
    """
    eintrag = require_found(
        AuditEventRepository(ctx.session).get(audit_event_id), "Protokolleintrag", audit_event_id
    )
    return AuditEventRead.model_validate(eintrag)
