"""Tabelle der Datei-Metadaten."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, BigInteger, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from timbertalk_core.db.mixins import Entity
from timbertalk_core.db.types import GUID, Quantity, UtcDateTime


class Attachment(Entity):
    """Metadaten einer Datei; der Inhalt liegt im Datenverzeichnis."""

    __tablename__ = "attachments"
    __table_args__ = (
        Index("ix_attachments_entity_type_entity_id", "entity_type", "entity_id"),
        Index("ix_attachments_sha256", "sha256"),
    )

    entity_type: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    original_name: Mapped[str | None] = mapped_column(String(250), nullable=True)
    captured_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    lat: Mapped[Decimal | None] = mapped_column(Quantity(), nullable=True)
    lon: Mapped[Decimal | None] = mapped_column(Quantity(), nullable=True)
    note: Mapped[str | None] = mapped_column(Text(), nullable=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON(), nullable=False, default=dict)
