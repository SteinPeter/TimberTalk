"""Prüft Firmendaten, Einstellungen und Steuersätze."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from timbertalk_core.context import ServiceContext
from timbertalk_core.domain.company.schemas import (
    CompanyUpsert,
    SettingUpsert,
    TaxRateCreate,
    TaxRateUpdate,
)
from timbertalk_core.domain.company.service import (
    create_tax_rate,
    delete_setting,
    get_company,
    get_setting,
    get_tax_rate_for_date,
    list_settings,
    list_tax_rates,
    set_company,
    set_setting,
    update_tax_rate,
)
from timbertalk_core.errors import Conflict, NotFound, ValidationFailed


def test_firmendaten_anlegen_und_aendern(ctx: ServiceContext) -> None:
    with pytest.raises(NotFound, match="keine Firmendaten"):
        get_company(ctx)

    company = set_company(
        ctx,
        CompanyUpsert(
            name="Zimmerei Muster GmbH",
            street="Holzweg 7",
            zip="10115",
            city="Berlin",
            home_lat=Decimal("52.530000"),
            home_lon=Decimal("13.380000"),
        ),
    )
    ctx.session.commit()
    assert company.city == "Berlin"
    assert company.country == "DE"
    assert company.home_lat == Decimal("52.530000")

    geaendert = set_company(
        ctx,
        CompanyUpsert(name="Zimmerei Muster GmbH", city="Potsdam"),
        expected_version=1,
    )
    ctx.session.commit()
    assert geaendert.id == company.id, "Es darf nur einen Firmendatensatz geben"
    assert geaendert.city == "Potsdam"
    assert geaendert.version == 2
    assert get_company(ctx).city == "Potsdam"


def test_firmendaten_versionskonflikt(ctx: ServiceContext) -> None:
    set_company(ctx, CompanyUpsert(name="Betrieb"))
    ctx.session.commit()
    with pytest.raises(Conflict, match="zwischenzeitlich geändert"):
        set_company(ctx, CompanyUpsert(name="Betrieb neu"), expected_version=99)


def test_einstellungen_setzen_lesen_loeschen(ctx: ServiceContext) -> None:
    set_setting(
        ctx,
        SettingUpsert(
            key="default_hourly_rate",
            value={"amount": "68.50", "currency": "EUR"},
            label_de="Standard-Stundensatz",
        ),
    )
    ctx.session.commit()
    assert get_setting(ctx, "default_hourly_rate").value["amount"] == "68.50"

    set_setting(ctx, SettingUpsert(key="default_hourly_rate", value={"amount": "72.00"}))
    ctx.session.commit()
    assert get_setting(ctx, "default_hourly_rate").value == {"amount": "72.00"}
    assert list_settings(ctx).total == 1

    delete_setting(ctx, "default_hourly_rate")
    ctx.session.commit()
    with pytest.raises(NotFound, match="nicht hinterlegt"):
        get_setting(ctx, "default_hourly_rate")


def test_steuersatz_gueltigkeit(ctx: ServiceContext) -> None:
    create_tax_rate(
        ctx,
        TaxRateCreate(
            code="19",
            percent=Decimal("16"),
            label_de="Umsatzsteuer 16 %",
            valid_from=date(2020, 7, 1),
            valid_to=date(2020, 12, 31),
        ),
    )
    create_tax_rate(
        ctx,
        TaxRateCreate(
            code="19",
            percent=Decimal("19"),
            label_de="Umsatzsteuer 19 %",
            valid_from=date(2021, 1, 1),
        ),
    )
    ctx.session.commit()

    assert get_tax_rate_for_date(ctx, "19", date(2020, 9, 1)).percent == Decimal("16")
    assert get_tax_rate_for_date(ctx, "19", date(2020, 12, 31)).percent == Decimal("16")
    assert get_tax_rate_for_date(ctx, "19", date(2021, 1, 1)).percent == Decimal("19")
    assert get_tax_rate_for_date(ctx, "19", date(2026, 11, 10)).percent == Decimal("19")
    assert list_tax_rates(ctx, code="19").total == 2

    with pytest.raises(NotFound, match="kein Wert gültig"):
        get_tax_rate_for_date(ctx, "19", date(2019, 1, 1))


def test_ueberlappende_steuersaetze_werden_abgelehnt(ctx: ServiceContext) -> None:
    create_tax_rate(
        ctx,
        TaxRateCreate(
            code="7", percent=Decimal("7"), label_de="Umsatzsteuer 7 %", valid_from=date(2021, 1, 1)
        ),
    )
    ctx.session.commit()
    with pytest.raises(Conflict, match="überlappenden"):
        create_tax_rate(
            ctx,
            TaxRateCreate(
                code="7",
                percent=Decimal("7.5"),
                label_de="Überlappend",
                valid_from=date(2024, 1, 1),
            ),
        )
    # Ein anderer Code darf denselben Zeitraum haben.
    create_tax_rate(
        ctx,
        TaxRateCreate(code="0", percent=Decimal("0"), label_de="Steuerfrei", valid_from=date(2021, 1, 1)),
    )
    ctx.session.commit()
    assert list_tax_rates(ctx).total == 2


def test_ende_vor_beginn_wird_abgelehnt(ctx: ServiceContext) -> None:
    with pytest.raises(ValidationFailed, match="nicht vor dem Beginn"):
        create_tax_rate(
            ctx,
            TaxRateCreate(
                code="19",
                percent=Decimal("19"),
                label_de="Falsch",
                valid_from=date(2026, 1, 1),
                valid_to=date(2025, 12, 31),
            ),
        )


def test_steuersatz_aendern(ctx: ServiceContext) -> None:
    tax_rate = create_tax_rate(
        ctx,
        TaxRateCreate(code="19", percent=Decimal("19"), label_de="Umsatzsteuer", valid_from=date(2021, 1, 1)),
    )
    ctx.session.commit()
    geaendert = update_tax_rate(
        ctx, tax_rate.id, TaxRateUpdate(valid_to=date(2026, 12, 31)), expected_version=1
    )
    ctx.session.commit()
    assert geaendert.valid_to == date(2026, 12, 31)
    assert get_tax_rate_for_date(ctx, "19", date(2026, 12, 31)).id == tax_rate.id
    with pytest.raises(NotFound, match="kein Wert gültig"):
        get_tax_rate_for_date(ctx, "19", date(2027, 1, 1))
