"""Router für Datei-Metadaten."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from timbertalk_core.api.deps import ApiKey, Context
from timbertalk_core.domain.attachments import service
from timbertalk_core.domain.attachments.schemas import (
    AttachmentCreate,
    AttachmentRead,
    AttachmentUpdate,
)
from timbertalk_core.schemas import Page

router = APIRouter(prefix="/attachments", tags=["Anhänge"])


@router.get("", summary="Anhänge listen")
def list_attachments(
    ctx: Context,
    _key: ApiKey,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    kind: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page[AttachmentRead]:
    """Listet Datei-Metadaten mit Paging."""
    return service.list_attachments(
        ctx,
        entity_type=entity_type,
        entity_id=entity_id,
        kind=kind,
        limit=limit,
        offset=offset,
    )


@router.post("", status_code=status.HTTP_201_CREATED, summary="Datei-Metadaten anlegen")
def create_attachment(ctx: Context, _key: ApiKey, data: AttachmentCreate) -> AttachmentRead:
    """Legt die Metadaten einer Datei an; die Datei selbst liegt im Datenverzeichnis."""
    return service.create_attachment(ctx, data)


@router.get("/{attachment_id}", summary="Datei-Metadaten lesen")
def get_attachment(ctx: Context, _key: ApiKey, attachment_id: uuid.UUID) -> AttachmentRead:
    """Liest Datei-Metadaten."""
    return service.get_attachment(ctx, attachment_id)


@router.patch("/{attachment_id}", summary="Datei-Metadaten ändern")
def update_attachment(
    ctx: Context,
    _key: ApiKey,
    attachment_id: uuid.UUID,
    data: AttachmentUpdate,
    expected_version: int | None = None,
) -> AttachmentRead:
    """Ändert Datei-Metadaten; Pfad und Prüfsumme bleiben unverändert."""
    return service.update_attachment(ctx, attachment_id, data, expected_version)


@router.delete("/{attachment_id}", summary="Datei-Metadaten löschen (Soft Delete)")
def delete_attachment(
    ctx: Context, _key: ApiKey, attachment_id: uuid.UUID, expected_version: int | None = None
) -> AttachmentRead:
    """Markiert Datei-Metadaten als gelöscht."""
    return service.delete_attachment(ctx, attachment_id, expected_version)
