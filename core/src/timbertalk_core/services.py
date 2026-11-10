"""Sammelstelle: importiert alle Service-Module, damit die Registry vollständig ist."""

from __future__ import annotations


def import_all_services() -> None:
    """Importiert jedes Service-Modul; beim Ergänzen einer Domäne hier eintragen."""
    from timbertalk_core.domain.company import service as company_service
    from timbertalk_core.domain.reference import service as reference_service

    _ = (company_service, reference_service)
