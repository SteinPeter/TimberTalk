# Die Endpunkte des Features „Material, Fahrten und Preise“ unter /api/materials.
# Ein Endpunkt nimmt die Anfrage an, ruft eine Funktion aus service.py auf und gibt das Ergebnis
# zurück – sonst nichts. Die Sitzung kommt aus Depends(get_session).
# Nur eines kommt dazu: Meldet der Service einen Fehler (ValueError: die Angabe passt nicht,
# LookupError: gibt es nicht), wird daraus eine Antwort mit deutschem Text.
# Das Objekt `router` muss bleiben: load_features() hängt es an die App.

# ruff meldet B008 bei jedem `Depends(...)` im Parameter. Genau so schreibt es CLAUDE.md aber vor
# (und FastAPI erwartet es), deshalb ist die Regel in dieser Datei ausgeschaltet.
# ruff: noqa: B008

from collections.abc import Callable
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from timbertalk.db import get_session
from timbertalk.features.materials import service
from timbertalk.features.materials.models import (
    Booking,
    BookingInfo,
    Company,
    CompanyIn,
    HourlyRate,
    HourlyRateIn,
    MaterialBookingIn,
    MaterialIn,
    MaterialInfo,
    MaterialItem,
    MaterialPrice,
    PriceIn,
    ProjectCosts,
    TravelBookingIn,
)

router = APIRouter(prefix="/api/materials", tags=["Material, Fahrten und Preise"])


def _run(function: Callable, *args):
    """Ruft eine Service-Funktion auf und macht aus ihren Fehlern eine Antwort mit Text."""
    try:
        return function(*args)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


# --- Materialstamm und Preise -----------------------------------------------------


@router.get("/items")
def list_materials(
    kategorie: str | None = None,
    on_date: date | None = None,
    session: Session = Depends(get_session),
) -> list[MaterialInfo]:
    return service.list_materials(session, kategorie, on_date)


@router.post("/items", status_code=201)
def create_material(data: MaterialIn, session: Session = Depends(get_session)) -> MaterialItem:
    return _run(service.create_material, session, data.name, data.category, data.unit)


@router.get("/items/{material_id}/prices")
def list_prices(material_id: int, session: Session = Depends(get_session)) -> list[MaterialPrice]:
    return _run(service.list_prices, session, material_id)


@router.post("/items/{material_id}/prices", status_code=201)
def add_price(
    material_id: int, data: PriceIn, session: Session = Depends(get_session)
) -> MaterialPrice:
    return _run(service.add_price, session, material_id, data.unit_price, data.valid_from)


# --- Stammdaten der Abrechnung ----------------------------------------------------


@router.get("/company")
def get_company(session: Session = Depends(get_session)) -> Company:
    return service.get_company(session)


@router.put("/company")
def save_company(data: CompanyIn, session: Session = Depends(get_session)) -> Company:
    return _run(service.save_company, session, data)


@router.get("/hourly-rates")
def list_hourly_rates(session: Session = Depends(get_session)) -> list[HourlyRate]:
    return service.list_hourly_rates(session)


@router.put("/hourly-rates")
def save_hourly_rate(data: HourlyRateIn, session: Session = Depends(get_session)) -> HourlyRate:
    return _run(service.save_hourly_rate, session, data.name, data.rate)


@router.delete("/hourly-rates/{hourly_rate_id}", status_code=204)
def delete_hourly_rate(hourly_rate_id: int, session: Session = Depends(get_session)) -> None:
    _run(service.delete_hourly_rate, session, hourly_rate_id)


# --- Buchen und Kosten ------------------------------------------------------------


@router.get("/bookings")
def list_bookings(project_id: int, session: Session = Depends(get_session)) -> list[BookingInfo]:
    return service.list_bookings(session, project_id)


@router.post("/bookings/material", status_code=201)
def book_material(data: MaterialBookingIn, session: Session = Depends(get_session)) -> Booking:
    return _run(
        service.book_material,
        session,
        data.project_id,
        data.material_id,
        data.quantity,
        data.booking_date,
    )


@router.post("/bookings/travel", status_code=201)
def book_travel(data: TravelBookingIn, session: Session = Depends(get_session)) -> Booking:
    return _run(service.book_travel, session, data.project_id, data.km, data.booking_date)


@router.get("/projects/{project_id}/costs")
def project_costs(project_id: int, session: Session = Depends(get_session)) -> ProjectCosts:
    return service.project_costs(session, project_id)
