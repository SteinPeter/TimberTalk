"""Sammelstelle aller Tabellen-Metadaten für Alembic-Autogenerate."""

from __future__ import annotations

from sqlalchemy import MetaData

from timbertalk_core.db.base import Base


def import_all_models() -> None:
    """Importiert alle Domänen-Modelle, damit `Base.metadata` vollständig ist."""
    # Beim Ergänzen einer Domäne hier eintragen, sonst fehlt sie in den Migrationen.
    from timbertalk_core.domain.audit import models as audit_models

    _ = (audit_models.AuditEvent,)


def get_metadata() -> MetaData:
    """Liefert die vollständige Metadaten-Sammlung aller Tabellen."""
    import_all_models()
    return Base.metadata
