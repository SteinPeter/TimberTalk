# Die Endpunkte des Features „Planung: Kalender je Mitarbeiter“ (F8) unter /api/planning.
# Ein Endpunkt nimmt die Anfrage an, ruft eine Funktion aus service.py auf und gibt das Ergebnis
# zurück. Fehler des Service werden zu Antworten mit deutschem Text.
#
# Rechte (F10): Lesen darf jeder Angemeldete – mit „calendar.view_all“ alle Kalender, sonst nur
# den eigenen. Eintragen, ändern und löschen braucht „calendar.dispatch“.
# Das Objekt `router` muss bleiben: load_features() hängt es an die App.

# ruff: noqa: B008 – FastAPI erwartet Depends(...) als Standardwert, siehe materials/api.py.

from collections.abc import Callable
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from timbertalk.db import get_session
from timbertalk.features.accounts.deps import can, current_account, require
from timbertalk.features.accounts.models import Account, Person
from timbertalk.features.planning import service
from timbertalk.features.planning.models import (
    EntryIn,
    EntryInfo,
    KindInfo,
    ResourceIn,
    ResourceInfo,
    SavedEntry,
)

router = APIRouter(prefix="/api/planning", tags=["Planung: Kalender je Mitarbeiter"])


def _run(function: Callable, *args):
    """Ruft eine Service-Funktion auf und macht aus ihren Fehlern eine Antwort mit Text."""
    try:
        return function(*args)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/kinds")
def list_kinds() -> list[KindInfo]:
    return service.kinds()


@router.get("/people")
def list_people(
    account: Account = Depends(current_account),
    view_all: bool = Depends(can("calendar.view_all")),
    session: Session = Depends(get_session),
) -> list[Person]:
    return service.visible_people(session, account.id, view_all)


@router.get("/entries")
def list_entries(
    start: date,
    end: date,
    account_id: int | None = None,
    account: Account = Depends(current_account),
    view_all: bool = Depends(can("calendar.view_all")),
    session: Session = Depends(get_session),
) -> list[EntryInfo]:
    return _run(service.list_entries, session, start, end, account.id, view_all, account_id)


@router.post("/entries", status_code=201)
def create_entry(
    data: EntryIn,
    account: Account = Depends(require("calendar.dispatch")),
    session: Session = Depends(get_session),
) -> SavedEntry:
    return _run(service.create_entry, session, data, account.id)


@router.put("/entries/{entry_id}")
def update_entry(
    entry_id: int,
    data: EntryIn,
    account: Account = Depends(require("calendar.dispatch")),
    session: Session = Depends(get_session),
) -> SavedEntry:
    return _run(service.update_entry, session, entry_id, data, account.id)


@router.delete("/entries/{entry_id}", status_code=204)
def delete_entry(
    entry_id: int,
    account: Account = Depends(require("calendar.dispatch")),
    session: Session = Depends(get_session),
) -> None:
    _run(service.delete_entry, session, entry_id, account.id)


# --- Fahrzeuge und Maschinen: sehen darf jeder, pflegen wer plant ---------------------


@router.get("/resources")
def list_resources(
    include_inactive: bool = False, session: Session = Depends(get_session)
) -> list[ResourceInfo]:
    return service.list_resources(session, include_inactive)


@router.post("/resources", status_code=201, summary="Fahrzeug oder Maschine anlegen")
def create_resource(
    data: ResourceIn,
    _: Account = Depends(require("calendar.dispatch")),
    session: Session = Depends(get_session),
) -> ResourceInfo:
    return _run(service.create_resource, session, data)


@router.put("/resources/{resource_id}", summary="Fahrzeug oder Maschine ändern")
def update_resource(
    resource_id: int,
    data: ResourceIn,
    _: Account = Depends(require("calendar.dispatch")),
    session: Session = Depends(get_session),
) -> ResourceInfo:
    return _run(service.update_resource, session, resource_id, data)
