"""Geschäftslogik der Mitarbeiter."""

from __future__ import annotations

import uuid

from timbertalk_core.context import ServiceContext
from timbertalk_core.domain.people.models import Employee
from timbertalk_core.domain.people.repository import EmployeeRepository
from timbertalk_core.domain.people.schemas import EmployeeCreate, EmployeeRead, EmployeeUpdate
from timbertalk_core.domain.reference.custom_fields import validate_attributes
from timbertalk_core.domain.reference.models import CostType
from timbertalk_core.domain.reference.repository import CostTypeRepository
from timbertalk_core.operations import operation
from timbertalk_core.schemas import Page
from timbertalk_core.service_support import (
    apply_updates,
    build_page,
    check_version,
    require_found,
    resolve_by_code,
)

EMPLOYEE_DE = "Mitarbeiter"


def _check_cost_type(ctx: ServiceContext, code: str | None) -> None:
    """Stellt sicher, dass eine angegebene Vorgabe-Kostenart existiert."""
    if code is not None:
        resolve_by_code(CostTypeRepository(ctx.session), CostType.code, code, "Kostenart")


@operation(name="employee.create", read_only=False, summary_de="Legt einen Mitarbeiter an.")
def create_employee(ctx: ServiceContext, data: EmployeeCreate) -> EmployeeRead:
    """Legt einen Mitarbeiter an.

    Parameter:
        data: Name, Rolle und optionale Vorgabe-Kostenart für Stundenbuchungen.
    """
    repository = EmployeeRepository(ctx.session)
    _check_cost_type(ctx, data.default_cost_type_code)
    values = data.model_dump()
    values["attributes"] = validate_attributes(ctx, Employee.__tablename__, values["attributes"])
    employee = repository.add(Employee(**values))
    ctx.flush()
    return EmployeeRead.model_validate(employee)


@operation(name="employee.get", read_only=True, summary_de="Liest einen Mitarbeiter.")
def get_employee(ctx: ServiceContext, employee_id: uuid.UUID) -> EmployeeRead:
    """Liest einen Mitarbeiter anhand seiner Kennung.

    Parameter:
        employee_id: Kennung des Mitarbeiters.
    """
    employee = require_found(EmployeeRepository(ctx.session).get(employee_id), EMPLOYEE_DE, employee_id)
    return EmployeeRead.model_validate(employee)


@operation(name="employee.list", read_only=True, summary_de="Listet Mitarbeiter.")
def list_employees(
    ctx: ServiceContext,
    role: str | None = None,
    active_only: bool = True,
    limit: int = 50,
    offset: int = 0,
) -> Page[EmployeeRead]:
    """Listet Mitarbeiter mit Paging, optional nach Rolle gefiltert.

    Parameter:
        role: Rolle (`owner`, `master`, `journeyman`, `apprentice`, `office`).
        active_only: wenn wahr, werden nur aktive Mitarbeiter geliefert.
        limit: maximale Anzahl Datensätze (höchstens 200).
        offset: Anzahl übersprungener Datensätze.
    """
    filters = []
    if role is not None:
        filters.append(Employee.role == role)
    if active_only:
        filters.append(Employee.active.is_(True))
    return build_page(
        EmployeeRepository(ctx.session),
        EmployeeRead,
        filters=filters,
        order_by=[Employee.last_name, Employee.first_name],
        limit=limit,
        offset=offset,
    )


@operation(name="employee.update", read_only=False, summary_de="Ändert einen Mitarbeiter.")
def update_employee(
    ctx: ServiceContext,
    employee_id: uuid.UUID,
    data: EmployeeUpdate,
    expected_version: int | None = None,
) -> EmployeeRead:
    """Ändert einen Mitarbeiter; nur übergebene Felder werden geändert.

    Parameter:
        employee_id: Kennung des Mitarbeiters.
        data: zu ändernde Felder.
        expected_version: erwartete Version für optimistisches Sperren.
    """
    repository = EmployeeRepository(ctx.session)
    employee = require_found(repository.get(employee_id), EMPLOYEE_DE, employee_id)
    check_version(employee, expected_version, EMPLOYEE_DE)
    if data.default_cost_type_code is not None:
        _check_cost_type(ctx, data.default_cost_type_code)
    changes = apply_updates(employee, data, skip=["attributes"])
    if "attributes" in changes:
        employee.attributes = validate_attributes(ctx, Employee.__tablename__, changes["attributes"])
    ctx.flush()
    return EmployeeRead.model_validate(employee)


@operation(name="employee.delete", read_only=False, summary_de="Löscht einen Mitarbeiter (Soft Delete).")
def delete_employee(
    ctx: ServiceContext, employee_id: uuid.UUID, expected_version: int | None = None
) -> EmployeeRead:
    """Markiert einen Mitarbeiter als gelöscht; Buchungen bleiben erhalten.

    Parameter:
        employee_id: Kennung des Mitarbeiters.
        expected_version: erwartete Version für optimistisches Sperren.
    """
    repository = EmployeeRepository(ctx.session)
    employee = require_found(repository.get(employee_id), EMPLOYEE_DE, employee_id)
    check_version(employee, expected_version, EMPLOYEE_DE)
    repository.soft_delete(employee)
    ctx.flush()
    return EmployeeRead.model_validate(employee)
