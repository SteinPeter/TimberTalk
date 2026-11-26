# Die Endpunkte des Features „Dashboard“ (F12) unter /api/dashboard. Jede Person sieht und ändert
# nur ihre eigene Auswahl. Das Objekt `router` muss bleiben: load_features() hängt es an die App.

# ruff: noqa: B008 – FastAPI erwartet Depends(...) als Standardwert, siehe materials/api.py.

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from timbertalk.db import get_session
from timbertalk.features.accounts.deps import current_account
from timbertalk.features.accounts.models import Account
from timbertalk.features.dashboard import service
from timbertalk.features.dashboard.models import LayoutInfo, WidgetInfo

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/widgets")
def available_widgets() -> list[WidgetInfo]:
    return service.available_widgets()


@router.get("/layout")
def get_layout(
    account: Account = Depends(current_account), session: Session = Depends(get_session)
) -> LayoutInfo:
    return service.get_layout(session, account.id)


@router.put("/layout", summary="Dashboard anpassen")
def save_layout(
    data: LayoutInfo,
    account: Account = Depends(current_account),
    session: Session = Depends(get_session),
) -> LayoutInfo:
    try:
        return service.save_layout(session, account.id, data.widgets)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
