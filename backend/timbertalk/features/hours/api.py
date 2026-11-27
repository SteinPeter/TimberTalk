# Die Endpunkte des Features „Stunden buchen“ (F4) unter /api/hours.
# Ein Endpunkt nimmt die Anfrage an, ruft eine Funktion aus service.py auf und gibt das Ergebnis
# zurück. Rechte (F10): „hours.book_own“ zum Buchen, „hours.view_all“ um die Stunden aller zu
# sehen, „hours.manage“ um für andere zu buchen und fremde Buchungen zu löschen.
# Das Objekt `router` muss bleiben: load_features() hängt es an die App.

# ruff: noqa: B008 – FastAPI erwartet Depends(...) als Standardwert, siehe materials/api.py.

from collections.abc import Callable
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from timbertalk.db import get_session
from timbertalk.features.accounts.deps import can, current_account, require
from timbertalk.features.accounts.models import Account
from timbertalk.features.hours import service
from timbertalk.features.hours.models import DayIn, HoursIn, HoursInfo, Suggestion

router = APIRouter(prefix="/api/hours", tags=["Stunden buchen"])


def _run(function: Callable, *args):
    """Ruft eine Service-Funktion auf und macht aus ihren Fehlern eine Antwort mit Text."""
    try:
        return function(*args)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/suggestions")
def suggestions(
    day: date,
    account: Account = Depends(require("hours.book_own")),
    session: Session = Depends(get_session),
) -> list[Suggestion]:
    return service.suggestions(session, account.id, day)


@router.get("")
def list_hours(
    start: date,
    end: date,
    account_id: int | None = None,
    account: Account = Depends(current_account),
    view_all: bool = Depends(can("hours.view_all")),
    session: Session = Depends(get_session),
) -> list[HoursInfo]:
    return _run(service.list_hours, session, start, end, account.id, view_all, account_id)


@router.post("", status_code=201, summary="Stunden buchen")
def book(
    data: HoursIn,
    account: Account = Depends(require("hours.book_own")),
    may_manage: bool = Depends(can("hours.manage")),
    session: Session = Depends(get_session),
) -> HoursInfo:
    return _run(service.book, session, data, account.id, may_manage)


@router.post("/confirm-day", status_code=201, summary="Stunden aus dem Kalender bestätigen")
def confirm_day(
    data: DayIn,
    account: Account = Depends(require("hours.book_own")),
    may_manage: bool = Depends(can("hours.manage")),
    session: Session = Depends(get_session),
) -> list[HoursInfo]:
    return _run(service.confirm_day, session, data.items, account.id, may_manage)


@router.delete("/{hours_id}", status_code=204, summary="Stunden löschen")
def delete_hours(
    hours_id: int,
    account: Account = Depends(current_account),
    may_manage: bool = Depends(can("hours.manage")),
    session: Session = Depends(get_session),
) -> None:
    _run(service.delete_hours, session, hours_id, account.id, may_manage)
