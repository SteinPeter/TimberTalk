# Die Endpunkte des Features „Planung: Kalender je Mitarbeiter“ (F8) unter /api/planning.
# Ein Endpunkt nimmt die Anfrage an, ruft eine Funktion aus service.py auf und gibt das Ergebnis
# zurück. Fehler des Service werden zu Antworten mit deutschem Text.
#
# Rechte (F10): Lesen darf jeder Angemeldete – mit „calendar.view_all“ alle Kalender, sonst nur
# den eigenen. Eintragen, ändern und löschen braucht „calendar.dispatch“. Urlaub beantragen
# braucht „calendar.request_absence“, genehmigen „calendar.approve_absence“. Der Abo-Link
# /ical/<schlüssel>.ics geht ohne Anmeldung (accounts/deps.py, PUBLIC_PREFIXES).
# Das Objekt `router` muss bleiben: load_features() hängt es an die App.

# ruff: noqa: B008 – FastAPI erwartet Depends(...) als Standardwert, siehe materials/api.py.

from collections.abc import Callable
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session

from timbertalk.db import get_session
from timbertalk.features.accounts.deps import can, current_account, require
from timbertalk.features.accounts.models import Account, Person
from timbertalk.features.planning import service
from timbertalk.features.planning.models import (
    Decision,
    DecisionIn,
    EntryIn,
    EntryInfo,
    IcalLink,
    KindInfo,
    RateIn,
    RequestIn,
    RequestInfo,
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


@router.post("/entries", status_code=201, summary="Termin eintragen")
def create_entry(
    data: EntryIn,
    account: Account = Depends(require("calendar.dispatch")),
    session: Session = Depends(get_session),
) -> SavedEntry:
    return _run(service.create_entry, session, data, account.id)


@router.put("/entries/{entry_id}", summary="Termin ändern")
def update_entry(
    entry_id: int,
    data: EntryIn,
    account: Account = Depends(require("calendar.dispatch")),
    session: Session = Depends(get_session),
) -> SavedEntry:
    return _run(service.update_entry, session, entry_id, data, account.id)


@router.delete("/entries/{entry_id}", status_code=204, summary="Termin löschen")
def delete_entry(
    entry_id: int,
    account: Account = Depends(require("calendar.dispatch")),
    session: Session = Depends(get_session),
) -> None:
    _run(service.delete_entry, session, entry_id, account.id)


# --- Fahrzeuge und Maschinen: sehen darf jeder, pflegen wer plant ---------------------


@router.get("/resources")
def list_resources(
    include_inactive: bool = False,
    show_rates: bool = Depends(can("finance.view")),
    session: Session = Depends(get_session),
) -> list[ResourceInfo]:
    return service.list_resources(session, include_inactive, show_rates)


@router.put("/resources/{resource_id}/rate", summary="Kilometersatz eines Fahrzeugs ändern")
def set_vehicle_rate(
    resource_id: int,
    data: RateIn,
    _: Account = Depends(require("finance.edit")),
    session: Session = Depends(get_session),
) -> ResourceInfo:
    return _run(service.set_vehicle_rate, session, resource_id, data.rate_per_km)


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


# --- Urlaubsanträge ---------------------------------------------------------------------


@router.get("/requests")
def list_requests(
    account: Account = Depends(current_account),
    may_approve: bool = Depends(can("calendar.approve_absence")),
    session: Session = Depends(get_session),
) -> list[RequestInfo]:
    return service.list_requests(session, account.id, may_approve)


@router.post("/requests", status_code=201, summary="Urlaub beantragen")
def request_absence(
    data: RequestIn,
    account: Account = Depends(require("calendar.request_absence")),
    session: Session = Depends(get_session),
) -> RequestInfo:
    return _run(service.request_absence, session, account.id, data)


@router.post("/requests/{request_id}/approve", summary="Urlaub genehmigen")
def approve_request(
    request_id: int,
    data: DecisionIn,
    account: Account = Depends(require("calendar.approve_absence")),
    session: Session = Depends(get_session),
) -> Decision:
    return _run(service.decide_request, session, request_id, True, account.id, data.note)


@router.post("/requests/{request_id}/reject", summary="Urlaub ablehnen")
def reject_request(
    request_id: int,
    data: DecisionIn,
    account: Account = Depends(require("calendar.approve_absence")),
    session: Session = Depends(get_session),
) -> Decision:
    return _run(service.decide_request, session, request_id, False, account.id, data.note)


@router.delete("/requests/{request_id}", status_code=204, summary="Urlaubsantrag zurückziehen")
def withdraw_request(
    request_id: int,
    account: Account = Depends(current_account),
    session: Session = Depends(get_session),
) -> None:
    _run(service.withdraw_request, session, request_id, account.id)


# --- Kalender-Abo (iCal) ------------------------------------------------------------------


@router.get("/ical-link")
def ical_link(
    account: Account = Depends(current_account), session: Session = Depends(get_session)
) -> IcalLink:
    return service.ical_link(session, account.id)


@router.post("/ical-link", summary="Kalender-Abo-Link erzeugen")
def new_ical_link(
    account: Account = Depends(current_account), session: Session = Depends(get_session)
) -> IcalLink:
    return service.new_ical_link(session, account.id)


@router.delete("/ical-link", status_code=204, summary="Kalender-Abo-Link ungültig machen")
def delete_ical_link(
    account: Account = Depends(current_account), session: Session = Depends(get_session)
) -> None:
    service.delete_ical_link(session, account.id)


@router.get("/ical/{token}.ics")
def ical_feed(token: str, session: Session = Depends(get_session)) -> Response:
    # Ohne Anmeldung (Kalender-Apps können sich nicht anmelden) – der Schlüssel ist der Schutz.
    text = _run(service.ical_feed, session, token)
    return Response(content=text, media_type="text/calendar; charset=utf-8")
