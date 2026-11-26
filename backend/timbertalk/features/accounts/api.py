# Die Endpunkte des Features „Benutzerkonten und Rechte“ unter /api/accounts.
# Ein Endpunkt nimmt die Anfrage an, ruft eine Funktion aus service.py auf und gibt das Ergebnis
# zurück. Dazu kommt hier nur, was HTTP betrifft: das Cookie mit dem Sitzungsschlüssel setzen und
# löschen und Fehler des Service in Antworten mit deutschem Text übersetzen.
# Das Objekt `router` muss bleiben: load_features() hängt es an die App.

# ruff: noqa: B008 – FastAPI erwartet Depends(...) als Standardwert, siehe materials/api.py.

from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlmodel import Session

from timbertalk.db import get_session
from timbertalk.features.accounts import service
from timbertalk.features.accounts.deps import (
    COOKIE_NAME,
    current_account,
    require,
    session_token,
)
from timbertalk.features.accounts.models import (
    Account,
    AccountIn,
    AccountInfo,
    AccountUpdateIn,
    CreatedAccount,
    LoginIn,
    Me,
    PasswordChangeIn,
    PermissionIn,
    ResetPasswordIn,
    RoleMatrix,
    StartPassword,
)

router = APIRouter(prefix="/api/accounts", tags=["Benutzerkonten und Rechte"])


def _run(function: Callable, *args):
    """Ruft eine Service-Funktion auf und macht aus ihren Fehlern eine Antwort mit Text."""
    try:
        return function(*args)
    except service.LoginFailed as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


# --- Anmelden und eigenes Konto -------------------------------------------------------


@router.post("/login")
def login(data: LoginIn, response: Response, session: Session = Depends(get_session)) -> Me:
    account, token = _run(service.login, session, data.identifier, data.password)
    # httponly: JavaScript kommt nicht an den Schlüssel. samesite=strict: fremde Seiten können
    # keine Anfragen mit diesem Cookie schicken.
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=service.SESSION_DAYS * 24 * 60 * 60,
        httponly=True,
        samesite="strict",
        path="/",
    )
    return service.me(session, account)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, session: Session = Depends(get_session)) -> None:
    token = session_token(request)
    if token:
        service.logout(session, token)
    response.delete_cookie(COOKIE_NAME, path="/")


@router.get("/me")
def get_me(
    account: Account = Depends(current_account), session: Session = Depends(get_session)
) -> Me:
    return service.me(session, account)


@router.post("/me/password", summary="Eigenes Passwort ändern")
def change_password(
    data: PasswordChangeIn,
    request: Request,
    account: Account = Depends(current_account),
    session: Session = Depends(get_session),
) -> Me:
    _run(
        service.change_own_password,
        session,
        account,
        data.old_password,
        data.new_password,
        session_token(request),
    )
    return service.me(session, account)


# --- Konten verwalten (Recht „accounts.manage“) ------------------------------------------


@router.get("")
def list_accounts(
    _: Account = Depends(require("accounts.manage")), session: Session = Depends(get_session)
) -> list[AccountInfo]:
    return service.list_accounts(session)


@router.post("", status_code=201, summary="Konto anlegen")
def create_account(
    data: AccountIn,
    acting: Account = Depends(require("accounts.manage")),
    session: Session = Depends(get_session),
) -> CreatedAccount:
    account, start_password = _run(
        service.create_account,
        session,
        data.username,
        data.display_name,
        data.role,
        data.personnel_number,
        data.start_password,
        acting,
    )
    return CreatedAccount(account=service.info(account), start_password=start_password)


@router.put("/{account_id}", summary="Konto ändern")
def update_account(
    account_id: int,
    data: AccountUpdateIn,
    acting: Account = Depends(require("accounts.manage")),
    session: Session = Depends(get_session),
) -> AccountInfo:
    account = _run(
        service.update_account,
        session,
        account_id,
        data.display_name,
        data.role,
        data.personnel_number,
        data.active,
        acting,
    )
    return service.info(account)


@router.post("/{account_id}/reset-password", summary="Passwort zurücksetzen")
def reset_password(
    account_id: int,
    data: ResetPasswordIn,
    acting: Account = Depends(require("accounts.manage")),
    session: Session = Depends(get_session),
) -> StartPassword:
    start_password = _run(service.reset_password, session, account_id, data.start_password, acting)
    return StartPassword(start_password=start_password)


# --- Rollen und Rechte (Recht „accounts.manage“) -----------------------------------------


@router.get("/roles")
def role_matrix(
    _: Account = Depends(require("accounts.manage")), session: Session = Depends(get_session)
) -> RoleMatrix:
    return service.role_matrix(session)


@router.put("/roles/{role}/permissions/{permission}", summary="Recht einer Rolle ändern")
def set_role_permission(
    role: str,
    permission: str,
    data: PermissionIn,
    acting: Account = Depends(require("accounts.manage")),
    session: Session = Depends(get_session),
) -> RoleMatrix:
    return _run(service.set_role_permission, session, role, permission, data.allowed, acting)
