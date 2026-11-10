"""Zentrale Erzeugung der Audit-Einträge über SQLAlchemy-Ereignisse.

Kein Service schreibt Audit-Einträge von Hand. Vor jedem Flush wird jede geänderte
Entität betrachtet und ein Eintrag in `audit_events` angelegt. Die fachliche Aktion
ergibt sich aus dem Zustand des Objekts oder aus `ServiceContext.action_hint`.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session, sessionmaker

from timbertalk_core.clock import utc_now
from timbertalk_core.db.types import new_id
from timbertalk_core.domain.audit.models import AuditEvent

if TYPE_CHECKING:
    from timbertalk_core.context import ServiceContext

CONTEXT_KEY = "service_context"
"""Schlüssel, unter dem der `ServiceContext` in `Session.info` liegt."""

IGNORED_FIELDS = frozenset({"version", "updated_at", "created_at"})
"""Felder, die im Protokoll nur Rauschen erzeugen."""


def _as_json(value: Any) -> Any:
    """Wandelt einen Spaltenwert in eine JSON-taugliche Darstellung."""
    if value is None or isinstance(value, bool | int | str):
        return value
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _as_json(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set):
        return [_as_json(item) for item in value]
    return str(value)


def _changes_for_insert(instance: object) -> dict[str, Any]:
    state = inspect(instance)
    changes: dict[str, Any] = {}
    for attr in state.mapper.column_attrs:
        if attr.key in IGNORED_FIELDS:
            continue
        value = getattr(instance, attr.key, None)
        if value is None:
            continue
        changes[attr.key] = {"old": None, "new": _as_json(value)}
    return changes


def _changes_for_update(instance: object) -> dict[str, Any]:
    state = inspect(instance)
    changes: dict[str, Any] = {}
    for attr in state.mapper.column_attrs:
        if attr.key in IGNORED_FIELDS:
            continue
        history = state.attrs[attr.key].history
        if not history.has_changes():
            continue
        old = history.deleted[0] if history.deleted else None
        new = history.added[0] if history.added else None
        if old == new:
            continue
        changes[attr.key] = {"old": _as_json(old), "new": _as_json(new)}
    return changes


def _action_for_update(changes: dict[str, Any]) -> str:
    deleted_at = changes.get("deleted_at")
    if isinstance(deleted_at, dict) and deleted_at.get("old") is None and deleted_at.get("new"):
        return "delete"
    if isinstance(deleted_at, dict) and deleted_at.get("old") and deleted_at.get("new") is None:
        return "restore"
    return "update"


def _ensure_id(instance: object) -> uuid.UUID:
    """Liefert die Kennung der Entität und vergibt sie, falls der Flush sie noch nicht gesetzt hat.

    Spalten-Vorgabewerte greifen erst beim Flush. Da das Protokoll vorher geschrieben wird,
    wird die UUIDv7 hier bereits vergeben.
    """
    entity_id = getattr(instance, "id", None)
    if entity_id is None:
        entity_id = new_id()
        instance.id = entity_id  # type: ignore[attr-defined]
    if not isinstance(entity_id, uuid.UUID):
        raise TypeError(f"Kennung von {type(instance).__name__} ist keine UUID.")
    return entity_id


def _build_event(
    context: ServiceContext, instance: object, action: str, changes: dict[str, Any]
) -> AuditEvent:
    entity_id = _ensure_id(instance)
    return AuditEvent(
        occurred_at=utc_now(),
        actor_type=str(context.actor_type.value),
        actor_id=context.actor_id,
        action=action,
        entity_type=str(getattr(instance, "__tablename__", type(instance).__name__)),
        entity_id=entity_id,
        changes=changes,
        source=str(context.source.value),
        correlation_id=context.correlation_id,
    )


def record_changes(session: Session, _flush_context: Any = None, _instances: Any = None) -> None:
    """Legt für jede geänderte Entität einen Audit-Eintrag an (Ereignis `before_flush`)."""
    context: ServiceContext | None = session.info.get(CONTEXT_KEY)
    if context is None:
        raise RuntimeError(
            "Schreibender Zugriff ohne ServiceContext: das Änderungsprotokoll kann nicht geschrieben werden."
        )

    hint = context.action_hint
    events: list[AuditEvent] = []

    for instance in session.new:
        if isinstance(instance, AuditEvent):
            continue
        _ensure_id(instance)
        changes = _changes_for_insert(instance)
        events.append(_build_event(context, instance, hint or "create", changes))

    for instance in session.dirty:
        if isinstance(instance, AuditEvent) or not session.is_modified(instance):
            continue
        changes = _changes_for_update(instance)
        if not changes:
            continue
        events.append(_build_event(context, instance, hint or _action_for_update(changes), changes))

    for instance in session.deleted:
        if isinstance(instance, AuditEvent):
            continue
        events.append(_build_event(context, instance, hint or "delete", _changes_for_insert(instance)))

    context.action_hint = None
    for audit_event in events:
        session.add(audit_event)


def install_audit_listener(factory: sessionmaker[Session]) -> None:
    """Hängt die zentrale Audit-Erzeugung an eine Session-Fabrik.

    Bewusst ohne Prüfung auf eine bestehende Registrierung: SQLAlchemy verwaltet
    Ereignis-Ziele anhand der Objekt-Kennung (`id()`). Wird eine alte Fabrik
    eingesammelt und eine neue an derselben Speicheradresse angelegt, meldet
    `event.contains` fälschlich eine bestehende Registrierung – das Protokoll
    würde dann still ausfallen. Eine frisch erzeugte Fabrik hat nie einen
    Listener, deshalb kann hier keine Doppelregistrierung entstehen.
    """
    event.listen(factory, "before_flush", record_changes)
