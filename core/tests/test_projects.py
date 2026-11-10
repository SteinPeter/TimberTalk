"""Prüft Projekte, Arbeitspakete und Abhängigkeiten."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from itertools import pairwise

import pytest

from timbertalk_core.clock import today
from timbertalk_core.context import ServiceContext
from timbertalk_core.domain.customers.schemas import CustomerCreate
from timbertalk_core.domain.customers.service import create_customer
from timbertalk_core.domain.enums import CustomerType, ProjectStatus, WorkPackageStatus
from timbertalk_core.domain.projects.schemas import (
    ProjectCreate,
    ProjectUpdate,
    WorkPackageCreate,
    WorkPackageDependencyCreate,
    WorkPackageUpdate,
)
from timbertalk_core.domain.projects.service import (
    create_dependency,
    create_project,
    create_work_package,
    delete_dependency,
    delete_project,
    delete_work_package,
    get_project_by_number,
    list_dependencies,
    list_projects,
    list_work_packages,
    next_project_number,
    update_project,
    update_work_package,
)
from timbertalk_core.errors import Conflict, NotFound, ValidationFailed


@pytest.fixture
def kunde(ctx: ServiceContext) -> uuid.UUID:
    """Legt einen Kunden an, dem Projekte zugeordnet werden."""
    customer = create_customer(
        ctx,
        CustomerCreate(
            customer_type=CustomerType.PRIVATE, first_name="Klara", last_name="Nagel", city="Berlin"
        ),
    )
    ctx.session.commit()
    return customer.id


def _projekt(ctx: ServiceContext, kunde: uuid.UUID, titel: str = "Dachgaube") -> uuid.UUID:
    project = create_project(ctx, ProjectCreate(customer_id=kunde, title=titel))
    ctx.session.commit()
    return project.id


def test_projektnummer_wird_vergeben(ctx: ServiceContext, kunde: uuid.UUID) -> None:
    jahr = today().year
    erstes = create_project(ctx, ProjectCreate(customer_id=kunde, title="Dachgaube"))
    ctx.session.commit()
    zweites = create_project(ctx, ProjectCreate(customer_id=kunde, title="Carport"))
    ctx.session.commit()

    assert erstes.number == f"{jahr}-001"
    assert zweites.number == f"{jahr}-002"
    assert erstes.status is ProjectStatus.INQUIRY
    assert get_project_by_number(ctx, erstes.number).id == erstes.id


def test_geloeschtes_projekt_blockiert_die_nummer(ctx: ServiceContext, kunde: uuid.UUID) -> None:
    """Nummern dürfen nie doppelt vergeben werden, auch nach dem Löschen nicht."""
    jahr = today().year
    erstes = create_project(ctx, ProjectCreate(customer_id=kunde, title="Erstes"))
    ctx.session.commit()
    delete_project(ctx, erstes.id)
    ctx.session.commit()

    zweites = create_project(ctx, ProjectCreate(customer_id=kunde, title="Zweites"))
    ctx.session.commit()
    assert zweites.number == f"{jahr}-002"
    assert next_project_number(ctx) == f"{jahr}-003"


def test_eigene_nummer_wird_uebernommen(ctx: ServiceContext, kunde: uuid.UUID) -> None:
    project = create_project(ctx, ProjectCreate(customer_id=kunde, title="Sonderfall", number="2026-999"))
    ctx.session.commit()
    assert project.number == "2026-999"

    with pytest.raises(Conflict, match="existiert bereits"):
        create_project(ctx, ProjectCreate(customer_id=kunde, title="Doppelt", number="2026-999"))


def test_projekt_braucht_bekannten_kunden(ctx: ServiceContext) -> None:
    with pytest.raises(NotFound, match="Kunde"):
        create_project(ctx, ProjectCreate(customer_id=uuid.uuid4(), title="Ohne Kunde"))


def test_projekt_zeitraum_wird_geprueft(ctx: ServiceContext, kunde: uuid.UUID) -> None:
    with pytest.raises(ValueError, match="geplante Ende"):
        ProjectCreate(
            customer_id=kunde,
            title="Falscher Zeitraum",
            planned_start=date(2026, 5, 1),
            planned_end=date(2026, 4, 1),
        )

    project_id = _projekt(ctx, kunde)
    update_project(ctx, project_id, ProjectUpdate(planned_start=date(2026, 5, 1)))
    ctx.session.commit()
    with pytest.raises(ValidationFailed, match="geplante Ende"):
        update_project(ctx, project_id, ProjectUpdate(planned_end=date(2026, 4, 1)))


def test_projekt_filtern(ctx: ServiceContext, kunde: uuid.UUID) -> None:
    aktiv = create_project(ctx, ProjectCreate(customer_id=kunde, title="Aktiv", status=ProjectStatus.ACTIVE))
    create_project(ctx, ProjectCreate(customer_id=kunde, title="Anfrage"))
    ctx.session.commit()

    assert list_projects(ctx, status="active").total == 1
    assert list_projects(ctx, status="active").items[0].id == aktiv.id
    assert list_projects(ctx, customer_id=kunde).total == 2
    assert list_projects(ctx, customer_id=uuid.uuid4()).total == 0


def test_arbeitspakete_mit_sortierung(ctx: ServiceContext, kunde: uuid.UUID) -> None:
    project_id = _projekt(ctx, kunde)
    zweites = create_work_package(
        ctx,
        WorkPackageCreate(
            project_id=project_id,
            title="Dach decken",
            sort_order=20,
            planned_hours=Decimal("18.500"),
        ),
    )
    erstes = create_work_package(ctx, WorkPackageCreate(project_id=project_id, title="Abbund", sort_order=10))
    ctx.session.commit()

    titel = [item.title for item in list_work_packages(ctx, project_id=project_id).items]
    assert titel == ["Abbund", "Dach decken"]
    assert zweites.planned_hours == Decimal("18.500")
    assert erstes.status is WorkPackageStatus.PLANNED


def test_arbeitspaket_braucht_projekt(ctx: ServiceContext) -> None:
    with pytest.raises(NotFound, match="Projekt"):
        create_work_package(ctx, WorkPackageCreate(project_id=uuid.uuid4(), title="Verwaist"))


def test_arbeitspaket_aendern(ctx: ServiceContext, kunde: uuid.UUID) -> None:
    project_id = _projekt(ctx, kunde)
    package = create_work_package(
        ctx, WorkPackageCreate(project_id=project_id, title="Abbund", cad_ref="cad://abbund/1")
    )
    ctx.session.commit()

    geaendert = update_work_package(
        ctx, package.id, WorkPackageUpdate(status=WorkPackageStatus.ACTIVE), expected_version=1
    )
    ctx.session.commit()
    assert geaendert.status is WorkPackageStatus.ACTIVE
    assert geaendert.cad_ref == "cad://abbund/1", "Andockpunkt für Modul B bleibt erhalten"


def test_abhaengigkeit_anlegen(ctx: ServiceContext, kunde: uuid.UUID) -> None:
    project_id = _projekt(ctx, kunde)
    abbund = create_work_package(ctx, WorkPackageCreate(project_id=project_id, title="Abbund"))
    montage = create_work_package(ctx, WorkPackageCreate(project_id=project_id, title="Montage"))
    ctx.session.commit()

    dependency = create_dependency(
        ctx, WorkPackageDependencyCreate(predecessor_id=abbund.id, successor_id=montage.id)
    )
    ctx.session.commit()
    assert dependency.type.value == "finish_to_start"
    assert list_dependencies(ctx, project_id=project_id).total == 1

    with pytest.raises(Conflict, match="besteht bereits"):
        create_dependency(ctx, WorkPackageDependencyCreate(predecessor_id=abbund.id, successor_id=montage.id))


def test_direkter_ringschluss_wird_abgelehnt(ctx: ServiceContext, kunde: uuid.UUID) -> None:
    project_id = _projekt(ctx, kunde)
    a = create_work_package(ctx, WorkPackageCreate(project_id=project_id, title="A"))
    b = create_work_package(ctx, WorkPackageCreate(project_id=project_id, title="B"))
    ctx.session.commit()

    create_dependency(ctx, WorkPackageDependencyCreate(predecessor_id=a.id, successor_id=b.id))
    ctx.session.commit()
    with pytest.raises(Conflict, match="Ringschluss"):
        create_dependency(ctx, WorkPackageDependencyCreate(predecessor_id=b.id, successor_id=a.id))


def test_indirekter_ringschluss_wird_abgelehnt(ctx: ServiceContext, kunde: uuid.UUID) -> None:
    project_id = _projekt(ctx, kunde)
    pakete = [
        create_work_package(ctx, WorkPackageCreate(project_id=project_id, title=f"Paket {i}"))
        for i in range(4)
    ]
    ctx.session.commit()

    for vorher, nachher in pairwise(pakete):
        create_dependency(ctx, WorkPackageDependencyCreate(predecessor_id=vorher.id, successor_id=nachher.id))
    ctx.session.commit()

    with pytest.raises(Conflict, match="Ringschluss"):
        create_dependency(
            ctx,
            WorkPackageDependencyCreate(predecessor_id=pakete[3].id, successor_id=pakete[0].id),
        )


def test_abhaengigkeit_von_sich_selbst_wird_abgelehnt(ctx: ServiceContext, kunde: uuid.UUID) -> None:
    project_id = _projekt(ctx, kunde)
    package = create_work_package(ctx, WorkPackageCreate(project_id=project_id, title="Allein"))
    ctx.session.commit()
    with pytest.raises(ValidationFailed, match="von sich selbst"):
        create_dependency(
            ctx, WorkPackageDependencyCreate(predecessor_id=package.id, successor_id=package.id)
        )


def test_abhaengigkeit_nur_innerhalb_eines_projekts(ctx: ServiceContext, kunde: uuid.UUID) -> None:
    erstes = _projekt(ctx, kunde, "Projekt eins")
    zweites = _projekt(ctx, kunde, "Projekt zwei")
    a = create_work_package(ctx, WorkPackageCreate(project_id=erstes, title="A"))
    b = create_work_package(ctx, WorkPackageCreate(project_id=zweites, title="B"))
    ctx.session.commit()

    with pytest.raises(ValidationFailed, match="innerhalb eines Projekts"):
        create_dependency(ctx, WorkPackageDependencyCreate(predecessor_id=a.id, successor_id=b.id))


def test_geloeschtes_paket_loest_abhaengigkeiten(ctx: ServiceContext, kunde: uuid.UUID) -> None:
    project_id = _projekt(ctx, kunde)
    a = create_work_package(ctx, WorkPackageCreate(project_id=project_id, title="A"))
    b = create_work_package(ctx, WorkPackageCreate(project_id=project_id, title="B"))
    ctx.session.commit()
    create_dependency(ctx, WorkPackageDependencyCreate(predecessor_id=a.id, successor_id=b.id))
    ctx.session.commit()

    delete_work_package(ctx, b.id)
    ctx.session.commit()
    assert list_dependencies(ctx).total == 0
    assert list_work_packages(ctx, project_id=project_id).total == 1

    # Nach dem Lösen ist die Kante frei, ein Ringschluss entsteht nicht mehr.
    c = create_work_package(ctx, WorkPackageCreate(project_id=project_id, title="C"))
    ctx.session.commit()
    create_dependency(ctx, WorkPackageDependencyCreate(predecessor_id=c.id, successor_id=a.id))
    ctx.session.commit()
    assert list_dependencies(ctx).total == 1


def test_abhaengigkeit_loeschen(ctx: ServiceContext, kunde: uuid.UUID) -> None:
    project_id = _projekt(ctx, kunde)
    a = create_work_package(ctx, WorkPackageCreate(project_id=project_id, title="A"))
    b = create_work_package(ctx, WorkPackageCreate(project_id=project_id, title="B"))
    ctx.session.commit()
    dependency = create_dependency(ctx, WorkPackageDependencyCreate(predecessor_id=a.id, successor_id=b.id))
    ctx.session.commit()

    delete_dependency(ctx, dependency.id, expected_version=1)
    ctx.session.commit()
    assert list_dependencies(ctx).total == 0
