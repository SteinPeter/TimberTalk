"""Geschäftslogik der Datei-Metadaten.

Dieser Block verwaltet nur Metadaten. Das Hochladen von Dateien ist nicht Teil des
Auftrags; die Dateien liegen im Datenverzeichnis und werden hier nur beschrieben.
"""

from __future__ import annotations

import uuid
from pathlib import PurePosixPath

from timbertalk_core.context import ServiceContext
from timbertalk_core.domain.attachments.models import Attachment
from timbertalk_core.domain.attachments.repository import AttachmentRepository
from timbertalk_core.domain.attachments.schemas import (
    AttachmentCreate,
    AttachmentRead,
    AttachmentUpdate,
)
from timbertalk_core.domain.reference.custom_fields import validate_attributes
from timbertalk_core.errors import ValidationFailed
from timbertalk_core.operations import operation
from timbertalk_core.schemas import Page
from timbertalk_core.service_support import (
    apply_updates,
    build_page,
    check_version,
    require_found,
)

ATTACHMENT_DE = "Anhang"


def _check_relative_path(file_path: str) -> str:
    """Stellt sicher, dass der Pfad relativ ist und nicht aus dem Datenverzeichnis führt."""
    pfad = PurePosixPath(file_path.replace("\\", "/"))
    if pfad.is_absolute() or ".." in pfad.parts:
        raise ValidationFailed(
            "Der Dateipfad muss relativ zum Datenverzeichnis sein und darf nicht aus ihm herausführen.",
            errors={"file_path": "relativer Pfad ohne '..' erwartet"},
            file_path=file_path,
        )
    return str(pfad)


@operation(name="attachment.create", read_only=False, summary_de="Legt Metadaten zu einer Datei an.")
def create_attachment(ctx: ServiceContext, data: AttachmentCreate) -> AttachmentRead:
    """Legt die Metadaten einer Datei an (Foto, Lieferschein, Eingangsrechnung, CAD).

    Parameter:
        data: Entität und Kennung, zu der die Datei gehört, Pfad, Medientyp,
            Größe, Prüfsumme und Art der Datei.
    """
    values = data.model_dump()
    values["file_path"] = _check_relative_path(data.file_path)
    values["attributes"] = validate_attributes(ctx, Attachment.__tablename__, values["attributes"])
    attachment = AttachmentRepository(ctx.session).add(Attachment(**values))
    ctx.session.flush()
    return AttachmentRead.model_validate(attachment)


@operation(name="attachment.get", read_only=True, summary_de="Liest Datei-Metadaten.")
def get_attachment(ctx: ServiceContext, attachment_id: uuid.UUID) -> AttachmentRead:
    """Liest Datei-Metadaten anhand ihrer Kennung.

    Parameter:
        attachment_id: Kennung des Anhangs.
    """
    attachment = require_found(
        AttachmentRepository(ctx.session).get(attachment_id), ATTACHMENT_DE, attachment_id
    )
    return AttachmentRead.model_validate(attachment)


@operation(name="attachment.list", read_only=True, summary_de="Listet Anhänge einer Entität.")
def list_attachments(
    ctx: ServiceContext,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    kind: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[AttachmentRead]:
    """Listet Anhänge mit Paging, meist zu einer bestimmten Entität.

    Parameter:
        entity_type: Tabellenname, z. B. `bookings`.
        entity_id: Kennung des Datensatzes.
        kind: Art der Datei (`photo`, `delivery_note`, `invoice_in`, `cad`, `other`).
        limit: maximale Anzahl Datensätze (höchstens 200).
        offset: Anzahl übersprungener Datensätze.
    """
    filters = []
    if entity_type is not None:
        filters.append(Attachment.entity_type == entity_type)
    if entity_id is not None:
        filters.append(Attachment.entity_id == entity_id)
    if kind is not None:
        filters.append(Attachment.kind == kind)
    return build_page(
        AttachmentRepository(ctx.session),
        AttachmentRead,
        filters=filters,
        order_by=[Attachment.created_at.desc()],
        limit=limit,
        offset=offset,
    )


@operation(name="attachment.update", read_only=False, summary_de="Ändert Datei-Metadaten.")
def update_attachment(
    ctx: ServiceContext,
    attachment_id: uuid.UUID,
    data: AttachmentUpdate,
    expected_version: int | None = None,
) -> AttachmentRead:
    """Ändert die Metadaten einer Datei; Pfad und Prüfsumme bleiben unverändert.

    Parameter:
        attachment_id: Kennung des Anhangs.
        data: zu ändernde Felder.
        expected_version: erwartete Version für optimistisches Sperren.
    """
    repository = AttachmentRepository(ctx.session)
    attachment = require_found(repository.get(attachment_id), ATTACHMENT_DE, attachment_id)
    check_version(attachment, expected_version, ATTACHMENT_DE)
    changes = apply_updates(attachment, data, skip=["attributes"])
    if "attributes" in changes:
        attachment.attributes = validate_attributes(ctx, Attachment.__tablename__, changes["attributes"])
    ctx.session.flush()
    return AttachmentRead.model_validate(attachment)


@operation(name="attachment.delete", read_only=False, summary_de="Löscht Datei-Metadaten (Soft Delete).")
def delete_attachment(
    ctx: ServiceContext, attachment_id: uuid.UUID, expected_version: int | None = None
) -> AttachmentRead:
    """Markiert Datei-Metadaten als gelöscht; die Datei selbst bleibt liegen.

    Parameter:
        attachment_id: Kennung des Anhangs.
        expected_version: erwartete Version für optimistisches Sperren.
    """
    repository = AttachmentRepository(ctx.session)
    attachment = require_found(repository.get(attachment_id), ATTACHMENT_DE, attachment_id)
    check_version(attachment, expected_version, ATTACHMENT_DE)
    repository.soft_delete(attachment)
    ctx.session.flush()
    return AttachmentRead.model_validate(attachment)
