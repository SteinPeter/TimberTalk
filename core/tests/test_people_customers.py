"""Prüft Mitarbeiter und Kunden."""

from __future__ import annotations

import pytest

from timbertalk_core.context import ServiceContext
from timbertalk_core.domain.customers.schemas import CustomerCreate, CustomerUpdate
from timbertalk_core.domain.customers.service import (
    create_customer,
    delete_customer,
    get_customer,
    list_customers,
    update_customer,
)
from timbertalk_core.domain.enums import CostTypeKind, CustomerType, EmployeeRole
from timbertalk_core.domain.people.schemas import EmployeeCreate, EmployeeUpdate
from timbertalk_core.domain.people.service import (
    create_employee,
    delete_employee,
    get_employee,
    list_employees,
    update_employee,
)
from timbertalk_core.domain.reference.schemas import CostTypeCreate, UnitCreate
from timbertalk_core.domain.reference.service import create_cost_type, create_unit
from timbertalk_core.errors import NotFound


@pytest.fixture
def lohn_kostenart(ctx: ServiceContext) -> str:
    """Legt Einheit und Kostenart an, die Mitarbeiter als Vorgabe nutzen können."""
    create_unit(ctx, UnitCreate(code="h", label_de="Stunde"))
    create_cost_type(
        ctx,
        CostTypeCreate(
            code="labor_journeyman",
            name_de="Lohn Geselle",
            kind=CostTypeKind.LABOR,
            default_unit_code="h",
            labor_share=True,
        ),
    )
    ctx.session.commit()
    return "labor_journeyman"


def test_mitarbeiter_anlegen_und_lesen(ctx: ServiceContext, lohn_kostenart: str) -> None:
    employee = create_employee(
        ctx,
        EmployeeCreate(
            first_name="Anna",
            last_name="Berger",
            role=EmployeeRole.JOURNEYMAN,
            default_cost_type_code=lohn_kostenart,
        ),
    )
    ctx.session.commit()
    assert employee.display_name == "Anna Berger"
    assert employee.role is EmployeeRole.JOURNEYMAN
    assert employee.user_id is None, "Login-Benutzer kommen erst später"
    assert get_employee(ctx, employee.id).id == employee.id


def test_mitarbeiter_mit_unbekannter_kostenart(ctx: ServiceContext) -> None:
    with pytest.raises(NotFound, match="Kostenart mit dem Code 'gibtsnicht'"):
        create_employee(
            ctx,
            EmployeeCreate(
                first_name="Bert",
                last_name="Klein",
                role=EmployeeRole.MASTER,
                default_cost_type_code="gibtsnicht",
            ),
        )


def test_mitarbeiter_aendern_und_loeschen(ctx: ServiceContext) -> None:
    employee = create_employee(
        ctx, EmployeeCreate(first_name="Carl", last_name="Dorn", role=EmployeeRole.APPRENTICE)
    )
    ctx.session.commit()

    geaendert = update_employee(
        ctx, employee.id, EmployeeUpdate(role=EmployeeRole.JOURNEYMAN), expected_version=1
    )
    ctx.session.commit()
    assert geaendert.role is EmployeeRole.JOURNEYMAN

    delete_employee(ctx, employee.id)
    ctx.session.commit()
    assert list_employees(ctx).total == 0
    with pytest.raises(NotFound):
        get_employee(ctx, employee.id)


def test_mitarbeiter_nach_rolle_filtern(ctx: ServiceContext) -> None:
    create_employee(ctx, EmployeeCreate(first_name="Dora", last_name="Ast", role=EmployeeRole.OFFICE))
    create_employee(ctx, EmployeeCreate(first_name="Emil", last_name="Bast", role=EmployeeRole.MASTER))
    ctx.session.commit()
    assert list_employees(ctx, role="office").total == 1
    assert [item.last_name for item in list_employees(ctx).items] == ["Ast", "Bast"]


def test_privatkunde_anzeigename_aus_personennamen(ctx: ServiceContext) -> None:
    customer = create_customer(
        ctx,
        CustomerCreate(
            customer_type=CustomerType.PRIVATE,
            first_name="Familie",
            last_name="Schmidt",
            street="Lindenweg 3",
            zip="14467",
            city="Potsdam",
        ),
    )
    ctx.session.commit()
    assert customer.display_name == "Familie Schmidt"
    assert customer.is_construction_business is False
    assert customer.country == "DE"


def test_gewerbekunde_anzeigename_aus_firmenname(ctx: ServiceContext) -> None:
    customer = create_customer(
        ctx,
        CustomerCreate(
            customer_type=CustomerType.BUSINESS,
            company_name="Bau Beispiel GmbH",
            vat_id="DE123456789",
            is_construction_business=True,
        ),
    )
    ctx.session.commit()
    assert customer.display_name == "Bau Beispiel GmbH"
    assert customer.is_construction_business is True


def test_kunde_ohne_namen_wird_abgelehnt() -> None:
    with pytest.raises(ValueError, match="fehlt ein Name"):
        CustomerCreate(customer_type=CustomerType.PRIVATE)


def test_kunden_suchen_und_filtern(ctx: ServiceContext) -> None:
    create_customer(
        ctx,
        CustomerCreate(
            customer_type=CustomerType.PRIVATE,
            first_name="Hans",
            last_name="Meier",
            city="Berlin",
        ),
    )
    create_customer(
        ctx,
        CustomerCreate(
            customer_type=CustomerType.BUSINESS,
            company_name="Holzbau Nord GmbH",
            city="Hamburg",
            email="info@holzbau-nord.example",
        ),
    )
    ctx.session.commit()

    assert list_customers(ctx).total == 2
    assert list_customers(ctx, customer_type="business").total == 1
    assert list_customers(ctx, search="meier").total == 1
    assert list_customers(ctx, search="hamburg").total == 1
    assert list_customers(ctx, search="holzbau-nord").total == 1
    assert list_customers(ctx, search="gibtsnicht").total == 0


def test_kunde_aendern_und_loeschen(ctx: ServiceContext) -> None:
    customer = create_customer(
        ctx,
        CustomerCreate(customer_type=CustomerType.PRIVATE, first_name="Ida", last_name="Jung", city="Köln"),
    )
    ctx.session.commit()

    geaendert = update_customer(
        ctx, customer.id, CustomerUpdate(city="Bonn", phone="0228 1234"), expected_version=1
    )
    ctx.session.commit()
    assert geaendert.city == "Bonn"
    assert geaendert.phone == "0228 1234"
    assert geaendert.version == 2

    delete_customer(ctx, customer.id)
    ctx.session.commit()
    with pytest.raises(NotFound):
        get_customer(ctx, customer.id)
