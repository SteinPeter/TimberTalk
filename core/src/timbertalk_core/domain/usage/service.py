"""Geschäftslogik für Modellpreise und KI-Verbrauch."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from timbertalk_core.clock import utc_now
from timbertalk_core.context import ServiceContext
from timbertalk_core.domain.enums import UsageGrouping, UsageModule, UsagePeriod
from timbertalk_core.domain.usage.models import LlmUsage, ModelPrice
from timbertalk_core.domain.usage.repository import LlmUsageRepository, ModelPriceRepository
from timbertalk_core.domain.usage.schemas import (
    ModelPriceCreate,
    ModelPriceRead,
    UsageRead,
    UsageRecord,
    UsageSummary,
    UsageSummaryRow,
)
from timbertalk_core.errors import Conflict, NotFound
from timbertalk_core.operations import operation
from timbertalk_core.schemas import Page
from timbertalk_core.service_support import build_page, check_version, ensure_unique, require_found

MODEL_PRICE_DE = "Modellpreis"
USAGE_DE = "KI-Verbrauch"

TOKENS_PER_MILLION = Decimal(1_000_000)
"""Modellpreise gelten je Million Token."""

COST_SCALE = Decimal("0.000001")
"""Kosten werden auf sechs Nachkommastellen gerundet, damit Bruchteile nicht verloren gehen."""


def compute_cost(price: ModelPrice, input_tokens: int, output_tokens: int) -> Decimal:
    """Berechnet die Kosten eines Aufrufs aus Tokenzahlen und Modellpreis.

    Parameter:
        price: der gültige Modellpreis je Million Token.
        input_tokens: Anzahl der Eingabe-Token.
        output_tokens: Anzahl der Ausgabe-Token.
    """
    eingabe = Decimal(input_tokens) * price.input_per_mtok / TOKENS_PER_MILLION
    ausgabe = Decimal(output_tokens) * price.output_per_mtok / TOKENS_PER_MILLION
    return (eingabe + ausgabe).quantize(COST_SCALE, rounding=ROUND_HALF_UP)


# --------------------------------------------------------------------------- Modellpreise


@operation(name="model_price.create", read_only=False, summary_de="Legt einen Modellpreis an.")
def create_model_price(ctx: ServiceContext, data: ModelPriceCreate) -> ModelPriceRead:
    """Legt den Preis eines Sprachmodells je Million Token an.

    Parameter:
        data: Anbieter, Modell, Preise für Eingabe und Ausgabe und Gültigkeitsbeginn.
    """
    repository = ModelPriceRepository(ctx.session)
    ensure_unique(
        repository,
        ModelPrice.provider == data.provider,
        ModelPrice.model == data.model,
        ModelPrice.valid_from == data.valid_from,
        message=(
            f"Für '{data.provider}/{data.model}' gibt es ab {data.valid_from.isoformat()} "
            "bereits einen Preis."
        ),
        provider=data.provider,
        model=data.model,
    )
    price = repository.add(ModelPrice(**data.model_dump()))
    ctx.session.flush()
    return ModelPriceRead.model_validate(price)


@operation(name="model_price.list", read_only=True, summary_de="Listet Modellpreise.")
def list_model_prices(
    ctx: ServiceContext,
    provider: str | None = None,
    model: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[ModelPriceRead]:
    """Listet Modellpreise mit Paging.

    Parameter:
        provider: Anbieter des Modells.
        model: Modellkennung.
        limit: maximale Anzahl Datensätze (höchstens 200).
        offset: Anzahl übersprungener Datensätze.
    """
    filters = []
    if provider is not None:
        filters.append(ModelPrice.provider == provider)
    if model is not None:
        filters.append(ModelPrice.model == model)
    return build_page(
        ModelPriceRepository(ctx.session),
        ModelPriceRead,
        filters=filters,
        order_by=[ModelPrice.provider, ModelPrice.model, ModelPrice.valid_from.desc()],
        limit=limit,
        offset=offset,
    )


@operation(
    name="model_price.get_for_date",
    read_only=True,
    summary_de="Liest den an einem Tag gültigen Modellpreis.",
)
def get_model_price_for_date(
    ctx: ServiceContext, provider: str, model: str, on_date: date | None = None
) -> ModelPriceRead:
    """Liefert den Modellpreis, der an einem Tag gilt.

    Parameter:
        provider: Anbieter des Modells.
        model: Modellkennung.
        on_date: Stichtag; ohne Angabe der heutige Tag.
    """
    stichtag = on_date or utc_now().date()
    price = ModelPriceRepository(ctx.session).valid_on(provider, model, stichtag)
    if price is None:
        raise NotFound(
            f"Für '{provider}/{model}' ist am {stichtag.isoformat()} kein Preis hinterlegt.",
            provider=provider,
            model=model,
            on_date=stichtag.isoformat(),
        )
    return ModelPriceRead.model_validate(price)


@operation(name="model_price.delete", read_only=False, summary_de="Löscht einen Modellpreis (Soft Delete).")
def delete_model_price(
    ctx: ServiceContext, model_price_id: uuid.UUID, expected_version: int | None = None
) -> ModelPriceRead:
    """Markiert einen Modellpreis als gelöscht.

    Parameter:
        model_price_id: Kennung des Modellpreises.
        expected_version: erwartete Version für optimistisches Sperren.
    """
    repository = ModelPriceRepository(ctx.session)
    price = require_found(repository.get(model_price_id), MODEL_PRICE_DE, model_price_id)
    check_version(price, expected_version, MODEL_PRICE_DE)
    repository.soft_delete(price)
    ctx.session.flush()
    return ModelPriceRead.model_validate(price)


# --------------------------------------------------------------------------- Verbrauch


@operation(name="usage.record", read_only=False, summary_de="Protokolliert einen KI-Aufruf.")
def record_usage(ctx: ServiceContext, data: UsageRecord) -> UsageRead:
    """Protokolliert einen KI-Aufruf und berechnet die Kosten aus den Modellpreisen.

    Parameter:
        data: Anbieter, Modell, Modul, Funktion, Tokenzahlen und optionale Zuordnung
            zu Akteur, Projekt und Anfrage-Kennung.
    """
    zeitpunkt = data.occurred_at or utc_now()
    price = ModelPriceRepository(ctx.session).valid_on(data.provider, data.model, zeitpunkt.date())
    if price is None:
        raise NotFound(
            f"Für '{data.provider}/{data.model}' ist am {zeitpunkt.date().isoformat()} "
            "kein Preis hinterlegt; der Verbrauch kann nicht bewertet werden.",
            provider=data.provider,
            model=data.model,
        )

    usage = LlmUsageRepository(ctx.session).add(
        LlmUsage(
            occurred_at=zeitpunkt,
            provider=data.provider,
            model=data.model,
            module=data.module.value,
            feature=data.feature,
            actor_id=data.actor_id or ctx.actor_id,
            project_id=data.project_id,
            input_tokens=data.input_tokens,
            output_tokens=data.output_tokens,
            cost=compute_cost(price, data.input_tokens, data.output_tokens),
            currency=price.currency,
            request_id=data.request_id,
            success=data.success,
            model_price_id=price.id,
        )
    )
    ctx.session.flush()
    return UsageRead.model_validate(usage)


@operation(name="usage.list", read_only=True, summary_de="Listet protokollierte KI-Aufrufe.")
def list_usage(
    ctx: ServiceContext,
    module: UsageModule | None = None,
    model: str | None = None,
    project_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[UsageRead]:
    """Listet protokollierte KI-Aufrufe mit Paging.

    Parameter:
        module: Modul `a` oder `b`.
        model: Modellkennung.
        project_id: Kennung des Projekts.
        limit: maximale Anzahl Datensätze (höchstens 200).
        offset: Anzahl übersprungener Datensätze.
    """
    filters = []
    if module is not None:
        filters.append(LlmUsage.module == module.value)
    if model is not None:
        filters.append(LlmUsage.model == model)
    if project_id is not None:
        filters.append(LlmUsage.project_id == project_id)
    return build_page(
        LlmUsageRepository(ctx.session),
        UsageRead,
        filters=filters,
        order_by=[LlmUsage.occurred_at.desc()],
        limit=limit,
        offset=offset,
    )


def _period_key(moment: datetime, period: UsagePeriod) -> str:
    """Bildet den Schlüssel eines Zeitraums, z. B. `2026-05` bei Monatsraster."""
    lokal = moment.astimezone(UTC)
    match period:
        case UsagePeriod.DAY:
            return lokal.date().isoformat()
        case UsagePeriod.MONTH:
            return f"{lokal.year:04d}-{lokal.month:02d}"
        case UsagePeriod.YEAR:
            return f"{lokal.year:04d}"


def _group_key(usage: LlmUsage, group_by: UsageGrouping) -> str:
    """Bildet den Gruppenschlüssel einer Zeile der Übersicht."""
    match group_by:
        case UsageGrouping.MODEL:
            return usage.model
        case UsageGrouping.PROVIDER:
            return usage.provider
        case UsageGrouping.MODULE:
            return usage.module
        case UsageGrouping.FEATURE:
            return usage.feature
        case UsageGrouping.PROJECT:
            return str(usage.project_id) if usage.project_id else "ohne Projekt"
        case UsageGrouping.ACTOR:
            return str(usage.actor_id) if usage.actor_id else "ohne Akteur"


@operation(name="usage.summary", read_only=True, summary_de="Fasst den KI-Verbrauch zusammen.")
def usage_summary(
    ctx: ServiceContext,
    period: UsagePeriod = UsagePeriod.MONTH,
    group_by: UsageGrouping = UsageGrouping.MODEL,
    date_from: date | None = None,
    date_to: date | None = None,
) -> UsageSummary:
    """Fasst den KI-Verbrauch je Zeitraum und Gruppe zusammen (Kostenübersicht).

    Parameter:
        period: Zeitraster (`day`, `month`, `year`).
        group_by: Gruppierung (`model`, `provider`, `module`, `feature`, `project`, `actor`).
        date_from: erster berücksichtigter Tag; ohne Angabe ab dem ersten Eintrag.
        date_to: letzter berücksichtigter Tag; ohne Angabe bis heute.
    """
    beginn = (
        datetime.combine(date_from, datetime.min.time(), tzinfo=UTC)
        if date_from
        else datetime(1970, 1, 1, tzinfo=UTC)
    )
    ende = (
        datetime.combine(date_to + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
        if date_to
        else utc_now() + timedelta(days=1)
    )

    eintraege = LlmUsageRepository(ctx.session).in_period(beginn, ende)
    gruppen: dict[tuple[str, str], UsageSummaryRow] = {}
    waehrungen: dict[str, Decimal] = defaultdict(Decimal)

    for usage in eintraege:
        schluessel = (_period_key(usage.occurred_at, period), _group_key(usage, group_by))
        zeile = gruppen.get(schluessel)
        if zeile is None:
            zeile = UsageSummaryRow(
                period=schluessel[0],
                group=schluessel[1],
                calls=0,
                input_tokens=0,
                output_tokens=0,
                cost=Decimal("0"),
                currency=usage.currency,
            )
            gruppen[schluessel] = zeile
        zeile.calls += 1
        zeile.input_tokens += usage.input_tokens
        zeile.output_tokens += usage.output_tokens
        zeile.cost += usage.cost
        waehrungen[usage.currency] += usage.cost

    if len(waehrungen) > 1:
        raise Conflict(
            "Der Verbrauch enthält mehrere Währungen; eine gemeinsame Summe ist nicht möglich.",
            currencies=sorted(waehrungen),
        )

    waehrung = next(iter(waehrungen), "EUR")
    zeilen = [gruppen[key] for key in sorted(gruppen)]
    return UsageSummary(
        period=period,
        group_by=group_by,
        rows=zeilen,
        total_cost=sum((zeile.cost for zeile in zeilen), Decimal("0")),
        currency=waehrung,
    )
