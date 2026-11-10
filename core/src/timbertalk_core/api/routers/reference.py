"""Router für Referenzdaten. Dünner Adapter: Eingabe prüfen, Service rufen, Ergebnis geben."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from timbertalk_core.api.deps import ApiKey, Context
from timbertalk_core.domain.reference import service
from timbertalk_core.domain.reference.schemas import (
    CostTypeCreate,
    CostTypeRead,
    CostTypeUpdate,
    CustomFieldDefinitionCreate,
    CustomFieldDefinitionRead,
    CustomFieldDefinitionUpdate,
    UnitCreate,
    UnitRead,
    UnitUpdate,
)
from timbertalk_core.schemas import Page

units_router = APIRouter(prefix="/units", tags=["Einheiten"])
cost_types_router = APIRouter(prefix="/cost-types", tags=["Kostenarten"])
custom_fields_router = APIRouter(prefix="/custom-fields", tags=["Zusatzfelder"])


@units_router.get("", summary="Einheiten listen")
def list_units(
    ctx: Context,
    _key: ApiKey,
    active_only: bool = True,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page[UnitRead]:
    """Listet Einheiten mit Paging."""
    return service.list_units(ctx, active_only=active_only, limit=limit, offset=offset)


@units_router.post("", status_code=status.HTTP_201_CREATED, summary="Einheit anlegen")
def create_unit(ctx: Context, _key: ApiKey, data: UnitCreate) -> UnitRead:
    """Legt eine Einheit an."""
    return service.create_unit(ctx, data)


@units_router.get("/by-code/{code}", summary="Einheit über ihren Code lesen")
def get_unit_by_code(ctx: Context, _key: ApiKey, code: str) -> UnitRead:
    """Liest eine Einheit anhand ihres Kurzzeichens."""
    return service.get_unit_by_code(ctx, code)


@units_router.get("/{unit_id}", summary="Einheit lesen")
def get_unit(ctx: Context, _key: ApiKey, unit_id: uuid.UUID) -> UnitRead:
    """Liest eine Einheit."""
    return service.get_unit(ctx, unit_id)


@units_router.patch("/{unit_id}", summary="Einheit ändern")
def update_unit(
    ctx: Context,
    _key: ApiKey,
    unit_id: uuid.UUID,
    data: UnitUpdate,
    expected_version: int | None = None,
) -> UnitRead:
    """Ändert eine Einheit."""
    return service.update_unit(ctx, unit_id, data, expected_version)


@units_router.delete("/{unit_id}", summary="Einheit löschen (Soft Delete)")
def delete_unit(
    ctx: Context, _key: ApiKey, unit_id: uuid.UUID, expected_version: int | None = None
) -> UnitRead:
    """Markiert eine Einheit als gelöscht."""
    return service.delete_unit(ctx, unit_id, expected_version)


@cost_types_router.get("", summary="Kostenarten listen")
def list_cost_types(
    ctx: Context,
    _key: ApiKey,
    kind: str | None = None,
    active_only: bool = True,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page[CostTypeRead]:
    """Listet Kostenarten mit Paging."""
    return service.list_cost_types(ctx, kind=kind, active_only=active_only, limit=limit, offset=offset)


@cost_types_router.post("", status_code=status.HTTP_201_CREATED, summary="Kostenart anlegen")
def create_cost_type(ctx: Context, _key: ApiKey, data: CostTypeCreate) -> CostTypeRead:
    """Legt eine Kostenart an; neue Kostenfaktoren brauchen keine Code-Änderung."""
    return service.create_cost_type(ctx, data)


@cost_types_router.get("/by-code/{code}", summary="Kostenart über ihren Code lesen")
def get_cost_type_by_code(ctx: Context, _key: ApiKey, code: str) -> CostTypeRead:
    """Liest eine Kostenart anhand ihres Codes."""
    return service.get_cost_type_by_code(ctx, code)


@cost_types_router.get("/{cost_type_id}", summary="Kostenart lesen")
def get_cost_type(ctx: Context, _key: ApiKey, cost_type_id: uuid.UUID) -> CostTypeRead:
    """Liest eine Kostenart."""
    return service.get_cost_type(ctx, cost_type_id)


@cost_types_router.patch("/{cost_type_id}", summary="Kostenart ändern")
def update_cost_type(
    ctx: Context,
    _key: ApiKey,
    cost_type_id: uuid.UUID,
    data: CostTypeUpdate,
    expected_version: int | None = None,
) -> CostTypeRead:
    """Ändert eine Kostenart."""
    return service.update_cost_type(ctx, cost_type_id, data, expected_version)


@cost_types_router.delete("/{cost_type_id}", summary="Kostenart löschen (Soft Delete)")
def delete_cost_type(
    ctx: Context, _key: ApiKey, cost_type_id: uuid.UUID, expected_version: int | None = None
) -> CostTypeRead:
    """Markiert eine Kostenart als gelöscht."""
    return service.delete_cost_type(ctx, cost_type_id, expected_version)


@custom_fields_router.get("", summary="Zusatzfeld-Definitionen listen")
def list_custom_fields(
    ctx: Context,
    _key: ApiKey,
    entity_type: str | None = None,
    active_only: bool = True,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page[CustomFieldDefinitionRead]:
    """Listet Zusatzfeld-Definitionen mit Paging."""
    return service.list_custom_fields(
        ctx, entity_type=entity_type, active_only=active_only, limit=limit, offset=offset
    )


@custom_fields_router.post("", status_code=status.HTTP_201_CREATED, summary="Zusatzfeld definieren")
def create_custom_field(
    ctx: Context, _key: ApiKey, data: CustomFieldDefinitionCreate
) -> CustomFieldDefinitionRead:
    """Legt eine Zusatzfeld-Definition an; danach ist das Feld in `attributes` erlaubt."""
    return service.create_custom_field(ctx, data)


@custom_fields_router.get("/{definition_id}", summary="Zusatzfeld-Definition lesen")
def get_custom_field(ctx: Context, _key: ApiKey, definition_id: uuid.UUID) -> CustomFieldDefinitionRead:
    """Liest eine Zusatzfeld-Definition."""
    return service.get_custom_field(ctx, definition_id)


@custom_fields_router.patch("/{definition_id}", summary="Zusatzfeld-Definition ändern")
def update_custom_field(
    ctx: Context,
    _key: ApiKey,
    definition_id: uuid.UUID,
    data: CustomFieldDefinitionUpdate,
    expected_version: int | None = None,
) -> CustomFieldDefinitionRead:
    """Ändert eine Zusatzfeld-Definition."""
    return service.update_custom_field(ctx, definition_id, data, expected_version)


@custom_fields_router.delete("/{definition_id}", summary="Zusatzfeld-Definition löschen (Soft Delete)")
def delete_custom_field(
    ctx: Context, _key: ApiKey, definition_id: uuid.UUID, expected_version: int | None = None
) -> CustomFieldDefinitionRead:
    """Markiert eine Zusatzfeld-Definition als gelöscht."""
    return service.delete_custom_field(ctx, definition_id, expected_version)
