# Bausteine für alle Endpunkte: Wer ist angemeldet, und darf er das?
#
# - require_login   hängt main.py an JEDEN Feature-Router. Ohne Anmeldung antwortet die API mit
#                   401. Ausnahme ist nur PUBLIC_PATHS (die Anmeldung selbst).
# - current_account liefert das angemeldete Konto, z. B. für „wer hat das gebucht?“.
# - require("…")    lässt den Endpunkt nur mit diesem Recht zu, sonst 403.
# - can("…")        sagt nur Ja oder Nein, z. B. um Preise auszublenden statt abzulehnen.
#
# So benutzt ein Feature sie in seiner api.py:
#
#     @router.post("/items/{material_id}/prices")
#     def add_price(..., _: Account = Depends(require("finance.edit"))): ...
#
# Die Rechte selbst stehen in permissions.py.

# ruff: noqa: B008 – FastAPI erwartet Depends(...) als Standardwert, siehe materials/api.py.

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request
from sqlmodel import Session

from timbertalk.db import get_session
from timbertalk.features.accounts import service
from timbertalk.features.accounts.models import Account
from timbertalk.features.accounts.permissions import PERMISSIONS

# Name des Cookies, in dem der Browser den Sitzungsschlüssel hält.
COOKIE_NAME = "timbertalk_session"

# Diese Adressen gehen ohne Anmeldung.
PUBLIC_PATHS = {
    "/api/accounts/login",
    "/api/accounts/login-info",  # Demo-Modus? Anmeldedaten für die Entwicklung?
    "/api/accounts/demo-login",  # geht nur, wenn der Demo-Modus an ist
}

# Adressen, die mit diesem Anfang ohne Anmeldung gehen. Der Kalender-Abo-Link (F8) muss von der
# Kalender-App des Handys abrufbar sein, die sich nicht anmelden kann; dort schützt ein geheimer,
# langer Schlüssel in der Adresse selbst.
PUBLIC_PREFIXES = ("/api/planning/ical/",)

# Diese Adressen gehen auch, solange jemand noch sein Startpasswort ersetzen muss.
PASSWORD_CHANGE_PATHS = {
    "/api/accounts/me",
    "/api/accounts/me/password",
    "/api/accounts/logout",
}


def session_token(request: Request) -> str | None:
    """Der Sitzungsschlüssel aus dem Cookie – oder, für spätere Apps, aus dem Kopf
    `Authorization: Bearer <Schlüssel>`."""
    token = request.cookies.get(COOKIE_NAME)
    if token:
        return token
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip() or None
    return None


def _account_or_401(request: Request, session: Session) -> Account:
    token = session_token(request)
    account = service.account_for_token(session, token) if token else None
    if account is None:
        raise HTTPException(status_code=401, detail="Bitte zuerst anmelden.")
    return account


def current_account(request: Request, session: Session = Depends(get_session)) -> Account:
    """Das angemeldete Konto. Ohne gültige Anmeldung: 401."""
    return _account_or_401(request, session)


def require_login(request: Request, session: Session = Depends(get_session)) -> None:
    """Für alle Feature-Router (main.py): nur mit Anmeldung, und erst nach dem eigenen Passwort."""
    path = request.url.path
    if path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES):
        return
    account = _account_or_401(request, session)
    # Im Demo-Modus muss niemand zuerst ein eigenes Passwort festlegen.
    if (
        account.must_change_password
        and request.url.path not in PASSWORD_CHANGE_PATHS
        and not service.demo_mode(session)
    ):
        raise HTTPException(status_code=403, detail="Bitte zuerst ein eigenes Passwort festlegen.")


def require(permission: str) -> Callable[..., Account]:
    """Ein Baustein, der den Endpunkt nur mit diesem Recht zulässt. Gibt das Konto zurück."""
    if permission not in PERMISSIONS:
        raise RuntimeError(f"Das Recht „{permission}“ steht nicht in permissions.py.")

    def dependency(
        account: Account = Depends(current_account), session: Session = Depends(get_session)
    ) -> Account:
        if not service.has_permission(session, account, permission):
            raise HTTPException(
                status_code=403,
                detail=f"Dafür fehlt Ihnen das Recht „{PERMISSIONS[permission]}“.",
            )
        return account

    return dependency


def can(permission: str) -> Callable[..., bool]:
    """Ein Baustein, der nur sagt, ob das angemeldete Konto dieses Recht hat."""
    if permission not in PERMISSIONS:
        raise RuntimeError(f"Das Recht „{permission}“ steht nicht in permissions.py.")

    def dependency(
        account: Account = Depends(current_account), session: Session = Depends(get_session)
    ) -> bool:
        return service.has_permission(session, account, permission)

    return dependency
