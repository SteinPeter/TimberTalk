"""Router für Materialkatalog und Preise."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Query, status

from timbertalk_core.api.deps import ApiKey, Context
from timbertalk_core.domain.catalog import service
from timbertalk_core.domain.catalog.schemas import (
    MaterialItemCreate,
    MaterialItemRead,
    MaterialItemUpdate,
    PriceCreate,
    PriceRead,
    PriceUpdate,
    ResolvedPrice,
)
from timbertalk_core.domain.enums import PriceTargetType
from timbertalk_core.schemas import Page

material_items_router = APIRouter(prefix="/material-items", tags=["Materialkatalog"])
prices_router = APIRouter(prefix="/prices", tags=["Preise"])


@material_items_router.get("", summary="Artikel listen")
def list_material_items(
    ctx: Context,
    _key: ApiKey,
    search: str | None = None,
    category: str | None = None,
    active_only: bool = True,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page[MaterialItemRead]:
    """Listet Artikel des Materialkatalogs mit Paging."""
    return service.list_material_items(
        ctx,
        search=search,
        category=category,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )


@material_items_router.post("", status_code=status.HTTP_201_CREATED, summary="Artikel anlegen")
def create_material_item(ctx: Context, _key: ApiKey, data: MaterialItemCreate) -> MaterialItemRead:
    """Legt einen Artikel im Materialkatalog an."""
    return service.create_material_item(ctx, data)


@material_items_router.get("/{material_item_id}", summary="Artikel lesen")
def get_material_item(ctx: Context, _key: ApiKey, material_item_id: uuid.UUID) -> MaterialItemRead:
    """Liest einen Artikel."""
    return service.get_material_item(ctx, material_item_id)


@material_items_router.patch("/{material_item_id}", summary="Artikel ändern")
def update_material_item(
    ctx: Context,
    _key: ApiKey,
    material_item_id: uuid.UUID,
    data: MaterialItemUpdate,
    expected_version: int | None = None,
) -> MaterialItemRead:
    """Ändert einen Artikel."""
    return service.update_material_item(ctx, material_item_id, data, expected_version)


@material_items_router.delete("/{material_item_id}", summary="Artikel löschen (Soft Delete)")
def delete_material_item(
    ctx: Context, _key: ApiKey, material_item_id: uuid.UUID, expected_version: int | None = None
) -> MaterialItemRead:
    """Markiert einen Artikel als gelöscht."""
    return service.delete_material_item(ctx, material_item_id, expected_version)


@prices_router.get("", summary="Preise listen")
def list_prices(
    ctx: Context,
    _key: ApiKey,
    target_type: str | None = None,
    target_id: uuid.UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page[PriceRead]:
    """Listet Preise mit Paging."""
    return service.list_prices(ctx, target_type=target_type, target_id=target_id, limit=limit, offset=offset)


@prices_router.post("", status_code=status.HTTP_201_CREATED, summary="Preis anlegen")
def create_price(ctx: Context, _key: ApiKey, data: PriceCreate) -> PriceRead:
    """Legt einen Preis mit Gültigkeitszeitraum an."""
    return service.create_price(ctx, data)


@prices_router.get("/resolve", summary="Am Stichtag gültigen Preis ermitteln")
def resolve_price(
    ctx: Context,
    _key: ApiKey,
    target_type: PriceTargetType,
    target_id: uuid.UUID,
    on_date: date | None = None,
) -> ResolvedPrice:
    """Ermittelt den gültigen Preis eines Artikels oder einer Kostenart."""
    return service.get_price(ctx, target_type, target_id, on_date)


@prices_router.get("/{price_id}", summary="Preis lesen")
def get_price_record(ctx: Context, _key: ApiKey, price_id: uuid.UUID) -> PriceRead:
    """Liest einen Preis-Datensatz."""
    return service.get_price_record(ctx, price_id)


@prices_router.patch("/{price_id}", summary="Preis ändern")
def update_price(
    ctx: Context,
    _key: ApiKey,
    price_id: uuid.UUID,
    data: PriceUpdate,
    expected_version: int | None = None,
) -> PriceRead:
    """Ändert einen Preis."""
    return service.update_price(ctx, price_id, data, expected_version)


@prices_router.delete("/{price_id}", summary="Preis löschen (Soft Delete)")
def delete_price(
    ctx: Context, _key: ApiKey, price_id: uuid.UUID, expected_version: int | None = None
) -> PriceRead:
    """Markiert einen Preis als gelöscht."""
    return service.delete_price(ctx, price_id, expected_version)
