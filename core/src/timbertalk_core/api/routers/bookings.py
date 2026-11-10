"""Router für Buchungen."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from timbertalk_core.api.deps import ApiKey, Context
from timbertalk_core.domain.bookings import service
from timbertalk_core.domain.bookings.details import registered_kinds
from timbertalk_core.domain.bookings.schemas import BookingCreate, BookingRead, BookingUpdate
from timbertalk_core.domain.enums import BookingStatus
from timbertalk_core.schemas import Page

router = APIRouter(prefix="/bookings", tags=["Buchungen"])


@router.get("", summary="Buchungen listen")
def list_bookings(
    ctx: Context,
    _key: ApiKey,
    project_id: uuid.UUID | None = None,
    work_package_id: uuid.UUID | None = None,
    employee_id: uuid.UUID | None = None,
    cost_type_id: uuid.UUID | None = None,
    booking_status: Annotated[BookingStatus | None, Query(alias="status")] = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page[BookingRead]:
    """Listet Buchungen mit Paging und Filtern."""
    return service.list_bookings(
        ctx,
        project_id=project_id,
        work_package_id=work_package_id,
        employee_id=employee_id,
        cost_type_id=cost_type_id,
        status=booking_status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


@router.post("", status_code=status.HTTP_201_CREATED, summary="Buchung anlegen")
def create_booking(ctx: Context, _key: ApiKey, data: BookingCreate) -> BookingRead:
    """Legt eine Buchung an; jede neue Buchung beginnt im Status `draft`."""
    return service.create_booking(ctx, data)


@router.get("/kinds", summary="Buchungsarten und ihre Detailfelder")
def list_kinds(_key: ApiKey) -> dict[str, str]:
    """Liefert die registrierten Buchungsarten mit dem Namen ihres Detail-Schemas."""
    return registered_kinds()


@router.get("/{booking_id}", summary="Buchung lesen")
def get_booking(ctx: Context, _key: ApiKey, booking_id: uuid.UUID) -> BookingRead:
    """Liest eine Buchung samt geltendem Preis und Betrag."""
    return service.get_booking(ctx, booking_id)


@router.patch("/{booking_id}", summary="Buchung ändern")
def update_booking(
    ctx: Context,
    _key: ApiKey,
    booking_id: uuid.UUID,
    data: BookingUpdate,
    expected_version: int | None = None,
) -> BookingRead:
    """Ändert eine Buchung; `locked` und `cancelled` sind unveränderbar."""
    return service.update_booking(ctx, booking_id, data, expected_version)


@router.post("/{booking_id}/confirm", summary="Buchung bestätigen")
def confirm_booking(
    ctx: Context, _key: ApiKey, booking_id: uuid.UUID, expected_version: int | None = None
) -> BookingRead:
    """Bestätigt eine Buchung; nur ein menschlicher Akteur darf das."""
    return service.confirm_booking(ctx, booking_id, expected_version)


@router.post("/{booking_id}/cancel", summary="Buchung stornieren")
def cancel_booking(
    ctx: Context, _key: ApiKey, booking_id: uuid.UUID, expected_version: int | None = None
) -> BookingRead:
    """Storniert eine Buchung."""
    return service.cancel_booking(ctx, booking_id, expected_version)


@router.delete("/{booking_id}", summary="Buchung löschen (Soft Delete)")
def delete_booking(
    ctx: Context, _key: ApiKey, booking_id: uuid.UUID, expected_version: int | None = None
) -> BookingRead:
    """Markiert eine Buchung als gelöscht."""
    return service.delete_booking(ctx, booking_id, expected_version)
