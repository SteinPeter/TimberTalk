"""Router für Modellpreise und KI-Verbrauch."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Query, status

from timbertalk_core.api.deps import ApiKey, Context
from timbertalk_core.domain.enums import UsageGrouping, UsageModule, UsagePeriod
from timbertalk_core.domain.usage import service
from timbertalk_core.domain.usage.schemas import (
    ModelPriceCreate,
    ModelPriceRead,
    UsageRead,
    UsageRecord,
    UsageSummary,
)
from timbertalk_core.schemas import Page

model_prices_router = APIRouter(prefix="/model-prices", tags=["Modellpreise"])
usage_router = APIRouter(prefix="/usage", tags=["KI-Verbrauch"])


@model_prices_router.get("", summary="Modellpreise listen")
def list_model_prices(
    ctx: Context,
    _key: ApiKey,
    provider: str | None = None,
    model: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page[ModelPriceRead]:
    """Listet Modellpreise mit Paging."""
    return service.list_model_prices(ctx, provider=provider, model=model, limit=limit, offset=offset)


@model_prices_router.post("", status_code=status.HTTP_201_CREATED, summary="Modellpreis anlegen")
def create_model_price(ctx: Context, _key: ApiKey, data: ModelPriceCreate) -> ModelPriceRead:
    """Legt den Preis eines Sprachmodells je Million Token an."""
    return service.create_model_price(ctx, data)


@model_prices_router.get("/for-date", summary="Am Stichtag gültigen Modellpreis lesen")
def get_model_price_for_date(
    ctx: Context, _key: ApiKey, provider: str, model: str, on_date: date | None = None
) -> ModelPriceRead:
    """Liefert den Modellpreis, der an einem Tag gilt."""
    return service.get_model_price_for_date(ctx, provider, model, on_date)


@model_prices_router.delete("/{model_price_id}", summary="Modellpreis löschen (Soft Delete)")
def delete_model_price(
    ctx: Context, _key: ApiKey, model_price_id: uuid.UUID, expected_version: int | None = None
) -> ModelPriceRead:
    """Markiert einen Modellpreis als gelöscht."""
    return service.delete_model_price(ctx, model_price_id, expected_version)


@usage_router.get("", summary="KI-Aufrufe listen")
def list_usage(
    ctx: Context,
    _key: ApiKey,
    module: UsageModule | None = None,
    model: str | None = None,
    project_id: uuid.UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page[UsageRead]:
    """Listet protokollierte KI-Aufrufe mit Paging."""
    return service.list_usage(
        ctx, module=module, model=model, project_id=project_id, limit=limit, offset=offset
    )


@usage_router.post("", status_code=status.HTTP_201_CREATED, summary="KI-Aufruf protokollieren")
def record_usage(ctx: Context, _key: ApiKey, data: UsageRecord) -> UsageRead:
    """Protokolliert einen KI-Aufruf und berechnet die Kosten aus den Modellpreisen."""
    return service.record_usage(ctx, data)


@usage_router.get("/summary", summary="Verbrauchsübersicht")
def usage_summary(
    ctx: Context,
    _key: ApiKey,
    period: UsagePeriod = UsagePeriod.MONTH,
    group_by: UsageGrouping = UsageGrouping.MODEL,
    date_from: date | None = None,
    date_to: date | None = None,
) -> UsageSummary:
    """Fasst den KI-Verbrauch je Zeitraum und Gruppe zusammen."""
    return service.usage_summary(ctx, period=period, group_by=group_by, date_from=date_from, date_to=date_to)
