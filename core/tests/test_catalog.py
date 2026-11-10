"""Prüft Materialkatalog und Preisermittlung."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest

from timbertalk_core.context import ServiceContext
from timbertalk_core.domain.catalog.schemas import (
    MaterialItemCreate,
    MaterialItemUpdate,
    PriceCreate,
    PriceUpdate,
)
from timbertalk_core.domain.catalog.service import (
    create_material_item,
    create_price,
    delete_material_item,
    delete_price,
    get_price,
    list_material_items,
    list_prices,
    update_material_item,
    update_price,
)
from timbertalk_core.domain.enums import (
    CostTypeKind,
    MaterialCategory,
    PriceSource,
    PriceTargetType,
)
from timbertalk_core.domain.reference.schemas import CostTypeCreate, UnitCreate
from timbertalk_core.domain.reference.service import create_cost_type, create_unit
from timbertalk_core.errors import Conflict, NotFound, ValidationFailed


@pytest.fixture
def stammdaten(ctx: ServiceContext) -> dict[str, uuid.UUID]:
    """Legt Einheiten und Kostenarten an und liefert deren Kennungen."""
    create_unit(ctx, UnitCreate(code="m3", label_de="Kubikmeter", decimals=3))
    create_unit(ctx, UnitCreate(code="stk", label_de="Stück", decimals=0))
    create_unit(ctx, UnitCreate(code="h", label_de="Stunde", decimals=2))
    holz = create_cost_type(
        ctx,
        CostTypeCreate(
            code="material_timber",
            name_de="Holz",
            kind=CostTypeKind.MATERIAL,
            default_unit_code="m3",
        ),
    )
    lohn = create_cost_type(
        ctx,
        CostTypeCreate(
            code="labor_master",
            name_de="Lohn Meister",
            kind=CostTypeKind.LABOR,
            default_unit_code="h",
            default_unit_price=Decimal("68.5000"),
            labor_share=True,
        ),
    )
    ctx.session.commit()
    return {"holz": holz.id, "lohn": lohn.id}


def _artikel(ctx: ServiceContext, name: str = "KVH Fichte C24 60×200") -> uuid.UUID:
    item = create_material_item(
        ctx,
        MaterialItemCreate(
            name=name,
            category=MaterialCategory.TIMBER,
            unit_code="m3",
            cost_type_code="material_timber",
            wood_species="Fichte",
            grade="C24",
            width_mm=60,
            height_mm=200,
            length_mm=5000,
        ),
    )
    ctx.session.commit()
    return item.id


def test_artikel_anlegen(ctx: ServiceContext, stammdaten: dict[str, uuid.UUID]) -> None:
    item_id = _artikel(ctx)
    items = list_material_items(ctx)
    assert items.total == 1
    item = items.items[0]
    assert item.id == item_id
    assert item.category is MaterialCategory.TIMBER
    assert (item.width_mm, item.height_mm, item.length_mm) == (60, 200, 5000)


def test_artikel_braucht_bekannte_einheit_und_kostenart(ctx: ServiceContext) -> None:
    with pytest.raises(NotFound, match="Einheit"):
        create_material_item(
            ctx,
            MaterialItemCreate(
                name="Ohne Einheit",
                category=MaterialCategory.OTHER,
                unit_code="xyz",
                cost_type_code="material_timber",
            ),
        )


def test_doppelte_artikelnummer_wird_abgelehnt(ctx: ServiceContext, stammdaten: dict[str, uuid.UUID]) -> None:
    vorlage = MaterialItemCreate(
        name="Dachlatte 30×50",
        sku="DL-3050",
        category=MaterialCategory.TIMBER,
        unit_code="stk",
        cost_type_code="material_timber",
    )
    create_material_item(ctx, vorlage)
    ctx.session.commit()
    with pytest.raises(Conflict, match="Artikelnummer"):
        create_material_item(ctx, vorlage)


def test_artikel_suchen_und_filtern(ctx: ServiceContext, stammdaten: dict[str, uuid.UUID]) -> None:
    _artikel(ctx, "KVH Fichte C24 60×200")
    create_material_item(
        ctx,
        MaterialItemCreate(
            name="Vollgewindeschraube 8×240",
            sku="VGS-8240",
            category=MaterialCategory.FASTENERS,
            unit_code="stk",
            cost_type_code="material_timber",
        ),
    )
    ctx.session.commit()

    assert list_material_items(ctx, search="kvh").total == 1
    assert list_material_items(ctx, search="vgs").total == 1
    assert list_material_items(ctx, category="fasteners").total == 1
    assert list_material_items(ctx).total == 2


def test_artikel_aendern_und_loeschen(ctx: ServiceContext, stammdaten: dict[str, uuid.UUID]) -> None:
    item_id = _artikel(ctx)
    geaendert = update_material_item(
        ctx, item_id, MaterialItemUpdate(grade="GL24h", name="BSH GL24h 100×280"), expected_version=1
    )
    ctx.session.commit()
    assert geaendert.grade == "GL24h"

    delete_material_item(ctx, item_id)
    ctx.session.commit()
    assert list_material_items(ctx).total == 0


# --------------------------------------------------------------------------- Preise


def test_preis_je_datum(ctx: ServiceContext, stammdaten: dict[str, uuid.UUID]) -> None:
    item_id = _artikel(ctx)
    create_price(
        ctx,
        PriceCreate(
            target_type=PriceTargetType.MATERIAL_ITEM,
            target_id=item_id,
            unit_price=Decimal("489.5000"),
            valid_from=date(2026, 1, 1),
            valid_to=date(2026, 6, 30),
            note="Platzhalterpreis",
        ),
    )
    create_price(
        ctx,
        PriceCreate(
            target_type=PriceTargetType.MATERIAL_ITEM,
            target_id=item_id,
            unit_price=Decimal("512.0000"),
            valid_from=date(2026, 7, 1),
            source=PriceSource.SUPPLIER,
            note="Platzhalterpreis",
        ),
    )
    ctx.session.commit()

    # Ränder der Gültigkeit
    assert get_price(ctx, PriceTargetType.MATERIAL_ITEM, item_id, date(2026, 1, 1)).unit_price == (
        Decimal("489.5000")
    )
    assert get_price(ctx, PriceTargetType.MATERIAL_ITEM, item_id, date(2026, 6, 30)).unit_price == (
        Decimal("489.5000")
    )
    assert get_price(ctx, PriceTargetType.MATERIAL_ITEM, item_id, date(2026, 7, 1)).unit_price == (
        Decimal("512.0000")
    )
    # Offenes Ende gilt weiter
    ermittelt = get_price(ctx, PriceTargetType.MATERIAL_ITEM, item_id, date(2030, 1, 1))
    assert ermittelt.unit_price == Decimal("512.0000")
    assert ermittelt.origin == "price_material_item"
    assert ermittelt.currency == "EUR"

    with pytest.raises(NotFound, match="kein Preis hinterlegt"):
        get_price(ctx, PriceTargetType.MATERIAL_ITEM, item_id, date(2025, 12, 31))


def test_ueberlappende_preise_werden_abgelehnt(ctx: ServiceContext, stammdaten: dict[str, uuid.UUID]) -> None:
    item_id = _artikel(ctx)
    create_price(
        ctx,
        PriceCreate(
            target_type=PriceTargetType.MATERIAL_ITEM,
            target_id=item_id,
            unit_price=Decimal("489.50"),
            valid_from=date(2026, 1, 1),
        ),
    )
    ctx.session.commit()

    with pytest.raises(Conflict, match="überlappender Gültigkeit"):
        create_price(
            ctx,
            PriceCreate(
                target_type=PriceTargetType.MATERIAL_ITEM,
                target_id=item_id,
                unit_price=Decimal("512.00"),
                valid_from=date(2026, 7, 1),
            ),
        )

    # Lückenlos anschließend ist erlaubt, wenn der erste Preis begrenzt wird.
    vorhandener = list_prices(ctx, target_id=item_id).items[0]
    update_price(ctx, vorhandener.id, PriceUpdate(valid_to=date(2026, 6, 30)))
    ctx.session.commit()
    create_price(
        ctx,
        PriceCreate(
            target_type=PriceTargetType.MATERIAL_ITEM,
            target_id=item_id,
            unit_price=Decimal("512.00"),
            valid_from=date(2026, 7, 1),
        ),
    )
    ctx.session.commit()
    assert list_prices(ctx, target_id=item_id).total == 2


def test_tagesgleiche_ueberlappung_wird_erkannt(
    ctx: ServiceContext, stammdaten: dict[str, uuid.UUID]
) -> None:
    item_id = _artikel(ctx)
    create_price(
        ctx,
        PriceCreate(
            target_type=PriceTargetType.MATERIAL_ITEM,
            target_id=item_id,
            unit_price=Decimal("100.00"),
            valid_from=date(2026, 1, 1),
            valid_to=date(2026, 6, 30),
        ),
    )
    ctx.session.commit()
    with pytest.raises(Conflict):
        create_price(
            ctx,
            PriceCreate(
                target_type=PriceTargetType.MATERIAL_ITEM,
                target_id=item_id,
                unit_price=Decimal("110.00"),
                valid_from=date(2026, 6, 30),
                valid_to=date(2026, 12, 31),
            ),
        )


def test_ende_vor_beginn_wird_abgelehnt(ctx: ServiceContext, stammdaten: dict[str, uuid.UUID]) -> None:
    item_id = _artikel(ctx)
    with pytest.raises(ValueError, match="nicht vor dem Beginn"):
        PriceCreate(
            target_type=PriceTargetType.MATERIAL_ITEM,
            target_id=item_id,
            unit_price=Decimal("1.00"),
            valid_from=date(2026, 7, 1),
            valid_to=date(2026, 1, 1),
        )

    create_price(
        ctx,
        PriceCreate(
            target_type=PriceTargetType.MATERIAL_ITEM,
            target_id=item_id,
            unit_price=Decimal("1.00"),
            valid_from=date(2026, 7, 1),
        ),
    )
    ctx.session.commit()
    preis = list_prices(ctx, target_id=item_id).items[0]
    with pytest.raises(ValidationFailed, match="nicht vor dem Beginn"):
        update_price(ctx, preis.id, PriceUpdate(valid_to=date(2026, 1, 1)))


def test_preis_vorrang_kostenart_vor_vorgabe(ctx: ServiceContext, stammdaten: dict[str, uuid.UUID]) -> None:
    """Artikel ohne eigenen Preis greift auf die Kostenart zurück, dann auf den Vorgabepreis."""
    item_id = _artikel(ctx)
    # Kein Preis irgendwo: die Kostenart 'Holz' hat auch keinen Vorgabepreis.
    with pytest.raises(NotFound, match="kein Preis hinterlegt"):
        get_price(ctx, PriceTargetType.MATERIAL_ITEM, item_id, date(2026, 5, 1))

    create_price(
        ctx,
        PriceCreate(
            target_type=PriceTargetType.COST_TYPE,
            target_id=stammdaten["holz"],
            unit_price=Decimal("450.0000"),
            valid_from=date(2026, 1, 1),
        ),
    )
    ctx.session.commit()
    ueber_kostenart = get_price(ctx, PriceTargetType.MATERIAL_ITEM, item_id, date(2026, 5, 1))
    assert ueber_kostenart.unit_price == Decimal("450.0000")
    assert ueber_kostenart.origin == "price_cost_type"

    # Ein eigener Artikelpreis hat Vorrang.
    create_price(
        ctx,
        PriceCreate(
            target_type=PriceTargetType.MATERIAL_ITEM,
            target_id=item_id,
            unit_price=Decimal("489.5000"),
            valid_from=date(2026, 1, 1),
        ),
    )
    ctx.session.commit()
    direkt = get_price(ctx, PriceTargetType.MATERIAL_ITEM, item_id, date(2026, 5, 1))
    assert direkt.unit_price == Decimal("489.5000")
    assert direkt.origin == "price_material_item"


def test_vorgabepreis_der_kostenart_greift(ctx: ServiceContext, stammdaten: dict[str, uuid.UUID]) -> None:
    ermittelt = get_price(ctx, PriceTargetType.COST_TYPE, stammdaten["lohn"], date(2026, 5, 1))
    assert ermittelt.unit_price == Decimal("68.5000")
    assert ermittelt.origin == "cost_type_default"
    assert ermittelt.price_id is None


def test_preis_zu_unbekanntem_ziel(ctx: ServiceContext) -> None:
    with pytest.raises(NotFound):
        create_price(
            ctx,
            PriceCreate(
                target_type=PriceTargetType.MATERIAL_ITEM,
                target_id=uuid.uuid4(),
                unit_price=Decimal("1.00"),
                valid_from=date(2026, 1, 1),
            ),
        )


def test_preis_loeschen(ctx: ServiceContext, stammdaten: dict[str, uuid.UUID]) -> None:
    item_id = _artikel(ctx)
    preis = create_price(
        ctx,
        PriceCreate(
            target_type=PriceTargetType.MATERIAL_ITEM,
            target_id=item_id,
            unit_price=Decimal("489.50"),
            valid_from=date(2026, 1, 1),
        ),
    )
    ctx.session.commit()
    delete_price(ctx, preis.id, expected_version=1)
    ctx.session.commit()
    assert list_prices(ctx, target_id=item_id).total == 0
    # Nach dem Löschen ist der Zeitraum wieder frei.
    create_price(
        ctx,
        PriceCreate(
            target_type=PriceTargetType.MATERIAL_ITEM,
            target_id=item_id,
            unit_price=Decimal("500.00"),
            valid_from=date(2026, 1, 1),
        ),
    )
    ctx.session.commit()
    assert list_prices(ctx, target_id=item_id).total == 1
