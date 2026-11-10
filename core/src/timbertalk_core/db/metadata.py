"""Sammelstelle aller Tabellen-Metadaten für Alembic-Autogenerate."""

from __future__ import annotations

from sqlalchemy import MetaData

from timbertalk_core.db.base import Base


def import_all_models() -> None:
    """Importiert alle Domänen-Modelle, damit `Base.metadata` vollständig ist."""
    # Beim Ergänzen einer Domäne hier eintragen, sonst fehlt sie in den Migrationen.
    from timbertalk_core.domain.audit import models as audit_models
    from timbertalk_core.domain.company import models as company_models
    from timbertalk_core.domain.customers import models as customer_models
    from timbertalk_core.domain.people import models as people_models
    from timbertalk_core.domain.projects import models as project_models
    from timbertalk_core.domain.reference import models as reference_models

    _ = (
        audit_models.AuditEvent,
        company_models.Company,
        company_models.Setting,
        company_models.TaxRate,
        reference_models.Unit,
        reference_models.CostType,
        reference_models.CustomFieldDefinition,
        people_models.Employee,
        customer_models.Customer,
        project_models.Project,
        project_models.WorkPackage,
        project_models.WorkPackageDependency,
    )


def get_metadata() -> MetaData:
    """Liefert die vollständige Metadaten-Sammlung aller Tabellen."""
    import_all_models()
    return Base.metadata
