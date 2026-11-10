"""Geschäftslogik der Referenzdaten: Einheiten, Kostenarten, Zusatzfeld-Definitionen."""

from __future__ import annotations

import uuid

from timbertalk_core.context import ServiceContext
from timbertalk_core.domain.enums import CustomFieldDataType
from timbertalk_core.domain.reference.custom_fields import validate_attributes
from timbertalk_core.domain.reference.models import CostType, CustomFieldDefinition, Unit
from timbertalk_core.domain.reference.repository import (
    CostTypeRepository,
    CustomFieldDefinitionRepository,
    UnitRepository,
)
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
from timbertalk_core.errors import ValidationFailed
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

UNIT_DE = "Einheit"
COST_TYPE_DE = "Kostenart"
CUSTOM_FIELD_DE = "Zusatzfeld-Definition"


# --------------------------------------------------------------------------- Einheiten


@operation(name="unit.create", read_only=False, summary_de="Legt eine Einheit an.")
def create_unit(ctx: ServiceContext, data: UnitCreate) -> UnitRead:
    """Legt eine neue Einheit an.

    Parameter:
        data: Kurzzeichen, Anzeigename und Anzeige-Genauigkeit (Nachkommastellen).
    """
    repository = UnitRepository(ctx.session)
    ensure_unique(
        repository,
        Unit.code == data.code,
        message=f"Eine Einheit mit dem Code '{data.code}' existiert bereits.",
        code=data.code,
    )
    unit = repository.add(Unit(**data.model_dump()))
    ctx.session.flush()
    return UnitRead.model_validate(unit)


@operation(name="unit.get", read_only=True, summary_de="Liest eine Einheit.")
def get_unit(ctx: ServiceContext, unit_id: uuid.UUID) -> UnitRead:
    """Liest eine Einheit anhand ihrer Kennung.

    Parameter:
        unit_id: Kennung der Einheit.
    """
    unit = require_found(UnitRepository(ctx.session).get(unit_id), UNIT_DE, unit_id)
    return UnitRead.model_validate(unit)


@operation(name="unit.get_by_code", read_only=True, summary_de="Liest eine Einheit über ihren Code.")
def get_unit_by_code(ctx: ServiceContext, code: str) -> UnitRead:
    """Liest eine Einheit anhand ihres Kurzzeichens.

    Parameter:
        code: Kurzzeichen der Einheit, z. B. `h` oder `m3`.
    """
    unit = resolve_by_code(UnitRepository(ctx.session), Unit.code, code, UNIT_DE)
    return UnitRead.model_validate(unit)


@operation(name="unit.list", read_only=True, summary_de="Listet Einheiten.")
def list_units(
    ctx: ServiceContext,
    active_only: bool = True,
    limit: int = 50,
    offset: int = 0,
) -> Page[UnitRead]:
    """Listet Einheiten mit Paging.

    Parameter:
        active_only: wenn wahr, werden nur aktive Einheiten geliefert.
        limit: maximale Anzahl Datensätze (höchstens 200).
        offset: Anzahl übersprungener Datensätze.
    """
    filters = [Unit.active.is_(True)] if active_only else []
    return build_page(
        UnitRepository(ctx.session),
        UnitRead,
        filters=filters,
        order_by=[Unit.sort_order, Unit.code],
        limit=limit,
        offset=offset,
    )


@operation(name="unit.update", read_only=False, summary_de="Ändert eine Einheit.")
def update_unit(
    ctx: ServiceContext,
    unit_id: uuid.UUID,
    data: UnitUpdate,
    expected_version: int | None = None,
) -> UnitRead:
    """Ändert eine Einheit; nur übergebene Felder werden geändert.

    Parameter:
        unit_id: Kennung der Einheit.
        data: zu ändernde Felder.
        expected_version: erwartete Version für optimistisches Sperren.
    """
    repository = UnitRepository(ctx.session)
    unit = require_found(repository.get(unit_id), UNIT_DE, unit_id)
    check_version(unit, expected_version, UNIT_DE)
    apply_updates(unit, data)
    ctx.session.flush()
    return UnitRead.model_validate(unit)


