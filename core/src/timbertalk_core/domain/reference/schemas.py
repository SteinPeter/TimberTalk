"""Schemas der Referenzdaten."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from timbertalk_core.domain.enums import CostTypeKind, CustomFieldDataType
from timbertalk_core.schemas import BaseSchema, MoneyValue


class UnitCreate(BaseSchema):
    """Neue Einheit."""

    code: str = Field(min_length=1, max_length=20, description="Kurzzeichen, z. B. `h` oder `m3`")
    label_de: str = Field(min_length=1, max_length=100, description="Anzeigename auf Deutsch")
    decimals: int = Field(default=2, ge=0, le=6, description="Nachkommastellen in der Anzeige")
    active: bool = True
    sort_order: int = 100


class UnitUpdate(BaseSchema):
    """Änderung einer Einheit; nur gesetzte Felder werden übernommen."""

    label_de: str | None = Field(default=None, min_length=1, max_length=100)
    decimals: int | None = Field(default=None, ge=0, le=6)
    active: bool | None = None
    sort_order: int | None = None


class UnitRead(BaseSchema):
    """Einheit mit Verwaltungsfeldern."""

    id: uuid.UUID
    code: str
    label_de: str
    decimals: int
    active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int


class CostTypeCreate(BaseSchema):
    """Neue Kostenart; neue Kostenfaktoren brauchen keine Code-Änderung."""

    code: str = Field(min_length=1, max_length=50, description="Kurzzeichen, z. B. `labor_master`")
    name_de: str = Field(min_length=1, max_length=150, description="Anzeigename auf Deutsch")
    kind: CostTypeKind = Field(description="Verhalten: labor, material, travel, equipment, other")
    default_unit_code: str = Field(min_length=1, max_length=20, description="Vorgabe-Einheit")
    default_unit_price: MoneyValue | None = Field(default=None, description="Vorgabepreis je Einheit in Euro")
    tax_rate_code: str | None = Field(default=None, max_length=20, description="Code des Steuersatzes")
    labor_share: bool = Field(default=False, description="Lohnanteil im Sinne von § 35a EStG")
    active: bool = True
    sort_order: int = 100
    attributes: dict[str, Any] = Field(default_factory=dict)


class CostTypeUpdate(BaseSchema):
    """Änderung einer Kostenart; nur gesetzte Felder werden übernommen."""

    name_de: str | None = Field(default=None, min_length=1, max_length=150)
    kind: CostTypeKind | None = None
    default_unit_code: str | None = Field(default=None, min_length=1, max_length=20)
    default_unit_price: MoneyValue | None = None
    tax_rate_code: str | None = Field(default=None, max_length=20)
    labor_share: bool | None = None
    active: bool | None = None
    sort_order: int | None = None
    attributes: dict[str, object] | None = None


class CostTypeRead(BaseSchema):
    """Kostenart mit Verwaltungsfeldern."""

    id: uuid.UUID
    code: str
    name_de: str
    kind: CostTypeKind
    default_unit_code: str
    default_unit_price: MoneyValue | None
    tax_rate_code: str | None
    labor_share: bool
    active: bool
    sort_order: int
    attributes: dict[str, object]
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int


class CustomFieldDefinitionCreate(BaseSchema):
    """Neue Definition eines Zusatzfeldes."""

    entity_type: str = Field(min_length=1, max_length=60, description="Tabellenname, z. B. `customers`")
    key: str = Field(
        min_length=1,
        max_length=60,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Schlüssel in `attributes`, Kleinbuchstaben und Unterstriche",
    )
    label_de: str = Field(min_length=1, max_length=150)
    data_type: CustomFieldDataType
    unit_code: str | None = Field(default=None, max_length=20)
    required: bool = False
    enum_values: list[str] | None = Field(
        default=None, description="Erlaubte Werte, nur bei data_type `enum`"
    )
    active: bool = True
    sort_order: int = 100


class CustomFieldDefinitionUpdate(BaseSchema):
    """Änderung einer Zusatzfeld-Definition; nur gesetzte Felder werden übernommen."""

    label_de: str | None = Field(default=None, min_length=1, max_length=150)
    data_type: CustomFieldDataType | None = None
    unit_code: str | None = Field(default=None, max_length=20)
    required: bool | None = None
    enum_values: list[str] | None = None
    active: bool | None = None
    sort_order: int | None = None


class CustomFieldDefinitionRead(BaseSchema):
    """Zusatzfeld-Definition mit Verwaltungsfeldern."""

    id: uuid.UUID
    entity_type: str
    key: str
    label_de: str
    data_type: CustomFieldDataType
    unit_code: str | None
    required: bool
    enum_values: list[str] | None
    active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int
