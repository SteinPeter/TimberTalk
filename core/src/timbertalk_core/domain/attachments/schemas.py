"""Schemas der Datei-Metadaten."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from timbertalk_core.domain.enums import AttachmentKind
from timbertalk_core.schemas import BaseSchema, QuantityValue


class AttachmentCreate(BaseSchema):
    """Neue Datei-Metadaten; die Datei selbst liegt bereits im Datenverzeichnis."""

    entity_type: str = Field(
        min_length=1, max_length=60, description="Tabellenname, z. B. `bookings` oder `projects`"
    )
    entity_id: uuid.UUID = Field(description="Kennung des Datensatzes, zu dem die Datei gehört")
    file_path: str = Field(min_length=1, max_length=500, description="Pfad relativ zum Datenverzeichnis")
    mime_type: str = Field(min_length=1, max_length=100, description="Medientyp, z. B. `image/jpeg`")
    size_bytes: int = Field(ge=0, description="Größe der Datei in Bytes")
    sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
        description="SHA-256-Prüfsumme in Kleinbuchstaben",
    )
    kind: AttachmentKind = Field(description="photo, delivery_note, invoice_in, cad oder other")
    original_name: str | None = Field(default=None, max_length=250)
    captured_at: datetime | None = Field(default=None, description="Aufnahmezeitpunkt (UTC)")
    lat: QuantityValue | None = Field(default=None, description="Breitengrad der Aufnahme")
    lon: QuantityValue | None = Field(default=None, description="Längengrad der Aufnahme")
    note: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class AttachmentUpdate(BaseSchema):
    """Änderung der Metadaten; nur gesetzte Felder werden übernommen."""

    kind: AttachmentKind | None = None
    original_name: str | None = Field(default=None, max_length=250)
    captured_at: datetime | None = None
    lat: QuantityValue | None = None
    lon: QuantityValue | None = None
    note: str | None = None
    attributes: dict[str, object] | None = None


class AttachmentRead(BaseSchema):
    """Datei-Metadaten mit Verwaltungsfeldern."""

    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    file_path: str
    mime_type: str
    size_bytes: int
    sha256: str
    kind: AttachmentKind
    original_name: str | None
    captured_at: datetime | None
    lat: QuantityValue | None
    lon: QuantityValue | None
    note: str | None
    attributes: dict[str, object]
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int
