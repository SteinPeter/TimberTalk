"""Geschäftslogik der Kunden."""

from __future__ import annotations

import uuid

from sqlalchemy import func, or_

from timbertalk_core.context import ServiceContext
from timbertalk_core.domain.customers.models import Customer
from timbertalk_core.domain.customers.repository import CustomerRepository
from timbertalk_core.domain.customers.schemas import CustomerCreate, CustomerRead, CustomerUpdate
from timbertalk_core.domain.reference.custom_fields import validate_attributes
from timbertalk_core.operations import operation
from timbertalk_core.schemas import Page
from timbertalk_core.service_support import (
    apply_updates,
    build_page,
    check_version,
    require_found,
)

CUSTOMER_DE = "Kunde"


@operation(name="customer.create", read_only=False, summary_de="Legt einen Kunden an.")
def create_customer(ctx: ServiceContext, data: CustomerCreate) -> CustomerRead:
    """Legt einen Kunden an; privat oder gewerblich.

    Parameter:
        data: Art des Kunden, Name, Adresse und Steuerangaben.
    """
    repository = CustomerRepository(ctx.session)
    values = data.model_dump()
    values["attributes"] = validate_attributes(ctx, Customer.__tablename__, values["attributes"])
    customer = repository.add(Customer(**values))
    ctx.session.flush()
    return CustomerRead.model_validate(customer)


@operation(name="customer.get", read_only=True, summary_de="Liest einen Kunden.")
def get_customer(ctx: ServiceContext, customer_id: uuid.UUID) -> CustomerRead:
    """Liest einen Kunden anhand seiner Kennung.

    Parameter:
        customer_id: Kennung des Kunden.
    """
    customer = require_found(CustomerRepository(ctx.session).get(customer_id), CUSTOMER_DE, customer_id)
    return CustomerRead.model_validate(customer)


@operation(name="customer.list", read_only=True, summary_de="Listet Kunden.")
def list_customers(
    ctx: ServiceContext,
    search: str | None = None,
    customer_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[CustomerRead]:
    """Listet Kunden mit Paging, optional gefiltert und durchsucht.

    Parameter:
        search: Suchtext für Anzeigename, Ort oder E-Mail-Adresse.
        customer_type: `private` oder `business`.
        limit: maximale Anzahl Datensätze (höchstens 200).
        offset: Anzahl übersprungener Datensätze.
    """
    filters = []
    if customer_type is not None:
        filters.append(Customer.customer_type == customer_type)
    if search:
        muster = f"%{search.lower()}%"
        filters.append(
            or_(
                func.lower(Customer.display_name).like(muster),
                func.lower(Customer.city).like(muster),
                func.lower(Customer.email).like(muster),
            )
        )
    return build_page(
        CustomerRepository(ctx.session),
        CustomerRead,
        filters=filters,
        order_by=[Customer.display_name],
        limit=limit,
        offset=offset,
    )


@operation(name="customer.update", read_only=False, summary_de="Ändert einen Kunden.")
def update_customer(
    ctx: ServiceContext,
    customer_id: uuid.UUID,
    data: CustomerUpdate,
    expected_version: int | None = None,
) -> CustomerRead:
    """Ändert einen Kunden; nur übergebene Felder werden geändert.

    Parameter:
        customer_id: Kennung des Kunden.
        data: zu ändernde Felder.
        expected_version: erwartete Version für optimistisches Sperren.
    """
    repository = CustomerRepository(ctx.session)
    customer = require_found(repository.get(customer_id), CUSTOMER_DE, customer_id)
    check_version(customer, expected_version, CUSTOMER_DE)
    changes = apply_updates(customer, data, skip=["attributes"])
    if "attributes" in changes:
        customer.attributes = validate_attributes(ctx, Customer.__tablename__, changes["attributes"])
    ctx.session.flush()
    return CustomerRead.model_validate(customer)


@operation(name="customer.delete", read_only=False, summary_de="Löscht einen Kunden (Soft Delete).")
def delete_customer(
    ctx: ServiceContext, customer_id: uuid.UUID, expected_version: int | None = None
) -> CustomerRead:
    """Markiert einen Kunden als gelöscht; Projekte bleiben erhalten.

    Parameter:
        customer_id: Kennung des Kunden.
        expected_version: erwartete Version für optimistisches Sperren.
    """
    repository = CustomerRepository(ctx.session)
    customer = require_found(repository.get(customer_id), CUSTOMER_DE, customer_id)
    check_version(customer, expected_version, CUSTOMER_DE)
    repository.soft_delete(customer)
    ctx.session.flush()
    return CustomerRead.model_validate(customer)
