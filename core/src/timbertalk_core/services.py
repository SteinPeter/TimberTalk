"""Sammelstelle: importiert alle Service-Module, damit die Registry vollständig ist."""

from __future__ import annotations


def import_all_services() -> None:
    """Importiert jedes Service-Modul; beim Ergänzen einer Domäne hier eintragen."""
    from timbertalk_core.domain.catalog import service as catalog_service
    from timbertalk_core.domain.company import service as company_service
    from timbertalk_core.domain.customers import service as customer_service
    from timbertalk_core.domain.people import service as people_service
    from timbertalk_core.domain.projects import service as project_service
    from timbertalk_core.domain.reference import service as reference_service

    _ = (
        catalog_service,
        company_service,
        customer_service,
        people_service,
        project_service,
        reference_service,
    )
