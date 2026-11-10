"""Router für Kunden."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from timbertalk_core.api.deps import ApiKey, Context
from timbertalk_core.domain.customers import service
from timbertalk_core.domain.customers.schemas import CustomerCreate, CustomerRead, CustomerUpdate
from timbertalk_core.schemas import Page

router = APIRouter(prefix="/customers", tags=["Kunden"])


@router.get("", summary="Kunden listen")
def list_customers(
    ctx: Context,
    _key: ApiKey,
    search: str | None = None,
    customer_type: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page[CustomerRead]:
    """Listet Kunden mit Paging, optional gefiltert und durchsucht."""
    return service.list_customers(ctx, search=search, customer_type=customer_type, limit=limit, offset=offset)


@router.post("", status_code=status.HTTP_201_CREATED, summary="Kunden anlegen")
def create_customer(ctx: Context, _key: ApiKey, data: CustomerCreate) -> CustomerRead:
    """Legt einen Kunden an."""
    return service.create_customer(ctx, data)


@router.get("/{customer_id}", summary="Kunden lesen")
def get_customer(ctx: Context, _key: ApiKey, customer_id: uuid.UUID) -> CustomerRead:
    """Liest einen Kunden."""
    return service.get_customer(ctx, customer_id)


@router.patch("/{customer_id}", summary="Kunden ändern")
def update_customer(
    ctx: Context,
    _key: ApiKey,
    customer_id: uuid.UUID,
    data: CustomerUpdate,
    expected_version: int | None = None,
) -> CustomerRead:
    """Ändert einen Kunden."""
    return service.update_customer(ctx, customer_id, data, expected_version)


@router.delete("/{customer_id}", summary="Kunden löschen (Soft Delete)")
def delete_customer(
    ctx: Context, _key: ApiKey, customer_id: uuid.UUID, expected_version: int | None = None
) -> CustomerRead:
    """Markiert einen Kunden als gelöscht."""
    return service.delete_customer(ctx, customer_id, expected_version)
