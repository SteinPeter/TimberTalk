"""Prüft die Referenzdaten: Einheiten, Kostenarten und Zusatzfelder."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select

from timbertalk_core.context import ServiceContext
from timbertalk_core.domain.audit.models import AuditEvent
from timbertalk_core.domain.enums import CostTypeKind, CustomFieldDataType
from timbertalk_core.domain.reference.custom_fields import validate_attributes
from timbertalk_core.domain.reference.schemas import (
    CostTypeCreate,
    CostTypeUpdate,
    CustomFieldDefinitionCreate,
    CustomFieldDefinitionUpdate,
    UnitCreate,
    UnitUpdate,
)
from timbertalk_core.domain.reference.service import (
    create_cost_type,
    create_custom_field,
    create_unit,
    delete_cost_type,
    delete_unit,
    get_cost_type_by_code,
    get_unit_by_code,
    list_cost_types,
    list_custom_fields,
    list_units,
    update_cost_type,
    update_custom_field,
    update_unit,
)
from timbertalk_core.errors import Conflict, NotFound, ValidationFailed


@pytest.fixture
def einheiten(ctx: ServiceContext) -> None:
    """Legt die Einheiten an, die Kostenarten brauchen."""
    create_unit(ctx, UnitCreate(code="h", label_de="Stunde", decimals=2, sort_order=10))
    create_unit(ctx, UnitCreate(code="km", label_de="Kilometer", decimals=1, sort_order=20))
    create_unit(ctx, UnitCreate(code="tag", label_de="Tag", decimals=2, sort_order=30))


def test_einheit_anlegen_und_lesen(ctx: ServiceContext) -> None:
    unit = create_unit(ctx, UnitCreate(code="m3", label_de="Kubikmeter", decimals=3))
    assert unit.code == "m3"
    assert unit.decimals == 3
    assert unit.version == 1
    assert get_unit_by_code(ctx, "m3").id == unit.id


def test_doppelte_einheit_wird_abgelehnt(ctx: ServiceContext) -> None:
    create_unit(ctx, UnitCreate(code="stk", label_de="Stück"))
    with pytest.raises(Conflict, match="existiert bereits"):
        create_unit(ctx, UnitCreate(code="stk", label_de="Stück (doppelt)"))


def test_soft_delete_gibt_code_wieder_frei(ctx: ServiceContext) -> None:
    unit = create_unit(ctx, UnitCreate(code="lfm", label_de="Laufmeter"))
    delete_unit(ctx, unit.id)
    ctx.session.commit()

    with pytest.raises(NotFound):
        get_unit_by_code(ctx, "lfm")

    neu = create_unit(ctx, UnitCreate(code="lfm", label_de="Laufmeter neu"))
    ctx.session.commit()
    assert neu.id != unit.id


def test_einheit_aendern_mit_versionspruefung(ctx: ServiceContext) -> None:
    unit = create_unit(ctx, UnitCreate(code="kg", label_de="Kilogramm"))
    ctx.session.commit()

    geaendert = update_unit(ctx, unit.id, UnitUpdate(label_de="Kilo"), expected_version=1)
    ctx.session.commit()
    assert geaendert.label_de == "Kilo"
    assert geaendert.version == 2

    with pytest.raises(Conflict, match="zwischenzeitlich geändert"):
        update_unit(ctx, unit.id, UnitUpdate(label_de="Kilo!"), expected_version=1)


def test_liste_filtert_inaktive(ctx: ServiceContext) -> None:
    create_unit(ctx, UnitCreate(code="aktiv", label_de="Aktiv"))
    inaktiv = create_unit(ctx, UnitCreate(code="inaktiv", label_de="Inaktiv"))
    update_unit(ctx, inaktiv.id, UnitUpdate(active=False))
    ctx.session.commit()

    seite = list_units(ctx)
    assert [item.code for item in seite.items] == ["aktiv"]
    assert seite.total == 1
    assert list_units(ctx, active_only=False).total == 2


def test_paging(ctx: ServiceContext, einheiten: None) -> None:
    erste = list_units(ctx, limit=2, offset=0)
    zweite = list_units(ctx, limit=2, offset=2)
    assert len(erste.items) == 2
    assert erste.total == 3
    assert len(zweite.items) == 1
    assert zweite.offset == 2


def test_kostenart_anlegen(ctx: ServiceContext, einheiten: None) -> None:
    cost_type = create_cost_type(
        ctx,
        CostTypeCreate(
            code="labor_master",
            name_de="Lohn Meister",
            kind=CostTypeKind.LABOR,
            default_unit_code="h",
            default_unit_price=Decimal("68.5000"),
            tax_rate_code="19",
            labor_share=True,
            sort_order=10,
        ),
    )
    assert cost_type.kind is CostTypeKind.LABOR
    assert cost_type.default_unit_price == Decimal("68.5000")
    assert cost_type.labor_share is True
    assert get_cost_type_by_code(ctx, "labor_master").id == cost_type.id


def test_neue_kostenart_ohne_codeaenderung(ctx: ServiceContext, einheiten: None) -> None:
    """Abnahmekriterium: 'Gerüst' (equipment, Tag) ist reine Dateneingabe."""
    geruest = create_cost_type(
        ctx,
        CostTypeCreate(
            code="scaffolding",
            name_de="Gerüst",
            kind=CostTypeKind.EQUIPMENT,
            default_unit_code="tag",
            default_unit_price=Decimal("120.00"),
        ),
    )
    ctx.session.commit()
    assert geruest.kind is CostTypeKind.EQUIPMENT
    assert geruest.default_unit_code == "tag"
    assert list_cost_types(ctx, kind="equipment").total == 1


def test_kostenart_braucht_bekannte_einheit(ctx: ServiceContext) -> None:
    with pytest.raises(NotFound, match="Einheit mit dem Code 'gibtsnicht'"):
        create_cost_type(
            ctx,
            CostTypeCreate(
                code="unbekannt",
                name_de="Unbekannt",
                kind=CostTypeKind.OTHER,
                default_unit_code="gibtsnicht",
            ),
        )


def test_kostenart_aendern(ctx: ServiceContext, einheiten: None) -> None:
    cost_type = create_cost_type(
        ctx,
        CostTypeCreate(
            code="disposal",
            name_de="Entsorgung",
            kind=CostTypeKind.OTHER,
            default_unit_code="h",
        ),
    )
    ctx.session.commit()
    geaendert = update_cost_type(
        ctx, cost_type.id, CostTypeUpdate(default_unit_code="tag", name_de="Entsorgung pauschal")
    )
    ctx.session.commit()
    assert geaendert.default_unit_code == "tag"
    assert geaendert.name_de == "Entsorgung pauschal"

    delete_cost_type(ctx, cost_type.id)
    ctx.session.commit()
    assert list_cost_types(ctx).total == 0


def test_gleitkommazahl_als_preis_wird_abgelehnt() -> None:
    with pytest.raises(ValueError, match="Gleitkommazahlen"):
        CostTypeCreate(
            code="float",
            name_de="Float",
            kind=CostTypeKind.OTHER,
            default_unit_code="h",
            default_unit_price=12.5,  # type: ignore[arg-type]
        )


# ------------------------------------------------------------------ Zusatzfelder


def test_neues_zusatzfeld_wird_validiert(ctx: ServiceContext) -> None:
    """Abnahmekriterium: customers.attributes.referral_source über Definition anlegen."""
    create_custom_field(
        ctx,
        CustomFieldDefinitionCreate(
            entity_type="customers",
            key="referral_source",
            label_de="Wie hat der Kunde uns gefunden?",
            data_type=CustomFieldDataType.ENUM,
            enum_values=["empfehlung", "internet", "messe"],
        ),
    )
    ctx.session.commit()

    assert validate_attributes(ctx, "customers", {"referral_source": "messe"}) == {"referral_source": "messe"}

    with pytest.raises(ValidationFailed) as fehler:
        validate_attributes(ctx, "customers", {"referral_source": "zeitung"})
    assert "referral_source" in fehler.value.errors


def test_unbekanntes_zusatzfeld_wird_abgelehnt(ctx: ServiceContext) -> None:
    with pytest.raises(ValidationFailed, match="ungültig") as fehler:
        validate_attributes(ctx, "customers", {"gibtsnicht": "wert"})
    assert "Unbekanntes Zusatzfeld" in fehler.value.errors["gibtsnicht"]


def test_pflichtfeld_wird_erzwungen(ctx: ServiceContext) -> None:
    create_custom_field(
        ctx,
        CustomFieldDefinitionCreate(
            entity_type="projects",
            key="bauleiter",
            label_de="Bauleiter",
            data_type=CustomFieldDataType.TEXT,
            required=True,
        ),
    )
    ctx.session.commit()

    with pytest.raises(ValidationFailed) as fehler:
        validate_attributes(ctx, "projects", {})
    assert "fehlt" in fehler.value.errors["bauleiter"]
    assert validate_attributes(ctx, "projects", {"bauleiter": "Meier"}) == {"bauleiter": "Meier"}


@pytest.mark.parametrize(
    ("data_type", "eingabe", "erwartet"),
    [
        (CustomFieldDataType.TEXT, "Hallo", "Hallo"),
        (CustomFieldDataType.INT, "42", 42),
        (CustomFieldDataType.INT, 42, 42),
        (CustomFieldDataType.DECIMAL, "12.50", "12.50"),
        (CustomFieldDataType.DECIMAL, Decimal("0.30"), "0.30"),
        (CustomFieldDataType.DATE, "2026-03-15", "2026-03-15"),
        (CustomFieldDataType.BOOL, True, True),
        (CustomFieldDataType.BOOL, "false", False),
    ],
)
def test_zusatzfeld_typen_werden_normalisiert(
    ctx: ServiceContext, data_type: CustomFieldDataType, eingabe: object, erwartet: object
) -> None:
    create_custom_field(
        ctx,
        CustomFieldDefinitionCreate(
            entity_type="customers",
            key="probe",
            label_de="Probe",
            data_type=data_type,
        ),
    )
    ctx.session.commit()
    assert validate_attributes(ctx, "customers", {"probe": eingabe}) == {"probe": erwartet}


@pytest.mark.parametrize(
    ("data_type", "eingabe"),
    [
        (CustomFieldDataType.INT, "keine Zahl"),
        (CustomFieldDataType.INT, True),
        (CustomFieldDataType.DECIMAL, 1.5),
        (CustomFieldDataType.DECIMAL, "1.1234567"),
        (CustomFieldDataType.DATE, "15.03.2026"),
        (CustomFieldDataType.BOOL, "vielleicht"),
        (CustomFieldDataType.TEXT, 123),
    ],
)
def test_falscher_typ_im_zusatzfeld_wird_abgelehnt(
    ctx: ServiceContext, data_type: CustomFieldDataType, eingabe: object
) -> None:
    create_custom_field(
        ctx,
        CustomFieldDefinitionCreate(
            entity_type="customers", key="probe", label_de="Probe", data_type=data_type
        ),
    )
    ctx.session.commit()
    with pytest.raises(ValidationFailed):
        validate_attributes(ctx, "customers", {"probe": eingabe})


def test_enum_ohne_werte_wird_abgelehnt(ctx: ServiceContext) -> None:
    with pytest.raises(ValidationFailed, match="erlaubte Werte"):
        create_custom_field(
            ctx,
            CustomFieldDefinitionCreate(
                entity_type="customers",
                key="leer",
                label_de="Leer",
                data_type=CustomFieldDataType.ENUM,
            ),
        )


def test_werte_nur_bei_enum(ctx: ServiceContext) -> None:
    with pytest.raises(ValidationFailed, match="nur für den Datentyp 'enum'"):
        create_custom_field(
            ctx,
            CustomFieldDefinitionCreate(
                entity_type="customers",
                key="text_mit_werten",
                label_de="Text",
                data_type=CustomFieldDataType.TEXT,
                enum_values=["a", "b"],
            ),
        )


def test_doppeltes_zusatzfeld_wird_abgelehnt(ctx: ServiceContext) -> None:
    definition = CustomFieldDefinitionCreate(
        entity_type="customers",
        key="doppelt",
        label_de="Doppelt",
        data_type=CustomFieldDataType.TEXT,
    )
    create_custom_field(ctx, definition)
    ctx.session.commit()
    with pytest.raises(Conflict, match="bereits definiert"):
        create_custom_field(ctx, definition)


def test_zusatzfeld_definition_aendern_und_listen(ctx: ServiceContext) -> None:
    definition = create_custom_field(
        ctx,
        CustomFieldDefinitionCreate(
            entity_type="customers",
            key="farbe",
            label_de="Farbe",
            data_type=CustomFieldDataType.ENUM,
            enum_values=["rot", "blau"],
        ),
    )
    ctx.session.commit()
    geaendert = update_custom_field(
        ctx, definition.id, CustomFieldDefinitionUpdate(enum_values=["rot", "blau", "grün"])
    )
    ctx.session.commit()
    assert geaendert.enum_values == ["rot", "blau", "grün"]
    assert list_custom_fields(ctx, entity_type="customers").total == 1
    assert list_custom_fields(ctx, entity_type="projects").total == 0


def test_kostenart_mit_zusatzfeld(ctx: ServiceContext, einheiten: None) -> None:
    create_custom_field(
        ctx,
        CustomFieldDefinitionCreate(
            entity_type="cost_types",
            key="konto",
            label_de="Sachkonto",
            data_type=CustomFieldDataType.INT,
        ),
    )
    ctx.session.commit()
    cost_type = create_cost_type(
        ctx,
        CostTypeCreate(
            code="mit_konto",
            name_de="Mit Konto",
            kind=CostTypeKind.MATERIAL,
            default_unit_code="h",
            attributes={"konto": "4400"},
        ),
    )
    ctx.session.commit()
    assert cost_type.attributes == {"konto": 4400}

    with pytest.raises(ValidationFailed):
        create_cost_type(
            ctx,
            CostTypeCreate(
                code="falsches_konto",
                name_de="Falsch",
                kind=CostTypeKind.MATERIAL,
                default_unit_code="h",
                attributes={"konto": "keine Zahl"},
            ),
        )


def test_jede_schreibende_operation_protokolliert(ctx: ServiceContext) -> None:
    """Abnahmekriterium: je schreibende Operation genau ein Audit-Eintrag."""
    unit = create_unit(ctx, UnitCreate(code="protokoll", label_de="Protokoll"))
    ctx.session.commit()
    update_unit(ctx, unit.id, UnitUpdate(label_de="Protokoll neu"))
    ctx.session.commit()
    delete_unit(ctx, unit.id)
    ctx.session.commit()

    events = list(
        ctx.session.scalars(
            select(AuditEvent)
            .where(AuditEvent.entity_id == unit.id)
            .order_by(AuditEvent.occurred_at, AuditEvent.id)
        )
    )
    assert [event.action for event in events] == ["create", "update", "delete"]
    assert events[1].changes["label_de"] == {"old": "Protokoll", "new": "Protokoll neu"}