@operation(name="unit.delete", read_only=False, summary_de="Löscht eine Einheit (Soft Delete).")
def delete_unit(ctx: ServiceContext, unit_id: uuid.UUID, expected_version: int | None = None) -> UnitRead:
    """Markiert eine Einheit als gelöscht; der Code wird danach wieder frei.

    Parameter:
        unit_id: Kennung der Einheit.
        expected_version: erwartete Version für optimistisches Sperren.
    """
    repository = UnitRepository(ctx.session)
    unit = require_found(repository.get(unit_id), UNIT_DE, unit_id)
    check_version(unit, expected_version, UNIT_DE)
    repository.soft_delete(unit)
    ctx.session.flush()
    return UnitRead.model_validate(unit)


# --------------------------------------------------------------------------- Kostenarten


def _require_unit(ctx: ServiceContext, code: str) -> Unit:
    """Stellt sicher, dass die Einheit existiert, und liefert sie."""
    return resolve_by_code(UnitRepository(ctx.session), Unit.code, code, UNIT_DE)


@operation(name="cost_type.create", read_only=False, summary_de="Legt eine Kostenart an.")
def create_cost_type(ctx: ServiceContext, data: CostTypeCreate) -> CostTypeRead:
    """Legt eine neue Kostenart an; neue Kostenfaktoren brauchen keine Code-Änderung.

    Parameter:
        data: Code, Name, Art (`kind`), Vorgabe-Einheit und optionaler Vorgabepreis.
    """
    repository = CostTypeRepository(ctx.session)
    ensure_unique(
        repository,
        CostType.code == data.code,
        message=f"Eine Kostenart mit dem Code '{data.code}' existiert bereits.",
        code=data.code,
    )
    _require_unit(ctx, data.default_unit_code)
    values = data.model_dump()
    values["attributes"] = validate_attributes(ctx, CostType.__tablename__, values["attributes"])
    cost_type = repository.add(CostType(**values))
    ctx.session.flush()
    return CostTypeRead.model_validate(cost_type)


@operation(name="cost_type.get", read_only=True, summary_de="Liest eine Kostenart.")
def get_cost_type(ctx: ServiceContext, cost_type_id: uuid.UUID) -> CostTypeRead:
    """Liest eine Kostenart anhand ihrer Kennung.

    Parameter:
        cost_type_id: Kennung der Kostenart.
    """
    cost_type = require_found(CostTypeRepository(ctx.session).get(cost_type_id), COST_TYPE_DE, cost_type_id)
    return CostTypeRead.model_validate(cost_type)


@operation(name="cost_type.get_by_code", read_only=True, summary_de="Liest eine Kostenart über ihren Code.")
def get_cost_type_by_code(ctx: ServiceContext, code: str) -> CostTypeRead:
    """Liest eine Kostenart anhand ihres Codes.

    Parameter:
        code: Code der Kostenart, z. B. `labor_master`.
    """
    cost_type = resolve_by_code(CostTypeRepository(ctx.session), CostType.code, code, COST_TYPE_DE)
    return CostTypeRead.model_validate(cost_type)


@operation(name="cost_type.list", read_only=True, summary_de="Listet Kostenarten.")
def list_cost_types(
    ctx: ServiceContext,
    kind: str | None = None,
    active_only: bool = True,
    limit: int = 50,
    offset: int = 0,
) -> Page[CostTypeRead]:
    """Listet Kostenarten mit Paging, optional nach Art gefiltert.

    Parameter:
        kind: Art der Kostenart (`labor`, `material`, `travel`, `equipment`, `other`).
        active_only: wenn wahr, werden nur aktive Kostenarten geliefert.
        limit: maximale Anzahl Datensätze (höchstens 200).
        offset: Anzahl übersprungener Datensätze.
    """
    filters = []
    if kind is not None:
        filters.append(CostType.kind == kind)
    if active_only:
        filters.append(CostType.active.is_(True))
    return build_page(
        CostTypeRepository(ctx.session),
        CostTypeRead,
        filters=filters,
        order_by=[CostType.sort_order, CostType.code],
        limit=limit,
        offset=offset,
    )


