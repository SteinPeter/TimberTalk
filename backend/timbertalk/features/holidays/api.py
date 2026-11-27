# Die Endpunkte des Features „Feiertage“ (F15) unter /api/holidays.
# Ein Endpunkt nimmt die Anfrage an, ruft eine Funktion aus service.py auf und gibt das Ergebnis
# zurück – sonst nichts. Die Sitzung kommt aus Depends(get_session).
# Das Objekt `router` muss bleiben: load_features() hängt es an die App.
#
# Lesen darf jeder (der Kalender zeigt die Feiertage allen). Das Bundesland festlegen darf, wer die
# Firmendaten ändern darf („finance.edit“) – es gehört zur Adresse des Betriebs.
# ruff: noqa: B008 – FastAPI erwartet Depends(...) als Standardwert, siehe materials/api.py.

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from timbertalk.db import get_session
from timbertalk.features.accounts.deps import require
from timbertalk.features.accounts.models import Account
from timbertalk.features.holidays import service
from timbertalk.features.holidays.models import Holiday, StateIn, StateInfo, StateOption

router = APIRouter(prefix="/api/holidays", tags=["Feiertage"])


@router.get("")
def list_holidays(start: date, end: date, session: Session = Depends(get_session)) -> list[Holiday]:
    try:
        return service.holidays_between(session, start, end)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/state")
def current_state(session: Session = Depends(get_session)) -> StateInfo:
    return service.current_state(session)


@router.get("/states")
def list_states() -> list[StateOption]:
    return service.list_states()


@router.put("/state", summary="Bundesland für Feiertage festlegen")
def set_state(
    data: StateIn,
    _: Account = Depends(require("finance.edit")),
    session: Session = Depends(get_session),
) -> StateInfo:
    try:
        return service.set_state(session, data.state)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
