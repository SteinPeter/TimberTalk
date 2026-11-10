"""Transaktionsgrenze einer HTTP-Anfrage.

Die Transaktion wird hier abgeschlossen und **nicht** in einer Abhängigkeit mit `yield`:
Code nach einem `yield` läuft bei FastAPI erst, nachdem die Antwort gesendet wurde. Ein
`commit` an jener Stelle käme zu spät – die unmittelbar folgende Anfrage sähe den eigenen
Schreibvorgang unter Umständen noch nicht. Diese Mittelschicht schreibt die Transaktion
fest, bevor die Antwort das Backend verlässt.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware

from timbertalk_core.api.deps import SESSION_STATE_KEY
from timbertalk_core.api.errors import problem_response
from timbertalk_core.errors import Conflict

Weiter = Callable[[Request], Awaitable[Response]]


def _abschliessen(session: Session, *, festschreiben: bool) -> None:
    """Schreibt die Transaktion fest oder verwirft sie und gibt die Verbindung zurück."""
    try:
        if festschreiben:
            session.commit()
        else:
            session.rollback()
    finally:
        session.close()


class TransactionMiddleware(BaseHTTPMiddleware):
    """Öffnet keine Session, schließt aber die der Anfrage verlässlich ab."""

    async def dispatch(self, request: Request, call_next: Weiter) -> Response:
        """Führt die Anfrage aus und schließt die Transaktion vor dem Senden der Antwort."""
        try:
            response = await call_next(request)
        except Exception:
            await self._beenden(request, festschreiben=False)
            raise

        erfolgreich = response.status_code < status.HTTP_400_BAD_REQUEST
        try:
            await self._beenden(request, festschreiben=erfolgreich)
        except IntegrityError:
            konflikt = Conflict(
                "Der Vorgang verletzt eine Regel der Datenbank, etwa eine Eindeutigkeit "
                "oder einen Verweis auf einen fehlenden Datensatz."
            )
            return problem_response(
                code=konflikt.code, detail=konflikt.message, http_status=konflikt.http_status
            )
        return response

    @staticmethod
    async def _beenden(request: Request, *, festschreiben: bool) -> None:
        """Schließt die Session der Anfrage ab, falls eine geöffnet wurde."""
        session: Session | None = getattr(request.state, SESSION_STATE_KEY, None)
        if session is None:
            return
        setattr(request.state, SESSION_STATE_KEY, None)
        await run_in_threadpool(_abschliessen, session, festschreiben=festschreiben)
