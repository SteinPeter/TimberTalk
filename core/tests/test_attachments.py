"""Prüft die Metadaten zu Dateien."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from timbertalk_core.context import ServiceContext
from timbertalk_core.domain.attachments.schemas import AttachmentCreate, AttachmentUpdate
from timbertalk_core.domain.attachments.service import (
    create_attachment,
    delete_attachment,
    get_attachment,
    list_attachments,
    update_attachment,
)
from timbertalk_core.domain.enums import AttachmentKind
from timbertalk_core.errors import NotFound, ValidationFailed

PRUEFSUMME = "a" * 64


def _metadaten(**overrides: object) -> AttachmentCreate:
    daten: dict[str, object] = {
        "entity_type": "bookings",
        "entity_id": uuid.uuid4(),
        "file_path": "attachments/2026/05/lieferschein.jpg",
        "mime_type": "image/jpeg",
        "size_bytes": 142_000,
        "sha256": PRUEFSUMME,
        "kind": AttachmentKind.DELIVERY_NOTE,
    }
    daten.update(overrides)
    return AttachmentCreate(**daten)  # type: ignore[arg-type]


def test_metadaten_anlegen(ctx: ServiceContext) -> None:
    attachment = create_attachment(
        ctx,
        _metadaten(
            kind=AttachmentKind.PHOTO,
            captured_at=datetime(2026, 5, 4, 9, 30, tzinfo=UTC),
            lat=Decimal("52.520000"),
            lon=Decimal("13.405000"),
            original_name="IMG_2026.jpg",
        ),
    )
    ctx.session.commit()
    assert attachment.kind is AttachmentKind.PHOTO
    assert attachment.size_bytes == 142_000
    assert attachment.lat == Decimal("52.520000")
    assert attachment.captured_at == datetime(2026, 5, 4, 9, 30, tzinfo=UTC)
    assert get_attachment(ctx, attachment.id).id == attachment.id


@pytest.mark.parametrize(
    "pfad",
    ["/etc/passwd", "../../geheim.txt", "attachments/../../raus.jpg"],
)
def test_pfad_muss_relativ_und_eingeschlossen_sein(ctx: ServiceContext, pfad: str) -> None:
    with pytest.raises(ValidationFailed, match="relativ zum Datenverzeichnis"):
        create_attachment(ctx, _metadaten(file_path=pfad))


def test_pruefsumme_wird_geprueft() -> None:
    with pytest.raises(ValueError, match="sha256"):
        _metadaten(sha256="zu kurz")


def test_anhaenge_filtern(ctx: ServiceContext) -> None:
    buchung = uuid.uuid4()
    create_attachment(ctx, _metadaten(entity_id=buchung))
    create_attachment(
        ctx,
        _metadaten(
            entity_type="projects",
            entity_id=uuid.uuid4(),
            kind=AttachmentKind.CAD,
            file_path="attachments/cad/gaube.ifc",
            mime_type="application/octet-stream",
        ),
    )
    ctx.session.commit()

    assert list_attachments(ctx).total == 2
    assert list_attachments(ctx, entity_type="bookings").total == 1
    assert list_attachments(ctx, entity_id=buchung).total == 1
    assert list_attachments(ctx, kind="cad").total == 1
    assert list_attachments(ctx, entity_type="customers").total == 0


def test_metadaten_aendern_und_loeschen(ctx: ServiceContext) -> None:
    attachment = create_attachment(ctx, _metadaten())
    ctx.session.commit()

    geaendert = update_attachment(
        ctx,
        attachment.id,
        AttachmentUpdate(kind=AttachmentKind.INVOICE_IN, note="Eingangsrechnung Holzhandel"),
        expected_version=1,
    )
    ctx.session.commit()
    assert geaendert.kind is AttachmentKind.INVOICE_IN
    assert geaendert.note == "Eingangsrechnung Holzhandel"
    assert geaendert.file_path == attachment.file_path, "Pfad und Prüfsumme bleiben unverändert"
    assert geaendert.sha256 == attachment.sha256

    delete_attachment(ctx, attachment.id)
    ctx.session.commit()
    assert list_attachments(ctx).total == 0
    with pytest.raises(NotFound):
        get_attachment(ctx, attachment.id)
