"""Aufbau der FastAPI-Anwendung.

Die Router sind dünne Adapter auf die Service-Schicht. Sie greifen nicht auf die
Datenbank zu; ein Test prüft das.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, FastAPI
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from timbertalk_core import __version__
from timbertalk_core.api.errors import register_error_handlers
from timbertalk_core.api.middleware import TransactionMiddleware
from timbertalk_core.api.routers import (
    attachments,
    audit,
    bookings,
    catalog,
    company,
    customers,
    operations,
    people,
    projects,
    reference,
    usage,
)
from timbertalk_core.config import Settings, get_settings
from timbertalk_core.db.session import create_db_engine, create_session_factory
from timbertalk_core.services import import_all_services

API_TITLE = "TimberTalk Core API"
API_DESCRIPTION = """
Backend für Zimmereien: Stammdaten, Projekte, Arbeitspakete, Buchungen und KI-Verbrauch.

Die Geschäftslogik liegt vollständig in der Service-Schicht; diese API ist nur ein Adapter.
Jede Anfrage braucht den Platzhalter-Schlüssel in der Kopfzeile `X-API-Key`. Der Akteur
kommt aus `X-Actor` (UUID), seine Art aus `X-Actor-Type` (`user`, `agent`, `system`),
die Herkunft aus `X-Source` und die Korrelations-Kennung aus `X-Correlation-Id`.
Fehler werden als Problem-JSON nach RFC 9457 beantwortet.
"""


def _all_routers() -> list[APIRouter]:
    """Liefert alle Router der Anwendung, ein Satz pro Domäne."""
    return [
        company.company_router,
        company.settings_router,
        company.tax_rates_router,
        reference.units_router,
        reference.cost_types_router,
        reference.custom_fields_router,
        people.router,
        customers.router,
        projects.projects_router,
        projects.work_packages_router,
        projects.dependencies_router,
        catalog.material_items_router,
        catalog.prices_router,
        bookings.router,
        attachments.router,
        usage.model_prices_router,
        usage.usage_router,
        audit.router,
        operations.router,
    ]


def create_app(
    settings: Settings | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> FastAPI:
    """Erzeugt die FastAPI-Anwendung samt Routern und Fehlerbehandlung.

    Parameter:
        settings: Einstellungen; ohne Angabe die des Prozesses.
        session_factory: fertige Session-Fabrik, etwa in Tests; sonst wird eine
            Engine aus den Einstellungen gebaut.
    """
    effektive_settings = settings or get_settings()
    import_all_services()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        engine: Engine | None = None
        if session_factory is not None:
            application.state.session_factory = session_factory
        else:
            engine = create_db_engine(effektive_settings)
            application.state.session_factory = create_session_factory(engine)
        application.state.settings = effektive_settings
        try:
            yield
        finally:
            if engine is not None:
                engine.dispose()

    application = FastAPI(
        title=API_TITLE,
        description=API_DESCRIPTION,
        version=__version__,
        lifespan=lifespan,
    )
    application.add_middleware(TransactionMiddleware)
    register_error_handlers(application)

    @application.get("/health", tags=["System"], summary="Verfügbarkeit prüfen")
    def health() -> dict[str, Any]:
        """Meldet, dass das Backend erreichbar ist."""
        return {"status": "ok", "version": __version__}

    for router in _all_routers():
        application.include_router(router)

    return application


app = create_app()
