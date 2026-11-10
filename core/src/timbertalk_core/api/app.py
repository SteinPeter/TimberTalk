"""Aufbau der FastAPI-Anwendung."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from timbertalk_core import __version__

API_TITLE = "TimberTalk Core API"
API_DESCRIPTION = (
    "Backend für Zimmereien: Stammdaten, Projekte, Arbeitspakete und Buchungen. "
    "Die Geschäftslogik liegt in der Service-Schicht; diese API ist nur ein Adapter."
)


def create_app() -> FastAPI:
    """Erzeugt die FastAPI-Anwendung samt Routern und Fehlerbehandlung."""
    application = FastAPI(
        title=API_TITLE,
        description=API_DESCRIPTION,
        version=__version__,
    )

    @application.get("/health", tags=["system"], summary="Verfügbarkeit prüfen")
    def health() -> dict[str, Any]:
        """Meldet, dass das Backend erreichbar ist."""
        return {"status": "ok", "version": __version__}

    return application


app = create_app()
