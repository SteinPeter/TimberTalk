"""Prüft Modellpreise, Kostenberechnung und Verbrauchsübersicht."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from timbertalk_core.context import ServiceContext
from timbertalk_core.domain.enums import UsageGrouping, UsageModule, UsagePeriod
from timbertalk_core.domain.usage.schemas import ModelPriceCreate, UsageRecord
from timbertalk_core.domain.usage.service import (
    create_model_price,
    get_model_price_for_date,
    list_model_prices,
    list_usage,
    record_usage,
    usage_summary,
)
from timbertalk_core.errors import Conflict, NotFound


@pytest.fixture
def preise(ctx: ServiceContext) -> None:
    """Legt Modellpreise für zwei Modelle an."""
    create_model_price(
        ctx,
        ModelPriceCreate(
            provider="anthropic",
            model="claude-opus-5",
            input_per_mtok=Decimal("12.0000"),
            output_per_mtok=Decimal("60.0000"),
            valid_from=date(2026, 1, 1),
            note="Platzhalterpreis",
        ),
    )
    create_model_price(
        ctx,
        ModelPriceCreate(
            provider="anthropic",
            model="claude-haiku-5-5",
            input_per_mtok=Decimal("0.8000"),
            output_per_mtok=Decimal("4.0000"),
            valid_from=date(2026, 1, 1),
            note="Platzhalterpreis",
        ),
    )
    ctx.session.commit()


def test_modellpreis_anlegen_und_lesen(ctx: ServiceContext, preise: None) -> None:
    assert list_model_prices(ctx).total == 2
    preis = get_model_price_for_date(ctx, "anthropic", "claude-opus-5", date(2026, 5, 1))
    assert preis.input_per_mtok == Decimal("12.0000")
    assert preis.currency == "EUR"

    with pytest.raises(NotFound, match="kein Preis hinterlegt"):
        get_model_price_for_date(ctx, "anthropic", "claude-opus-5", date(2025, 12, 31))


def test_doppelter_modellpreis_wird_abgelehnt(ctx: ServiceContext, preise: None) -> None:
    with pytest.raises(Conflict, match="bereits einen Preis"):
        create_model_price(
            ctx,
            ModelPriceCreate(
                provider="anthropic",
                model="claude-opus-5",
                input_per_mtok=Decimal("13.0000"),
                output_per_mtok=Decimal("65.0000"),
                valid_from=date(2026, 1, 1),
            ),
        )


def test_juengerer_preis_gilt(ctx: ServiceContext, preise: None) -> None:
    create_model_price(
        ctx,
        ModelPriceCreate(
            provider="anthropic",
            model="claude-opus-5",
            input_per_mtok=Decimal("10.0000"),
            output_per_mtok=Decimal("50.0000"),
            valid_from=date(2026, 7, 1),
        ),
    )
    ctx.session.commit()
    assert get_model_price_for_date(
        ctx, "anthropic", "claude-opus-5", date(2026, 6, 30)
    ).input_per_mtok == Decimal("12.0000")
    assert get_model_price_for_date(
        ctx, "anthropic", "claude-opus-5", date(2026, 7, 1)
    ).input_per_mtok == Decimal("10.0000")


def test_kosten_werden_aus_tokenzahlen_berechnet(ctx: ServiceContext, preise: None) -> None:
    """12 € je Mio. Eingabe und 60 € je Mio. Ausgabe: 1500 + 800 Token."""
    usage = record_usage(
        ctx,
        UsageRecord(
            provider="anthropic",
            model="claude-opus-5",
            module=UsageModule.A,
            feature="voice_booking",
            input_tokens=1500,
            output_tokens=800,
            occurred_at=datetime(2026, 5, 4, 10, 0, tzinfo=UTC),
            request_id="req-1",
        ),
    )
    ctx.session.commit()
    # 1500/1e6*12 = 0.018 ; 800/1e6*60 = 0.048 ; Summe 0.066
    assert usage.cost == Decimal("0.066000")
    assert usage.currency == "EUR"
    assert usage.actor_id == ctx.actor_id
    assert usage.model_price_id is not None
    assert usage.success is True


def test_kleinstbetraege_gehen_nicht_verloren(ctx: ServiceContext, preise: None) -> None:
    usage = record_usage(
        ctx,
        UsageRecord(
            provider="anthropic",
            model="claude-haiku-5-5",
            module=UsageModule.A,
            feature="klassifikation",
            input_tokens=10,
            output_tokens=1,
            occurred_at=datetime(2026, 5, 4, 10, 0, tzinfo=UTC),
        ),
    )
    ctx.session.commit()
    # 10/1e6*0.8 = 0.000008 ; 1/1e6*4 = 0.000004 ; Summe 0.000012
    assert usage.cost == Decimal("0.000012")


def test_null_token_kostet_nichts(ctx: ServiceContext, preise: None) -> None:
    usage = record_usage(
        ctx,
        UsageRecord(
            provider="anthropic",
            model="claude-opus-5",
            module=UsageModule.B,
            feature="cad_hinweis",
            success=False,
            occurred_at=datetime(2026, 5, 4, 10, 0, tzinfo=UTC),
        ),
    )
    ctx.session.commit()
    assert usage.cost == Decimal("0")
    assert usage.success is False


def test_verbrauch_ohne_preis_wird_abgelehnt(ctx: ServiceContext) -> None:
    with pytest.raises(NotFound, match="kein Preis hinterlegt"):
        record_usage(
            ctx,
            UsageRecord(
                provider="openai",
                model="unbekannt",
                module=UsageModule.A,
                feature="test",
                input_tokens=100,
            ),
        )


def _verbrauch(ctx: ServiceContext, projekt: uuid.UUID) -> None:
    """Protokolliert Aufrufe in zwei Monaten, zwei Modellen und zwei Modulen."""
    for tag, modell, modul, feature, eingabe, ausgabe in [
        (datetime(2026, 5, 4, 8, 0, tzinfo=UTC), "claude-opus-5", UsageModule.A, "voice", 1000, 500),
        (datetime(2026, 5, 20, 8, 0, tzinfo=UTC), "claude-opus-5", UsageModule.A, "voice", 2000, 1000),
        (
            datetime(2026, 5, 21, 8, 0, tzinfo=UTC),
            "claude-haiku-5-5",
            UsageModule.B,
            "cad",
            5000,
            200,
        ),
        (datetime(2026, 6, 2, 8, 0, tzinfo=UTC), "claude-opus-5", UsageModule.A, "bericht", 500, 100),
    ]:
        record_usage(
            ctx,
            UsageRecord(
                provider="anthropic",
                model=modell,
                module=modul,
                feature=feature,
                input_tokens=eingabe,
                output_tokens=ausgabe,
                project_id=projekt,
                occurred_at=tag,
            ),
        )
    ctx.session.commit()


def test_uebersicht_nach_monat_und_modell(ctx: ServiceContext, preise: None) -> None:
    projekt = uuid.uuid4()
    _verbrauch(ctx, projekt)

    uebersicht = usage_summary(ctx, period=UsagePeriod.MONTH, group_by=UsageGrouping.MODEL)
    zeilen = {(zeile.period, zeile.group): zeile for zeile in uebersicht.rows}
    assert set(zeilen) == {
        ("2026-05", "claude-opus-5"),
        ("2026-05", "claude-haiku-5-5"),
        ("2026-06", "claude-opus-5"),
    }
    mai_opus = zeilen[("2026-05", "claude-opus-5")]
    assert mai_opus.calls == 2
    assert mai_opus.input_tokens == 3000
    assert mai_opus.output_tokens == 1500
    # 3000/1e6*12 + 1500/1e6*60 = 0.036 + 0.09 = 0.126
    assert mai_opus.cost == Decimal("0.126000")
    assert uebersicht.total_cost == sum(zeile.cost for zeile in uebersicht.rows)
    assert uebersicht.currency == "EUR"


def test_uebersicht_nach_modul_tag_und_projekt(ctx: ServiceContext, preise: None) -> None:
    projekt = uuid.uuid4()
    _verbrauch(ctx, projekt)

    nach_modul = usage_summary(ctx, group_by=UsageGrouping.MODULE)
    assert {zeile.group for zeile in nach_modul.rows} == {"a", "b"}

    nach_tag = usage_summary(ctx, period=UsagePeriod.DAY, group_by=UsageGrouping.FEATURE)
    assert ("2026-05-04", "voice") in {(zeile.period, zeile.group) for zeile in nach_tag.rows}

    nach_jahr = usage_summary(ctx, period=UsagePeriod.YEAR, group_by=UsageGrouping.PROJECT)
    assert [(zeile.period, zeile.group) for zeile in nach_jahr.rows] == [("2026", str(projekt))]
    assert nach_jahr.rows[0].calls == 4


def test_uebersicht_mit_zeitraumgrenzen(ctx: ServiceContext, preise: None) -> None:
    projekt = uuid.uuid4()
    _verbrauch(ctx, projekt)

    nur_mai = usage_summary(
        ctx,
        period=UsagePeriod.MONTH,
        group_by=UsageGrouping.MODEL,
        date_from=date(2026, 5, 1),
        date_to=date(2026, 5, 31),
    )
    assert {zeile.period for zeile in nur_mai.rows} == {"2026-05"}

    nur_ein_tag = usage_summary(
        ctx, group_by=UsageGrouping.MODEL, date_from=date(2026, 5, 21), date_to=date(2026, 5, 21)
    )
    assert sum(zeile.calls for zeile in nur_ein_tag.rows) == 1

    leer = usage_summary(ctx, date_from=date(2027, 1, 1), date_to=date(2027, 12, 31))
    assert leer.rows == []
    assert leer.total_cost == Decimal("0")


def test_verbrauch_filtern(ctx: ServiceContext, preise: None) -> None:
    projekt = uuid.uuid4()
    _verbrauch(ctx, projekt)
    assert list_usage(ctx).total == 4
    assert list_usage(ctx, module=UsageModule.B).total == 1
    assert list_usage(ctx, model="claude-opus-5").total == 3
    assert list_usage(ctx, project_id=projekt).total == 4
    assert list_usage(ctx, project_id=uuid.uuid4()).total == 0
