"""Router für Mitarbeiter."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from timbertalk_core.api.deps import ApiKey, Context
from timbertalk_core.domain.people import service
from timbertalk_core.domain.people.schemas import EmployeeCreate, EmployeeRead, EmployeeUpdate
from timbertalk_core.schemas import Page

router = APIRouter(prefix="/employees", tags=["Mitarbeiter"])


@router.get("", summary="Mitarbeiter listen")
def list_employees(
    ctx: Context,
    _key: ApiKey,
    role: str | None = None,
    active_only: bool = True,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page[EmployeeRead]:
    """Listet Mitarbeiter mit Paging."""
    return service.list_employees(ctx, role=role, active_only=active_only, limit=limit, offset=offset)


@router.post("", status_code=status.HTTP_201_CREATED, summary="Mitarbeiter anlegen")
def create_employee(ctx: Context, _key: ApiKey, data: EmployeeCreate) -> EmployeeRead:
    """Legt einen Mitarbeiter an."""
    return service.create_employee(ctx, data)


@router.get("/{employee_id}", summary="Mitarbeiter lesen")
def get_employee(ctx: Context, _key: ApiKey, employee_id: uuid.UUID) -> EmployeeRead:
    """Liest einen Mitarbeiter."""
    return service.get_employee(ctx, employee_id)


@router.patch("/{employee_id}", summary="Mitarbeiter ändern")
def update_employee(
    ctx: Context,
    _key: ApiKey,
    employee_id: uuid.UUID,
    data: EmployeeUpdate,
    expected_version: int | None = None,
) -> EmployeeRead:
    """Ändert einen Mitarbeiter."""
    return service.update_employee(ctx, employee_id, data, expected_version)


@router.delete("/{employee_id}", summary="Mitarbeiter löschen (Soft Delete)")
def delete_employee(
    ctx: Context, _key: ApiKey, employee_id: uuid.UUID, expected_version: int | None = None
) -> EmployeeRead:
    """Markiert einen Mitarbeiter als gelöscht."""
    return service.delete_employee(ctx, employee_id, expected_version)
