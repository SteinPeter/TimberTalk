"""Schemas der Kunden."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Self

from pydantic import Field, model_validator

from timbertalk_core.domain.enums import CustomerType
from timbertalk_core.schemas import Attributes, BaseSchema


class CustomerCreate(BaseSchema):
    """Neuer Kunde; `display_name` wird bei Bedarf aus den Namensfeldern gebildet."""

    customer_type: CustomerType = Field(description="private oder business")
    display_name: str | None = Field(default=None, max_length=250)
    company_name: str | None = Field(default=None, max_length=200)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    street: str | None = Field(default=None, max_length=200)
    zip: str | None = Field(default=None, max_length=20)
    city: str | None = Field(default=None, max_length=100)
    country: str = Field(default="DE", min_length=2, max_length=2)
    email: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=50)
    vat_id: str | None = Field(default=None, max_length=50)
    is_construction_business: bool = Field(
        default=False, description="Bauleistender Unternehmer im Sinne von § 13b UStG"
    )
    notes: str | None = None
    attributes: Attributes

    @model_validator(mode="after")
    def _ensure_display_name(self) -> Self:
        """Bildet den Anzeigenamen aus Firmen- oder Personennamen, wenn er fehlt."""
        if self.display_name:
            return self
        if self.customer_type is CustomerType.BUSINESS and self.company_name:
            self.display_name = self.company_name
            return self
        person = " ".join(part for part in (self.first_name, self.last_name) if part).strip()
        if person:
            self.display_name = person
            return self
        raise ValueError(
            "Für den Kunden fehlt ein Name: bitte display_name, company_name oder Vor- und Nachname angeben."
        )


class CustomerUpdate(BaseSchema):
    """Änderung eines Kunden; nur gesetzte Felder werden übernommen."""

    customer_type: CustomerType | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=250)
    company_name: str | None = Field(default=None, max_length=200)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    street: str | None = Field(default=None, max_length=200)
    zip: str | None = Field(default=None, max_length=20)
    city: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    email: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=50)
    vat_id: str | None = Field(default=None, max_length=50)
    is_construction_business: bool | None = None
    notes: str | None = None
    attributes: dict[str, object] | None = None


class CustomerRead(BaseSchema):
    """Kunde mit Verwaltungsfeldern."""

    id: uuid.UUID
    customer_type: CustomerType
    display_name: str
    company_name: str | None
    first_name: str | None
    last_name: str | None
    street: str | None
    zip: str | None
    city: str | None
    country: str
    email: str | None
    phone: str | None
    vat_id: str | None
    is_construction_business: bool
    notes: str | None
    attributes: dict[str, object]
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int
