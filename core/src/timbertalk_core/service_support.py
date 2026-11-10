"""Wiederkehrende Bausteine der Service-Schicht."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel

from timbertalk_core.db.mixins import Entity
from timbertalk_core.db.repository import MAX_LIMIT, Repository
from timbertalk_core.errors import Conflict, NotFound
from timbertalk_core.schemas import Page


def require_found[ModelT: Entity](instance: ModelT | None, entity_type: str, entity_id: Any) -> ModelT:
    """Liefert den Datensatz oder wirft `NotFound`.

    Parameter:
        instance: gefundener Datensatz oder `None`.
        entity_type: deutschsprachige Bezeichnung für die Fehlermeldung.
        entity_id: Kennung, nach der gesucht wurde.
    """
    if instance is None:
        raise NotFound.for_entity(entity_type, entity_id)
    return instance


def check_version(instance: Entity, expected_version: int | None, entity_type: str) -> None:
    """Prüft die erwartete Version (optimistisches Sperren).

    Parameter:
        instance: der zu ändernde Datensatz.
        expected_version: vom Aufrufer erwartete Version; `None` überspringt die Prüfung.
        entity_type: deutschsprachige Bezeichnung für die Fehlermeldung.
    """
    if expected_version is None:
        return
    if instance.version != expected_version:
        raise Conflict(
            f"{entity_type} wurde zwischenzeitlich geändert "
            f"(erwartete Version {expected_version}, aktuell {instance.version}).",
            expected_version=expected_version,
            actual_version=instance.version,
        )


def apply_updates(instance: Entity, data: BaseModel, *, skip: Sequence[str] = ()) -> dict[str, Any]:
    """Überträgt die gesetzten Felder eines Änderungs-Schemas auf den Datensatz.

    Parameter:
        instance: der zu ändernde Datensatz.
        data: Änderungs-Schema; nicht gesetzte Felder bleiben unberührt.
        skip: Feldnamen, die der Service selbst behandelt.
    """
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if field in skip:
            continue
        setattr(instance, field, value)
    return changes


def ensure_unique[ModelT: Entity](
    repository: Repository[ModelT],
    *conditions: Any,
    message: str,
    **details: Any,
) -> None:
    """Stellt sicher, dass noch kein aktiver Datensatz die Bedingungen erfüllt.

    Parameter:
        repository: Repository der betroffenen Tabelle.
        conditions: Bedingungen, die zusammen eindeutig sein müssen.
        message: deutsche Fehlermeldung bei Verletzung.
        details: zusätzliche Angaben für den Fehler.
    """
    if repository.exists(*conditions):
        raise Conflict(message, **details)


def build_page[ModelT: Entity, OutT: BaseModel](
    repository: Repository[ModelT],
    schema: type[OutT],
    *,
    filters: Sequence[Any] = (),
    order_by: Sequence[Any] = (),
    limit: int = 50,
    offset: int = 0,
    include_deleted: bool = False,
) -> Page[OutT]:
    """Liest eine Seite und verpackt sie samt Gesamtzahl.

    Parameter:
        repository: Repository der betroffenen Tabelle.
        schema: Lese-Schema der Einträge.
        filters: zusätzliche Bedingungen.
        order_by: Sortierung.
        limit: maximale Seitengröße (höchstens 200).
        offset: Anzahl übersprungener Datensätze.
        include_deleted: wenn wahr, werden gelöschte Datensätze mitgeliefert.
    """
    effective_limit = max(1, min(limit, MAX_LIMIT))
    rows = repository.list(
        filters=filters,
        order_by=order_by,
        limit=effective_limit,
        offset=offset,
        include_deleted=include_deleted,
    )
    return Page[schema](  # type: ignore[valid-type]
        items=[schema.model_validate(row) for row in rows],
        total=repository.count(filters=filters, include_deleted=include_deleted),
        limit=effective_limit,
        offset=offset,
    )


def resolve_by_code[ModelT: Entity](
    repository: Repository[ModelT],
    code_column: Any,
    code: str,
    entity_type: str,
) -> ModelT:
    """Liest einen aktiven Datensatz anhand seines Codes oder wirft `NotFound`.

    Parameter:
        repository: Repository der betroffenen Tabelle.
        code_column: Spalte, die den Code enthält.
        code: gesuchter Code.
        entity_type: deutschsprachige Bezeichnung für die Fehlermeldung.
    """
    rows = repository.list(filters=[code_column == code], limit=1)
    if not rows:
        raise NotFound(f"{entity_type} mit dem Code '{code}' wurde nicht gefunden.", code=code)
    return rows[0]
