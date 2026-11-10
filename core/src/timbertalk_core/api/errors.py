"""Abbildung fachlicher Fehler auf Problem-JSON (RFC 9457)."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from timbertalk_core.errors import Conflict, TimberTalkError, ValidationFailed

PROBLEM_MEDIA_TYPE = "application/problem+json"
PROBLEM_BASE = "https://timbertalk.local/probleme"

TITLES: dict[str, str] = {
    "not_found": "Nicht gefunden",
    "conflict": "Konflikt mit dem aktuellen Datenstand",
    "invalid_state": "Im aktuellen Status nicht erlaubt",
    "validation_failed": "Eingabe ungültig",
    "permission_denied": "Nicht erlaubt",
    "error": "Fehler",
}


def problem_response(
    *,
    code: str,
    detail: str,
    http_status: int,
    errors: dict[str, str] | None = None,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    """Baut eine Problem-JSON-Antwort.

    Parameter:
        code: Fehlercode des Backends, z. B. `not_found`.
        detail: deutsche Beschreibung für Menschen.
        http_status: HTTP-Statuscode.
        errors: Feldfehler, Feldname auf Meldung.
        extra: zusätzliche Angaben zum Fehler.
    """
    body: dict[str, Any] = {
        "type": f"{PROBLEM_BASE}/{code}",
        "title": TITLES.get(code, TITLES["error"]),
        "status": http_status,
        "detail": detail,
        "code": code,
    }
    if errors:
        body["errors"] = errors
    if extra:
        body["context"] = extra
    return JSONResponse(status_code=http_status, content=body, media_type=PROBLEM_MEDIA_TYPE)


def register_error_handlers(app: FastAPI) -> None:
    """Registriert die Fehlerbehandlung der Anwendung."""

    @app.exception_handler(TimberTalkError)
    async def _fachlicher_fehler(_request: Request, exc: TimberTalkError) -> JSONResponse:
        return problem_response(
            code=exc.code,
            detail=exc.message,
            http_status=exc.http_status,
            errors=getattr(exc, "errors", None),
            extra=exc.details or None,
        )

    @app.exception_handler(RequestValidationError)
    async def _eingabefehler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        felder: dict[str, str] = {}
        for fehler in exc.errors():
            pfad = ".".join(str(teil) for teil in fehler["loc"][1:]) or str(fehler["loc"][0])
            felder[pfad] = str(fehler["msg"])
        return problem_response(
            code="validation_failed",
            detail="Die übergebenen Daten sind ungültig.",
            http_status=status.HTTP_422_UNPROCESSABLE_CONTENT,
            errors=felder,
        )

    @app.exception_handler(StaleDataError)
    async def _versionskonflikt(_request: Request, _exc: StaleDataError) -> JSONResponse:
        konflikt = Conflict(
            "Der Datensatz wurde zwischenzeitlich von jemand anderem geändert; "
            "bitte neu laden und erneut versuchen."
        )
        return problem_response(code=konflikt.code, detail=konflikt.message, http_status=konflikt.http_status)

    @app.exception_handler(IntegrityError)
    async def _integritaetsfehler(_request: Request, _exc: IntegrityError) -> JSONResponse:
        konflikt = Conflict(
            "Der Vorgang verletzt eine Regel der Datenbank, etwa eine Eindeutigkeit "
            "oder einen Verweis auf einen fehlenden Datensatz."
        )
        return problem_response(code=konflikt.code, detail=konflikt.message, http_status=konflikt.http_status)

    @app.exception_handler(ValueError)
    async def _wertfehler(_request: Request, exc: ValueError) -> JSONResponse:
        ungueltig = ValidationFailed(str(exc))
        return problem_response(
            code=ungueltig.code, detail=ungueltig.message, http_status=ungueltig.http_status
        )