@operation(name="cost_type.update", read_only=False, summary_de="Ändert eine Kostenart.")
def update_cost_type(
    ctx: ServiceContext,
    cost_type_id: uuid.UUID,
    data: CostTypeUpdate,
    expected_version: int | None = None,
) -> CostTypeRead:
    """Ändert eine Kostenart; nur übergebene Felder werden geändert.

    Parameter:
        cost_type_id: Kennung der Kostenart.
        data: zu ändernde Felder.
        expected_version: erwartete Version für optimistisches Sperren.
    """
    repository = CostTypeRepository(ctx.session)
    cost_type = require_found(repository.get(cost_type_id), COST_TYPE_DE, cost_type_id)
    check_version(cost_type, expected_version, COST_TYPE_DE)
    if data.default_unit_code is not None:
        _require_unit(ctx, data.default_unit_code)
    changes = apply_updates(cost_type, data, skip=["attributes"])
    if "attributes" in changes:
        cost_type.attributes = validate_attributes(ctx, CostType.__tablename__, changes["attributes"])
    ctx.session.flush()
    return CostTypeRead.model_validate(cost_type)


@operation(name="cost_type.delete", read_only=False, summary_de="Löscht eine Kostenart (Soft Delete).")
def delete_cost_type(
    ctx: ServiceContext, cost_type_id: uuid.UUID, expected_version: int | None = None
) -> CostTypeRead:
    """Markiert eine Kostenart als gelöscht.

    Parameter:
        cost_type_id: Kennung der Kostenart.
        expected_version: erwartete Version für optimistisches Sperren.
    """
    repository = CostTypeRepository(ctx.session)
    cost_type = require_found(repository.get(cost_type_id), COST_TYPE_DE, cost_type_id)
    check_version(cost_type, expected_version, COST_TYPE_DE)
    repository.soft_delete(cost_type)
    ctx.session.flush()
    return CostTypeRead.model_validate(cost_type)


# ------------------------------------------------------------- Zusatzfeld-Definitionen


def _check_enum_values(data: CustomFieldDefinitionCreate | CustomFieldDefinitionUpdate) -> None:
    """Stellt sicher, dass `enum` Werte mitbringt und andere Typen keine."""
    if data.data_type is CustomFieldDataType.ENUM:
        if not data.enum_values:
            raise ValidationFailed(
                "Für den Datentyp 'enum' müssen erlaubte Werte angegeben werden.",
                errors={"enum_values": "mindestens ein Wert erforderlich"},
            )
    elif data.data_type is not None and data.enum_values:
        raise ValidationFailed(
            f"Erlaubte Werte sind nur für den Datentyp 'enum' zulässig, nicht für '{data.data_type.value}'.",
            errors={"enum_values": "nur bei data_type 'enum' erlaubt"},
        )


@operation(
    name="custom_field.create",
    read_only=False,
    summary_de="Legt ein Zusatzfeld für eine Entität an.",
)
def create_custom_field(ctx: ServiceContext, data: CustomFieldDefinitionCreate) -> CustomFieldDefinitionRead:
    """Legt eine Zusatzfeld-Definition an; danach ist das Feld in `attributes` erlaubt.

    Parameter:
        data: Entität, Schlüssel, Anzeigename, Datentyp und ob das Feld Pflicht ist.
    """
    repository = CustomFieldDefinitionRepository(ctx.session)
    ensure_unique(
        repository,
        CustomFieldDefinition.entity_type == data.entity_type,
        CustomFieldDefinition.key == data.key,
        message=(f"Für '{data.entity_type}' ist das Zusatzfeld '{data.key}' bereits definiert."),
        entity_type=data.entity_type,
        key=data.key,
    )
    _check_enum_values(data)
    definition = repository.add(CustomFieldDefinition(**data.model_dump()))
    ctx.session.flush()
    return CustomFieldDefinitionRead.model_validate(definition)


