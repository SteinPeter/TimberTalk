"""Geschäftslogik für Projekte, Arbeitspakete und Abhängigkeiten."""

from __future__ import annotations

import uuid
from collections import defaultdict

from timbertalk_core.clock import today
from timbertalk_core.context import ServiceContext
from timbertalk_core.domain.customers.repository import CustomerRepository
from timbertalk_core.domain.projects.models import Project, WorkPackage, WorkPackageDependency
from timbertalk_core.domain.projects.repository import (
    ProjectRepository,
    WorkPackageDependencyRepository,
    WorkPackageRepository,
)
from timbertalk_core.domain.projects.schemas import (
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
    WorkPackageCreate,
    WorkPackageDependencyCreate,
    WorkPackageDependencyRead,
    WorkPackageRead,
    WorkPackageUpdate,
)
from timbertalk_core.domain.reference.custom_fields import validate_attributes
from timbertalk_core.errors import Conflict, ValidationFailed
from timbertalk_core.operations import operation
from timbertalk_core.schemas import Page
from timbertalk_core.service_support import (
    apply_updates,
    build_page,
    check_version,
    ensure_unique,
    require_found,
)

PROJECT_DE = "Projekt"
WORK_PACKAGE_DE = "Arbeitspaket"
DEPENDENCY_DE = "Abhängigkeit"
NUMBER_WIDTH = 3
"""Stellen der laufenden Nummer in `JJJJ-NNN`."""


def next_project_number(ctx: ServiceContext, year: int | None = None) -> str:
    """Ermittelt die nächste freie Projektnummer im Format `JJJJ-NNN`.

    Gelöschte Projekte zählen mit, damit eine Nummer nie zweimal vergeben wird.

    Parameter:
        ctx: Aufrufkontext mit offener Session.
        year: Jahr der Nummer; ohne Angabe das laufende Jahr.
    """
    jahr = year or today().year
    laufend = ProjectRepository(ctx.session).highest_sequence_for_year(jahr) + 1
    return f"{jahr}-{laufend:0{NUMBER_WIDTH}d}"


def _require_customer(ctx: ServiceContext, customer_id: uuid.UUID) -> None:
    """Stellt sicher, dass der Kunde existiert."""
    require_found(CustomerRepository(ctx.session).get(customer_id), "Kunde", customer_id)


@operation(name="project.create", read_only=False, summary_de="Legt ein Projekt an.")
def create_project(ctx: ServiceContext, data: ProjectCreate) -> ProjectRead:
    """Legt ein Projekt an und vergibt bei Bedarf die nächste Projektnummer.

    Parameter:
        data: Kunde, Titel, Status, Baustellenangaben und Planungszeitraum.
    """
    repository = ProjectRepository(ctx.session)
    _require_customer(ctx, data.customer_id)
    values = data.model_dump()
    values["attributes"] = validate_attributes(ctx, Project.__tablename__, values["attributes"])
    if values.get("number") is None:
        values["number"] = next_project_number(ctx)
    else:
        ensure_unique(
            repository,
            Project.number == values["number"],
            message=f"Ein Projekt mit der Nummer '{values['number']}' existiert bereits.",
            number=values["number"],
        )
    project = repository.add(Project(**values))
    ctx.flush()
    return ProjectRead.model_validate(project)


@operation(name="project.get", read_only=True, summary_de="Liest ein Projekt.")
def get_project(ctx: ServiceContext, project_id: uuid.UUID) -> ProjectRead:
    """Liest ein Projekt anhand seiner Kennung.

    Parameter:
        project_id: Kennung des Projekts.
    """
    project = require_found(ProjectRepository(ctx.session).get(project_id), PROJECT_DE, project_id)
    return ProjectRead.model_validate(project)


@operation(name="project.get_by_number", read_only=True, summary_de="Liest ein Projekt über seine Nummer.")
def get_project_by_number(ctx: ServiceContext, number: str) -> ProjectRead:
    """Liest ein Projekt anhand seiner lesbaren Nummer.

    Parameter:
        number: Projektnummer, z. B. `2026-014`.
    """
    project = ProjectRepository(ctx.session).by_number(number)
    return ProjectRead.model_validate(require_found(project, PROJECT_DE, number))


