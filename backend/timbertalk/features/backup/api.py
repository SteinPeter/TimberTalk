# Die Endpunkte des Features „Datensicherung, Wiederherstellung und Export“ unter /api/backup.
# Ein Endpunkt nimmt die Anfrage an, ruft eine Funktion aus service.py auf und gibt das Ergebnis
# zurück – sonst nichts. Die Sitzung kommt aus Depends(get_session).
# Das Objekt `router` muss bleiben: load_features() hängt es an die App.
#
# Einstellungen exportieren und importieren darf nur, wer Preise und Firmendaten ändern darf
# („finance.edit“) – in der Datei stehen Preise, Stundensätze und die Bankverbindung.
# ruff: noqa: B008 – FastAPI erwartet Depends(...) als Standardwert, siehe materials/api.py.

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from timbertalk.db import get_session
from timbertalk.features.accounts.deps import require
from timbertalk.features.accounts.models import Account
from timbertalk.features.backup import service
from timbertalk.features.backup.models import ImportResult, SettingsFile

router = APIRouter(prefix="/api/backup", tags=["Datensicherung, Wiederherstellung und Export"])


@router.get("/settings")
def export_settings(
    _: Account = Depends(require("finance.edit")), session: Session = Depends(get_session)
) -> SettingsFile:
    return service.export_settings(session)


@router.post("/settings", summary="Einstellungen importieren")
def import_settings(
    data: SettingsFile,
    _: Account = Depends(require("finance.edit")),
    session: Session = Depends(get_session),
) -> ImportResult:
    try:
        return service.import_settings(session, data)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