@operation(name="custom_field.get", read_only=True, summary_de="Liest eine Zusatzfeld-Definition.")
def get_custom_field(ctx: ServiceContext, definition_id: uuid.UUID) -> CustomFieldDefinitionRead:
    """Liest eine Zusatzfeld-Definition anhand ihrer Kennung.

    Parameter:
        definition_id: Kennung der Definition.
    """
    definition = require_found(
        CustomFieldDefinitionRepository(ctx.session).get(definition_id),
        CUSTOM_FIELD_DE,
        definition_id,
    )
    return CustomFieldDefinitionRead.model_validate(definition)


@operation(name="custom_field.list", read_only=True, summary_de="Listet Zusatzfeld-Definitionen.")
def list_custom_fields(
    ctx: ServiceContext,
    entity_type: str | None = None,
    active_only: bool = True,
    limit: int = 50,
    offset: int = 0,
) -> Page[CustomFieldDefinitionRead]:
    """Listet Zusatzfeld-Definitionen, optional für eine Entität.

    Parameter:
        entity_type: Tabellenname der Entität, z. B. `customers`.
        active_only: wenn wahr, werden nur aktive Definitionen geliefert.
        limit: maximale Anzahl Datensätze (höchstens 200).
        offset: Anzahl übersprungener Datensätze.
    """
    filters = []
    if entity_type is not None:
        filters.append(CustomFieldDefinition.entity_type == entity_type)
    if active_only:
        filters.append(CustomFieldDefinition.active.is_(True))
    return build_page(
        CustomFieldDefinitionRepository(ctx.session),
        CustomFieldDefinitionRead,
        filters=filters,
        order_by=[
            CustomFieldDefinition.entity_type,
            CustomFieldDefinition.sort_order,
            CustomFieldDefinition.key,
        ],
        limit=limit,
        offset=offset,
    )


@operation(name="custom_field.update", read_only=False, summary_de="Ändert eine Zusatzfeld-Definition.")
def update_custom_field(
    ctx: ServiceContext,
    definition_id: uuid.UUID,
    data: CustomFieldDefinitionUpdate,
    expected_version: int | None = None,
) -> CustomFieldDefinitionRead:
    """Ändert eine Zusatzfeld-Definition; nur übergebene Felder werden geändert.

    Parameter:
        definition_id: Kennung der Definition.
        data: zu ändernde Felder.
        expected_version: erwartete Version für optimistisches Sperren.
    """
    repository = CustomFieldDefinitionRepository(ctx.session)
    definition = require_found(repository.get(definition_id), CUSTOM_FIELD_DE, definition_id)
    check_version(definition, expected_version, CUSTOM_FIELD_DE)
    if data.data_type is not None or data.enum_values is not None:
        merged = CustomFieldDefinitionUpdate(
            data_type=data.data_type or CustomFieldDataType(definition.data_type),
            enum_values=data.enum_values if data.enum_values is not None else definition.enum_values,
        )
        _check_enum_values(merged)
    apply_updates(definition, data)
    ctx.session.flush()
    return CustomFieldDefinitionRead.model_validate(definition)


@operation(
    name="custom_field.delete",
    read_only=False,
    summary_de="Löscht eine Zusatzfeld-Definition (Soft Delete).",
)
def delete_custom_field(
    ctx: ServiceContext, definition_id: uuid.UUID, expected_version: int | None = None
) -> CustomFieldDefinitionRead:
    """Markiert eine Zusatzfeld-Definition als gelöscht.

    Parameter:
        definition_id: Kennung der Definition.
        expected_version: erwartete Version für optimistisches Sperren.
    """
    repository = CustomFieldDefinitionRepository(ctx.session)
    definition = require_found(repository.get(definition_id), CUSTOM_FIELD_DE, definition_id)
    check_version(definition, expected_version, CUSTOM_FIELD_DE)
    repository.soft_delete(definition)
    ctx.session.flush()
    return CustomFieldDefinitionRead.model_validate(definition)
