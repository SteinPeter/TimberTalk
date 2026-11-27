# Die Endpunkte des Features „Mitarbeitende“ (F14) unter /api/employees.
# Ein Endpunkt nimmt die Anfrage an, ruft eine Funktion aus service.py auf und gibt das Ergebnis
# zurück – sonst nichts. Die Sitzung kommt aus Depends(get_session).
# Das Objekt `router` muss bleiben: load_features() hängt es an die App.
#
# Rechte: die eigenen Konten sieht jeder; alle anderen nur mit „employees.view_all“ oder
# „employees.manage“ (sonst 403 bzw. 404). Soll-Stunden, Urlaubsanspruch und Resturlaub ändert nur,
# wer „employees.manage“ hat.
# ruff: noqa: B008 – FastAPI erwartet Depends(...) als Standardwert, siehe materials/api.py.

from collections.abc import Callable
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from timbertalk.db import get_session
from timbertalk.features.accounts.deps import can, current_account, require
from timbertalk.features.accounts.models import Account
from timbertalk.features.employees import service
from timbertalk.features.employees.models import (
    CarryoverIn,
    ContractIn,
    EmployeeSummary,
    VacationPreview,
)

router = APIRouter(prefix="/api/employees", tags=["Mitarbeitende"])


def _run(function: Callable, *args):
    """Ruft eine Service-Funktion auf und macht aus ihren Fehlern die passende Antwort."""
    try:
        return function(*args)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


def _year(year: int | None) -> int:
    return year or date.today().year


@router.get("/me")
def my_summary(
    year: int | None = None,
    account: Account = Depends(current_account),
    session: Session = Depends(get_session),
) -> EmployeeSummary:
    return _run(service.summary, session, account.id, _year(year))


@router.get("/me/vacation-preview")
def my_vacation_preview(
    start: date,
    end: date,
    account: Account = Depends(current_account),
    session: Session = Depends(get_session),
) -> VacationPreview:
    return _run(service.vacation_preview, session, account.id, start, end)


@router.get("/overview")
def overview(
    year: int | None = None,
    view_all: bool = Depends(can("employees.view_all")),
    manage: bool = Depends(can("employees.manage")),
    session: Session = Depends(get_session),
) -> list[EmployeeSummary]:
    return _run(service.overview, session, _year(year), view_all, manage)


@router.get("/{account_id}")
def person_summary(
    account_id: int,
    year: int | None = None,
    account: Account = Depends(current_account),
    view_all: bool = Depends(can("employees.view_all")),
    manage: bool = Depends(can("employees.manage")),
    session: Session = Depends(get_session),
) -> EmployeeSummary:
    return _run(
        service.visible_summary, session, account.id, view_all, manage, account_id, _year(year)
    )


@router.put("/{account_id}/contract", summary="Soll-Stunden und Urlaubsanspruch speichern")
def save_contract(
    account_id: int,
    data: ContractIn,
    _: Account = Depends(require("employees.manage")),
    session: Session = Depends(get_session),
) -> EmployeeSummary:
    return _run(service.save_contract, session, account_id, data)


@router.put("/{account_id}/carryover/{year}", summary="Resturlaub aus dem Vorjahr eintragen")
def set_carryover(
    account_id: int,
    year: int,
    data: CarryoverIn,
    _: Account = Depends(require("employees.manage")),
    session: Session = Depends(get_session),
) -> EmployeeSummary:
    return _run(service.set_carryover, session, account_id, year, data.days)
