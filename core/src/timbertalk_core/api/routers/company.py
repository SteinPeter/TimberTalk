"""Router für Firmendaten, Einstellungen und Steuersätze."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Query, status

from timbertalk_core.api.deps import ApiKey, Context
from timbertalk_core.domain.company import service
from timbertalk_core.domain.company.schemas import (
    CompanyRead,
    CompanyUpsert,
    SettingRead,
    SettingUpsert,
    TaxRateCreate,
    TaxRateRead,
    TaxRateUpdate,
)
from timbertalk_core.schemas import Page

company_router = APIRouter(prefix="/company", tags=["Firmendaten"])
settings_router = APIRouter(prefix="/settings", tags=["Einstellungen"])
tax_rates_router = APIRouter(prefix="/tax-rates", tags=["Steuersätze"])


@company_router.get("", summary="Firmendaten lesen")
def get_company(ctx: Context, _key: ApiKey) -> CompanyRead:
    """Liest die Firmendaten des Betriebs."""
    return service.get_company(ctx)


@company_router.put("", summary="Firmendaten anlegen oder ändern")
def set_company(
    ctx: Context, _key: ApiKey, data: CompanyUpsert, expected_version: int | None = None
) -> CompanyRead:
    """Legt die Firmendaten an oder ändert den vorhandenen Datensatz."""
    return service.set_company(ctx, data, expected_version)


@settings_router.get("", summary="Einstellungen listen")
def list_settings(
    ctx: Context,
    _key: ApiKey,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page[SettingRead]:
    """Listet Einstellungen mit Paging."""
    return service.list_settings(ctx, limit=limit, offset=offset)


@settings_router.put("", summary="Einstellung setzen")
def set_setting(ctx: Context, _key: ApiKey, data: SettingUpsert) -> SettingRead:
    """Setzt eine Einstellung; ein vorhandener Schlüssel wird überschrieben."""
    return service.set_setting(ctx, data)


@settings_router.get("/{key}", summary="Einstellung lesen")
def get_setting(ctx: Context, _key: ApiKey, key: str) -> SettingRead:
    """Liest eine Einstellung anhand ihres Schlüssels."""
    return service.get_setting(ctx, key)


@settings_router.delete("/{key}", summary="Einstellung löschen (Soft Delete)")
def delete_setting(ctx: Context, _key: ApiKey, key: str) -> SettingRead:
    """Markiert eine Einstellung als gelöscht."""
    return service.delete_setting(ctx, key)


@tax_rates_router.get("", summary="Steuersätze listen")
def list_tax_rates(
    ctx: Context,
    _key: ApiKey,
    code: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page[TaxRateRead]:
    """Listet Steuersätze mit Paging."""
    return service.list_tax_rates(ctx, code=code, limit=limit, offset=offset)


@tax_rates_router.post("", status_code=status.HTTP_201_CREATED, summary="Steuersatz anlegen")
def create_tax_rate(ctx: Context, _key: ApiKey, data: TaxRateCreate) -> TaxRateRead:
    """Legt einen Steuersatz mit Gültigkeitszeitraum an."""
    return service.create_tax_rate(ctx, data)


@tax_rates_router.get("/for-date", summary="Am Stichtag gültigen Steuersatz lesen")
def get_tax_rate_for_date(ctx: Context, _key: ApiKey, code: str, on_date: date | None = None) -> TaxRateRead:
    """Liefert den Steuersatz, der an einem Tag gültig ist."""
    return service.get_tax_rate_for_date(ctx, code, on_date)


@tax_rates_router.get("/{tax_rate_id}", summary="Steuersatz lesen")
def get_tax_rate(ctx: Context, _key: ApiKey, tax_rate_id: uuid.UUID) -> TaxRateRead:
    """Liest einen Steuersatz."""
    return service.get_tax_rate(ctx, tax_rate_id)


@tax_rates_router.patch("/{tax_rate_id}", summary="Steuersatz ändern")
def update_tax_rate(
    ctx: Context,
    _key: ApiKey,
    tax_rate_id: uuid.UUID,
    data: TaxRateUpdate,
    expected_version: int | None = None,
) -> TaxRateRead:
    """Ändert einen Steuersatz."""
    return service.update_tax_rate(ctx, tax_rate_id, data, expected_version)


@tax_rates_router.delete("/{tax_rate_id}", summary="Steuersatz löschen (Soft Delete)")
def delete_tax_rate(
    ctx: Context, _key: ApiKey, tax_rate_id: uuid.UUID, expected_version: int | None = None
) -> TaxRateRead:
    """Markiert einen Steuersatz als gelöscht."""
    return service.delete_tax_rate(ctx, tax_rate_id, expected_version)
