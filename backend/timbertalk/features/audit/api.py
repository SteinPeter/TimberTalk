# Die Endpunkte des Features „Änderungsprotokoll“ unter /api/audit. Nur lesen, nur mit dem Recht
# „audit.view“. Geschrieben wird das Protokoll von middleware.py.
# Das Objekt `router` muss bleiben: load_features() hängt es an die App.

# ruff: noqa: B008 – FastAPI erwartet Depends(...) als Standardwert, siehe materials/api.py.

from fastapi import APIRouter, Depends
from sqlmodel import Session

from timbertalk.db import get_session
from timbertalk.features.accounts.deps import require
from timbertalk.features.accounts.models import Account
from timbertalk.features.audit import service
from timbertalk.features.audit.models import AuditEvent

router = APIRouter(prefix="/api/audit", tags=["Änderungsprotokoll"])


@router.get("")
def list_events(
    area: str | None = None,
    _: Account = Depends(require("audit.view")),
    session: Session = Depends(get_session),
) -> list[AuditEvent]:
    return service.list_events(session, area)


@router.get("/areas")
def list_areas(
    _: Account = Depends(require("audit.view")), session: Session = Depends(get_session)
) -> list[str]:
    return service.list_areas(session)