@operation(name="project.list", read_only=True, summary_de="Listet Projekte.")
def list_projects(
    ctx: ServiceContext,
    customer_id: uuid.UUID | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[ProjectRead]:
    """Listet Projekte mit Paging, optional nach Kunde und Status gefiltert.

    Parameter:
        customer_id: Kennung des Kunden.
        status: Status (`inquiry`, `planned`, `active`, `done`, `cancelled`).
        limit: maximale Anzahl Datensätze (höchstens 200).
        offset: Anzahl übersprungener Datensätze.
    """
    filters = []
    if customer_id is not None:
        filters.append(Project.customer_id == customer_id)
    if status is not None:
        filters.append(Project.status == status)
    return build_page(
        ProjectRepository(ctx.session),
        ProjectRead,
        filters=filters,
        order_by=[Project.number.desc()],
        limit=limit,
        offset=offset,
    )


@operation(name="project.update", read_only=False, summary_de="Ändert ein Projekt.")
def update_project(
    ctx: ServiceContext,
    project_id: uuid.UUID,
    data: ProjectUpdate,
    expected_version: int | None = None,
) -> ProjectRead:
    """Ändert ein Projekt; nur übergebene Felder werden geändert.

    Parameter:
        project_id: Kennung des Projekts.
        data: zu ändernde Felder.
        expected_version: erwartete Version für optimistisches Sperren.
    """
    repository = ProjectRepository(ctx.session)
    project = require_found(repository.get(project_id), PROJECT_DE, project_id)
    check_version(project, expected_version, PROJECT_DE)
    if data.customer_id is not None:
        _require_customer(ctx, data.customer_id)
    if data.number is not None and data.number != project.number:
        ensure_unique(
            repository,
            Project.number == data.number,
            message=f"Ein Projekt mit der Nummer '{data.number}' existiert bereits.",
            number=data.number,
        )
    changes = apply_updates(project, data, skip=["attributes"])
    if "attributes" in changes:
        project.attributes = validate_attributes(ctx, Project.__tablename__, changes["attributes"])
    beginn = project.planned_start
    ende = project.planned_end
    if beginn and ende and ende < beginn:
        raise ValidationFailed(
            "Das geplante Ende darf nicht vor dem geplanten Beginn liegen.",
            errors={"planned_end": "muss nach planned_start liegen"},
        )
    ctx.flush()
    return ProjectRead.model_validate(project)


@operation(name="project.delete", read_only=False, summary_de="Löscht ein Projekt (Soft Delete).")
def delete_project(
    ctx: ServiceContext, project_id: uuid.UUID, expected_version: int | None = None
) -> ProjectRead:
    """Markiert ein Projekt als gelöscht; Buchungen bleiben erhalten.

    Parameter:
        project_id: Kennung des Projekts.
        expected_version: erwartete Version für optimistisches Sperren.
    """
    repository = ProjectRepository(ctx.session)
    project = require_found(repository.get(project_id), PROJECT_DE, project_id)
    check_version(project, expected_version, PROJECT_DE)
    repository.soft_delete(project)
    ctx.flush()
    return ProjectRead.model_validate(project)


# --------------------------------------------------------------------------- Arbeitspakete


@operation(name="work_package.create", read_only=False, summary_de="Legt ein Arbeitspaket an.")
def create_work_package(ctx: ServiceContext, data: WorkPackageCreate) -> WorkPackageRead:
    """Legt ein Arbeitspaket in einem Projekt an.

    Parameter:
        data: Projekt, Titel, Status, Planungszeitraum und geplante Stunden.
    """
    require_found(ProjectRepository(ctx.session).get(data.project_id), PROJECT_DE, data.project_id)
    values = data.model_dump()
    values["attributes"] = validate_attributes(ctx, WorkPackage.__tablename__, values["attributes"])
    work_package = WorkPackageRepository(ctx.session).add(WorkPackage(**values))
    ctx.flush()
    return WorkPackageRead.model_validate(work_package)


@operation(name="work_package.get", read_only=True, summary_de="Liest ein Arbeitspaket.")
def get_work_package(ctx: ServiceContext, work_package_id: uuid.UUID) -> WorkPackageRead:
    """Liest ein Arbeitspaket anhand seiner Kennung.

    Parameter:
        work_package_id: Kennung des Arbeitspakets.
    """
    work_package = require_found(
        WorkPackageRepository(ctx.session).get(work_package_id), WORK_PACKAGE_DE, work_package_id
    )
    return WorkPackageRead.model_validate(work_package)


@operation(name="work_package.list", read_only=True, summary_de="Listet Arbeitspakete.")
def list_work_packages(
    ctx: ServiceContext,
    project_id: uuid.UUID | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[WorkPackageRead]:
    """Listet Arbeitspakete mit Paging, optional nach Projekt und Status gefiltert.

    Parameter:
        project_id: Kennung des Projekts.
        status: Status (`planned`, `active`, `done`, `cancelled`).
        limit: maximale Anzahl Datensätze (höchstens 200).
        offset: Anzahl übersprungener Datensätze.
    """
    filters = []
    if project_id is not None:
        filters.append(WorkPackage.project_id == project_id)
    if status is not None:
        filters.append(WorkPackage.status == status)
    return build_page(
        WorkPackageRepository(ctx.session),
        WorkPackageRead,
        filters=filters,
        order_by=[WorkPackage.sort_order, WorkPackage.title],
        limit=limit,
        offset=offset,
    )


@operation(name="work_package.update", read_only=False, summary_de="Ändert ein Arbeitspaket.")
def update_work_package(
    ctx: ServiceContext,
    work_package_id: uuid.UUID,
    data: WorkPackageUpdate,
    expected_version: int | None = None,
) -> WorkPackageRead:
    """Ändert ein Arbeitspaket; nur übergebene Felder werden geändert.

    Parameter:
        work_package_id: Kennung des Arbeitspakets.
        data: zu ändernde Felder.
        expected_version: erwartete Version für optimistisches Sperren.
    """
    repository = WorkPackageRepository(ctx.session)
    work_package = require_found(repository.get(work_package_id), WORK_PACKAGE_DE, work_package_id)
    check_version(work_package, expected_version, WORK_PACKAGE_DE)
    changes = apply_updates(work_package, data, skip=["attributes"])
    if "attributes" in changes:
        work_package.attributes = validate_attributes(ctx, WorkPackage.__tablename__, changes["attributes"])
    if (
        work_package.planned_start
        and work_package.planned_end
        and work_package.planned_end < work_package.planned_start
    ):
        raise ValidationFailed(
            "Das geplante Ende darf nicht vor dem geplanten Beginn liegen.",
            errors={"planned_end": "muss nach planned_start liegen"},
        )
    ctx.flush()
    return WorkPackageRead.model_validate(work_package)


@operation(name="work_package.delete", read_only=False, summary_de="Löscht ein Arbeitspaket (Soft Delete).")
def delete_work_package(
    ctx: ServiceContext, work_package_id: uuid.UUID, expected_version: int | None = None
) -> WorkPackageRead:
    """Markiert ein Arbeitspaket als gelöscht; seine Abhängigkeiten werden mitgelöscht.

    Parameter:
        work_package_id: Kennung des Arbeitspakets.
        expected_version: erwartete Version für optimistisches Sperren.
    """
    repository = WorkPackageRepository(ctx.session)
    work_package = require_found(repository.get(work_package_id), WORK_PACKAGE_DE, work_package_id)
    check_version(work_package, expected_version, WORK_PACKAGE_DE)

    dependencies = WorkPackageDependencyRepository(ctx.session)
    for dependency in dependencies.list(
        filters=[
            (WorkPackageDependency.predecessor_id == work_package_id)
            | (WorkPackageDependency.successor_id == work_package_id)
        ],
        limit=200,
    ):
        dependencies.soft_delete(dependency)

    repository.soft_delete(work_package)
    ctx.flush()
    return WorkPackageRead.model_validate(work_package)


# --------------------------------------------------------------------------- Abhängigkeiten


def _would_create_cycle(
    edges: list[tuple[uuid.UUID, uuid.UUID]], predecessor: uuid.UUID, successor: uuid.UUID
) -> bool:
    """Prüft per Tiefensuche, ob eine neue Kante einen Zyklus erzeugen würde."""
    nachfolger: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    for von, nach in edges:
        nachfolger[von].append(nach)

    # Ein Zyklus entsteht, wenn der Vorgänger vom Nachfolger aus erreichbar ist.
    stack = [successor]
    gesehen: set[uuid.UUID] = set()
    while stack:
        aktuell = stack.pop()
        if aktuell == predecessor:
            return True
        if aktuell in gesehen:
            continue
        gesehen.add(aktuell)
        stack.extend(nachfolger[aktuell])
    return False


@operation(
    name="work_package_dependency.create",
    read_only=False,
    summary_de="Verknüpft zwei Arbeitspakete als Vorgänger und Nachfolger.",
)
def create_dependency(ctx: ServiceContext, data: WorkPackageDependencyCreate) -> WorkPackageDependencyRead:
    """Legt eine Abhängigkeit zwischen zwei Arbeitspaketen an; Zyklen werden abgewiesen.

    Parameter:
        data: Kennungen von Vorgänger und Nachfolger sowie die Art der Abhängigkeit.
    """
    if data.predecessor_id == data.successor_id:
        raise ValidationFailed(
            "Ein Arbeitspaket kann nicht von sich selbst abhängen.",
            errors={"successor_id": "muss sich vom Vorgänger unterscheiden"},
        )
    packages = WorkPackageRepository(ctx.session)
    vorgaenger = require_found(packages.get(data.predecessor_id), WORK_PACKAGE_DE, data.predecessor_id)
    nachfolger = require_found(packages.get(data.successor_id), WORK_PACKAGE_DE, data.successor_id)
    if vorgaenger.project_id != nachfolger.project_id:
        raise ValidationFailed(
            "Abhängigkeiten sind nur innerhalb eines Projekts möglich.",
            errors={"successor_id": "gehört zu einem anderen Projekt"},
        )

    repository = WorkPackageDependencyRepository(ctx.session)
    ensure_unique(
        repository,
        WorkPackageDependency.predecessor_id == data.predecessor_id,
        WorkPackageDependency.successor_id == data.successor_id,
        message="Diese Abhängigkeit besteht bereits.",
        predecessor_id=str(data.predecessor_id),
        successor_id=str(data.successor_id),
    )
    if _would_create_cycle(repository.edges(), data.predecessor_id, data.successor_id):
        raise Conflict(
            "Die Abhängigkeit würde einen Ringschluss erzeugen; "
            "Arbeitspakete dürfen sich nicht gegenseitig voraussetzen.",
            predecessor_id=str(data.predecessor_id),
            successor_id=str(data.successor_id),
        )

    dependency = repository.add(WorkPackageDependency(**data.model_dump()))
    ctx.flush()
    return WorkPackageDependencyRead.model_validate(dependency)


@operation(name="work_package_dependency.list", read_only=True, summary_de="Listet Abhängigkeiten.")
def list_dependencies(
    ctx: ServiceContext,
    project_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[WorkPackageDependencyRead]:
    """Listet Abhängigkeiten, optional auf ein Projekt eingeschränkt.

    Parameter:
        project_id: Kennung des Projekts.
        limit: maximale Anzahl Datensätze (höchstens 200).
        offset: Anzahl übersprungener Datensätze.
    """
    filters = []
    if project_id is not None:
        ids = [package.id for package in WorkPackageRepository(ctx.session).for_project(project_id)]
        filters.append(WorkPackageDependency.predecessor_id.in_(ids))
    return build_page(
        WorkPackageDependencyRepository(ctx.session),
        WorkPackageDependencyRead,
        filters=filters,
        order_by=[WorkPackageDependency.created_at],
        limit=limit,
        offset=offset,
    )


@operation(
    name="work_package_dependency.delete",
    read_only=False,
    summary_de="Löscht eine Abhängigkeit (Soft Delete).",
)
def delete_dependency(
    ctx: ServiceContext, dependency_id: uuid.UUID, expected_version: int | None = None
) -> WorkPackageDependencyRead:
    """Markiert eine Abhängigkeit als gelöscht.

    Parameter:
        dependency_id: Kennung der Abhängigkeit.
        expected_version: erwartete Version für optimistisches Sperren.
    """
    repository = WorkPackageDependencyRepository(ctx.session)
    dependency = require_found(repository.get(dependency_id), DEPENDENCY_DE, dependency_id)
    check_version(dependency, expected_version, DEPENDENCY_DE)
    repository.soft_delete(dependency)
    ctx.flush()
    return WorkPackageDependencyRead.model_validate(dependency)
