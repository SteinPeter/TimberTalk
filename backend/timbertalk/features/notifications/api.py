# Die Endpunkte des Features „Mitteilungen“ unter /api/notifications.
# Jeder sieht nur seine eigenen Mitteilungen. Schreiben tun andere Features über service.notify().
# Das Objekt `router` muss bleiben: load_features() hängt es an die App.

# ruff: noqa: B008 – FastAPI erwartet Depends(...) als Standardwert, siehe materials/api.py.

from fastapi import APIRouter, Depends
from sqlmodel import Session

from timbertalk.db import get_session
from timbertalk.features.accounts.deps import current_account
from timbertalk.features.accounts.models import Account
from timbertalk.features.notifications import service
from timbertalk.features.notifications.models import Notification, UnreadCount

router = APIRouter(prefix="/api/notifications", tags=["Mitteilungen"])


@router.get("")
def list_notifications(
    account: Account = Depends(current_account), session: Session = Depends(get_session)
) -> list[Notification]:
    return service.list_notifications(session, account.id)


@router.get("/unread-count")
def unread_count(
    account: Account = Depends(current_account), session: Session = Depends(get_session)
) -> UnreadCount:
    return UnreadCount(unread=service.unread_count(session, account.id))


@router.post("/read-all", status_code=204)
def mark_all_read(
    account: Account = Depends(current_account), session: Session = Depends(get_session)
) -> None:
    service.mark_all_read(session, account.id)
