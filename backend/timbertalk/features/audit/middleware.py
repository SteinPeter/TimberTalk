# Die Middleware des Änderungsprotokolls: Sie steht vor allen Endpunkten (main.py hängt sie an die
# App) und schreibt nach jeder erfolgreichen Änderung einen Eintrag.
#
# Eine Middleware ist ein Stück Code, das jede Anfrage auf dem Weg hinein und jede Antwort auf dem
# Weg hinaus sieht. Diese hier merkt sich die gesendeten Angaben (Body) und den Statuscode der
# Antwort. War es eine Änderung (POST, PUT, PATCH, DELETE) unter /api und ging sie gut (Status
# unter 400), schreibt sie ins Protokoll:
#   Bereich = erster Tag des Routers (z. B. „Material, Fahrten und Preise“)
#   Was     = summary des Endpunkts (z. B. „Preis eintragen“), sonst sein Funktionsname
#   Wer     = das angemeldete Konto (aus dem Cookie)
# Lesende Anfragen (GET) werden nicht protokolliert.

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from timbertalk.db import get_session
from timbertalk.features.accounts import service as accounts
from timbertalk.features.accounts.deps import session_token
from timbertalk.features.audit import service

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Diese Änderungen sind kein Fall fürs Protokoll (an- und abmelden, Mitteilungen gelesen,
# eigenes Dashboard).
SKIP_PATHS = {
    "/api/accounts/login",
    "/api/accounts/logout",
    "/api/notifications/read-all",
    "/api/dashboard/layout",  # die eigene Startseite – keine Änderung am Betrieb
}


class AuditMiddleware:
    """Schreibt erfolgreiche Änderungen über die API ins Änderungsprotokoll."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or scope["method"] not in WRITE_METHODS
            or not scope["path"].startswith("/api/")
            or scope["path"] in SKIP_PATHS
        ):
            await self.app(scope, receive, send)
            return

        body = bytearray()
        status = {"code": 500}

        async def receive_and_keep() -> Message:
            message = await receive()
            if message["type"] == "http.request":
                body.extend(message.get("body", b""))
            return message

        async def send_and_note(message: Message) -> None:
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
            await send(message)

        await self.app(scope, receive_and_keep, send_and_note)
        if status["code"] < 400:
            # Die Datenbank arbeitet nicht asynchron – deshalb in einem eigenen Thread.
            await run_in_threadpool(_write, scope, bytes(body))


def _write(scope: Scope, body: bytes) -> None:
    route = scope.get("route")
    area = route.tags[0] if route is not None and getattr(route, "tags", None) else "Sonstiges"
    action = (getattr(route, "summary", None) or getattr(route, "name", "")) or scope["path"]
    # Dieselbe Datenbank-Sitzung wie die Endpunkte – in Tests also die Test-Datenbank.
    session_factory = scope["app"].dependency_overrides.get(get_session, get_session)
    sessions = session_factory()
    session = next(sessions)
    try:
        token = session_token(Request(scope))
        account = accounts.account_for_token(session, token) if token else None
        service.record(
            session,
            account_id=account.id if account else None,
            account_name=account.display_name if account else "unbekannt",
            area=area,
            action=action,
            target=service.describe_target(scope.get("path_params", {})),
            details=service.describe_body(body),
            method=scope["method"],
            path=scope["path"],
        )
    finally:
        sessions.close()
