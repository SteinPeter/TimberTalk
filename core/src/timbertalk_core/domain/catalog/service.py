"""Geschäftslogik für Materialkatalog und Preisermittlung."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import func, or_

from timbertalk_core.clock import today
from timbertalk_core.context import ServiceContext
from timbertalk_core.domain.catalog.models import MaterialItem, Price
from timbertalk_core.domain.catalog.repository import MaterialItemRepository, PriceRepository
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
from timbertalk_core.domain.reference.custom_fields import validate_attributes
from timbertalk_core.domain.reference.models import CostType, Unit
from timbertalk_core.domain.reference.repository import CostTypeRepository, UnitRepository
from timbertalk_core.errors import Conflict, NotFound, ValidationFailed
from timbertalk_core.operations import operation
from timbertalk_core.schemas import Page
from timbertalk_core.service_support import (
    apply_updates,
    build_page,
    check_version,
    ensure_unique,
    require_found,
    resolve_by_code,
)

MATERIAL_DE = "Artikel"
PRICE_DE = "Preis"


# --------------------------------------------------------------------------- Materialkatalog


@operation(name="material_item.create", read_only=False, summary_de="Legt einen Artikel an.")
def create_material_item(ctx: ServiceContext, data: MaterialItemCreate) -> MaterialItemRead:
    """Legt einen Artikel im Materialkatalog an.

    Parameter:
        data: Name, Kategorie, Einheit, Kostenart und optionale Maße in Millimetern.
    """
    repository = MaterialItemRepository(ctx.session)
    resolve_by_code(UnitRepository(ctx.session), Unit.code, data.unit_code, "Einheit")
    resolve_by_code(CostTypeRepository(ctx.session), CostType.code, data.cost_type_code, "Kostenart")
    if data.sku:
        ensure_unique(
            repository,
            MaterialItem.sku == data.sku,
            message=f"Ein Artikel mit der Artikelnummer '{data.sku}' existiert bereits.",
            sku=data.sku,
        )
    values = data.model_dump()
    values["attributes"] = validate_attributes(ctx, MaterialItem.__tablename__, values["attributes"])
    item = repository.add(MaterialItem(**values))
    ctx.flush()
    return MaterialItemRead.model_validate(item)


@operation(name="material_item.get", read_only=True, summary_de="Liest einen Artikel.")
def get_material_item(ctx: ServiceContext, material_item_id: uuid.UUID) -> MaterialItemRead:
    """Liest einen Artikel anhand seiner Kennung.

    Parameter:
        material_item_id: Kennung des Artikels.
    """
    item = require_found(
        MaterialItemRepository(ctx.session).get(material_item_id), MATERIAL_DE, material_item_id
    )
    return MaterialItemRead.model_validate(item)


@operation(name="material_item.list", read_only=True, summary_de="Listet Artikel.")
def list_material_items(
    ctx: ServiceContext,
    search: str | None = None,
    category: str | None = None,
    active_only: bool = True,
    limit: int = 50,
    offset: int = 0,
) -> Page[MaterialItemRead]:
    """Listet Artikel des Materialkatalogs mit Paging.

    Parameter:
        search: Suchtext für Bezeichnung oder Artikelnummer.
        category: Kategorie (`timber`, `fasteners`, `insulation`, `membrane`, `other`).
        active_only: wenn wahr, werden nur aktive Artikel geliefert.
        limit: maximale Anzahl Datensätze (höchstens 200).
        offset: Anzahl übersprungener Datensätze.
    """
    filters = []
    if category is not None:
        filters.append(MaterialItem.category == category)
    if active_only:
        filters.append(MaterialItem.active.is_(True))
    if search:
        muster = f"%{search.lower()}%"
        filters.append(
            or_(
                func.lower(MaterialItem.name).like(muster),
                func.lower(MaterialItem.sku).like(muster),
            )
        )
    return build_page(
        MaterialItemRepository(ctx.session),
        MaterialItemRead,
        filters=filters,
        order_by=[MaterialItem.name],
        limit=limit,
        offset=offset,
    )


@operation(name="material_item.update", read_only=False, summary_de="Ändert einen Artikel.")
def update_material_item(
    ctx: ServiceContext,
    material_item_id: uuid.UUID,
    data: MaterialItemUpdate,
    expected_version: int | None = None,
) -> MaterialItemRead:
    """Ändert einen Artikel; nur übergebene Felder werden geändert.

    Parameter:
        material_item_id: Kennung des Artikels.
        data: zu ändernde Felder.
        expected_version: erwartete Version für optimistisches Sperren.
    """
    repository = MaterialItemRepository(ctx.session)
    item = require_found(repository.get(material_item_id), MATERIAL_DE, material_item_id)
    check_version(item, expected_version, MATERIAL_DE)
    if data.unit_code is not None:
        resolve_by_code(UnitRepository(ctx.session), Unit.code, data.unit_code, "Einheit")
    if data.cost_type_code is not None:
        resolve_by_code(CostTypeRepository(ctx.session), CostType.code, data.cost_type_code, "Kostenart")
    if data.sku is not None and data.sku != item.sku:
        ensure_unique(
            repository,
            MaterialItem.sku == data.sku,
            message=f"Ein Artikel mit der Artikelnummer '{data.sku}' existiert bereits.",
            sku=data.sku,
        )
    changes = apply_updates(item, data, skip=["attributes"])
    if "attributes" in changes:
        item.attributes = validate_attributes(ctx, MaterialItem.__tablename__, changes["attributes"])
    ctx.flush()
    return MaterialItemRead.model_validate(item)


@operation(name="material_item.delete", read_only=False, summary_de="Löscht einen Artikel (Soft Delete).")
def delete_material_item(
    ctx: ServiceContext, material_item_id: uuid.UUID, expected_version: int | None = None
) -> MaterialItemRead:
    """Markiert einen Artikel als gelöscht; Buchungen bleiben erhalten.

    Parameter:
        material_item_id: Kennung des Artikels.
        expected_version: erwartete Version für optimistisches Sperren.
    """
    repository = MaterialItemRepository(ctx.session)
    item = require_found(repository.get(material_item_id), MATERIAL_DE, material_item_id)
    check_version(item, expected_version, MATERIAL_DE)
    repository.soft_delete(item)
    ctx.flush()
    return MaterialItemRead.model_validate(item)


# --------------------------------------------------------------------------- Preise


def _require_target(ctx: ServiceContext, target_type: PriceTargetType, target_id: uuid.UUID) -> None:
    """Stellt sicher, dass das Ziel eines Preises existiert."""
    if target_type is PriceTargetType.MATERIAL_ITEM:
        require_found(MaterialItemRepository(ctx.session).get(target_id), MATERIAL_DE, target_id)
    else:
        require_found(CostTypeRepository(ctx.session).get(target_id), "Kostenart", target_id)


def _check_overlap(
    repository: PriceRepository,
    target_type: str,
    target_id: uuid.UUID,
    valid_from: date,
    valid_to: date | None,
    exclude_id: uuid.UUID | None = None,
) -> None:
    """Weist überlappende Gültigkeitszeiträume für dasselbe Ziel ab."""
    for existing in repository.for_target(target_type, target_id):
        if exclude_id is not None and existing.id == exclude_id:
            continue
        other_end = existing.valid_to
        overlaps = (other_end is None or other_end >= valid_from) and (
            valid_to is None or existing.valid_from <= valid_to
        )
        if overlaps:
            raise Conflict(
                "Für dieses Ziel gibt es bereits einen Preis mit überlappender Gültigkeit "
                f"(ab {existing.valid_from.isoformat()}).",
                target_type=target_type,
                target_id=str(target_id),
                conflicting_id=str(existing.id),
            )


@operation(name="price.create", read_only=False, summary_de="Legt einen Preis an.")
def create_price(ctx: ServiceContext, data: PriceCreate) -> PriceRead:
    """Legt einen Preis mit Gültigkeitszeitraum an; Überlappungen werden abgewiesen.

    Parameter:
        data: Ziel (Artikel oder Kostenart), Preis je Einheit und Gültigkeitszeitraum.
    """
    repository = PriceRepository(ctx.session)
    _require_target(ctx, data.target_type, data.target_id)
    _check_overlap(repository, data.target_type.value, data.target_id, data.valid_from, data.valid_to)
    price = repository.add(Price(**data.model_dump()))
    ctx.flush()
    return PriceRead.model_validate(price)


@operation(name="price.get", read_only=True, summary_de="Liest einen Preis-Datensatz.")
def get_price_record(ctx: ServiceContext, price_id: uuid.UUID) -> PriceRead:
    """Liest einen Preis-Datensatz anhand seiner Kennung.

    Parameter:
        price_id: Kennung des Preis-Datensatzes.
    """
    price = require_found(PriceRepository(ctx.session).get(price_id), PRICE_DE, price_id)
    return PriceRead.model_validate(price)


@operation(name="price.list", read_only=True, summary_de="Listet Preise eines Ziels.")
def list_prices(
    ctx: ServiceContext,
    target_type: str | None = None,
    target_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[PriceRead]:
    """Listet Preise mit Paging, optional für ein bestimmtes Ziel.

    Parameter:
        target_type: `material_item` oder `cost_type`.
        target_id: Kennung des Ziels.
        limit: maximale Anzahl Datensätze (höchstens 200).
        offset: Anzahl übersprungener Datensätze.
    """
    filters = []
    if target_type is not None:
        filters.append(Price.target_type == target_type)
    if target_id is not None:
        filters.append(Price.target_id == target_id)
    return build_page(
        PriceRepository(ctx.session),
        PriceRead,
        filters=filters,
        order_by=[Price.target_type, Price.valid_from],
        limit=limit,
        offset=offset,
    )


@operation(name="price.update", read_only=False, summary_de="Ändert einen Preis.")
def update_price(
    ctx: ServiceContext,
    price_id: uuid.UUID,
    data: PriceUpdate,
    expected_version: int | None = None,
) -> PriceRead:
    """Ändert einen Preis; Überlappungen werden abgewiesen.

    Parameter:
        price_id: Kennung des Preis-Datensatzes.
        data: zu ändernde Felder.
        expected_version: erwartete Version für optimistisches Sperren.
    """
    repository = PriceRepository(ctx.session)
    price = require_found(repository.get(price_id), PRICE_DE, price_id)
    check_version(price, expected_version, PRICE_DE)
    changes = data.model_dump(exclude_unset=True)
    neuer_beginn = changes.get("valid_from", price.valid_from)
    neues_ende = changes.get("valid_to", price.valid_to)
    if neues_ende is not None and neues_ende < neuer_beginn:
        raise ValidationFailed(
            "Das Ende der Gültigkeit darf nicht vor dem Beginn liegen.",
            errors={"valid_to": "muss nach valid_from liegen"},
        )
    if "valid_from" in changes or "valid_to" in changes:
        _check_overlap(
            repository,
            price.target_type,
            price.target_id,
            neuer_beginn,
            neues_ende,
            exclude_id=price.id,
        )
    apply_updates(price, data)
    ctx.flush()
    return PriceRead.model_validate(price)


@operation(name="price.delete", read_only=False, summary_de="Löscht einen Preis (Soft Delete).")
def delete_price(ctx: ServiceContext, price_id: uuid.UUID, expected_version: int | None = None) -> PriceRead:
    """Markiert einen Preis als gelöscht.

    Parameter:
        price_id: Kennung des Preis-Datensatzes.
        expected_version: erwartete Version für optimistisches Sperren.
    """
    repository = PriceRepository(ctx.session)
    price = require_found(repository.get(price_id), PRICE_DE, price_id)
    check_version(price, expected_version, PRICE_DE)
    repository.soft_delete(price)
    ctx.flush()
    return PriceRead.model_validate(price)


def find_valid_price(
    ctx: ServiceContext,
    target_type: PriceTargetType,
    target_id: uuid.UUID,
    on_date: date,
) -> Price | None:
    """Sucht den an einem Tag gültigen Preis-Datensatz eines Ziels.

    Parameter:
        ctx: Aufrufkontext mit offener Session.
        target_type: `material_item` oder `cost_type`.
        target_id: Kennung des Ziels.
        on_date: Stichtag.
    """
    for price in PriceRepository(ctx.session).for_target(target_type.value, target_id):
        if price.valid_from <= on_date and (price.valid_to is None or price.valid_to >= on_date):
            return price
    return None


@operation(
    name="price.resolve",
    read_only=True,
    summary_de="Ermittelt den an einem Tag gültigen Preis.",
)
def get_price(
    ctx: ServiceContext,
    target_type: PriceTargetType,
    target_id: uuid.UUID,
    on_date: date | None = None,
) -> ResolvedPrice:
    """Ermittelt den gültigen Preis eines Artikels oder einer Kostenart an einem Tag.

    Vorrang: ein gültiger Preis-Datensatz des Ziels; bei einem Artikel danach ein
    gültiger Preis seiner Kostenart; zuletzt der Vorgabepreis der Kostenart.

    Parameter:
        target_type: `material_item` oder `cost_type`.
        target_id: Kennung des Artikels bzw. der Kostenart.
        on_date: Stichtag; ohne Angabe gilt der heutige Tag.
    """
    stichtag = on_date or today()
    _require_target(ctx, target_type, target_id)

    direkt = find_valid_price(ctx, target_type, target_id, stichtag)
    if direkt is not None:
        herkunft = (
            "price_material_item" if target_type is PriceTargetType.MATERIAL_ITEM else "price_cost_type"
        )
        return ResolvedPrice(
            unit_price=direkt.unit_price,
            currency=direkt.currency,
            origin=herkunft,
            price_id=direkt.id,
            on_date=stichtag,
        )

    cost_type: CostType | None = None
    if target_type is PriceTargetType.MATERIAL_ITEM:
        item = require_found(MaterialItemRepository(ctx.session).get(target_id), MATERIAL_DE, target_id)
        cost_type = resolve_by_code(
            CostTypeRepository(ctx.session), CostType.code, item.cost_type_code, "Kostenart"
        )
        ueber_kostenart = find_valid_price(ctx, PriceTargetType.COST_TYPE, cost_type.id, stichtag)
        if ueber_kostenart is not None:
            return ResolvedPrice(
                unit_price=ueber_kostenart.unit_price,
                currency=ueber_kostenart.currency,
                origin="price_cost_type",
                price_id=ueber_kostenart.id,
                on_date=stichtag,
            )
    else:
        cost_type = require_found(CostTypeRepository(ctx.session).get(target_id), "Kostenart", target_id)

    if cost_type.default_unit_price is not None:
        return ResolvedPrice(
            unit_price=cost_type.default_unit_price,
            currency="EUR",
            origin="cost_type_default",
            price_id=None,
            on_date=stichtag,
        )

    raise NotFound(
        f"Für dieses Ziel ist am {stichtag.isoformat()} kein Preis hinterlegt.",
        target_type=target_type.value,
        target_id=str(target_id),
        on_date=stichtag.isoformat(),
    )
