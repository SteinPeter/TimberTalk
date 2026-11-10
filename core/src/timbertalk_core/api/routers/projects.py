"""Router für Projekte, Arbeitspakete und Abhängigkeiten."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from timbertalk_core.api.deps import ApiKey, Context
from timbertalk_core.domain.projects import service
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
from timbertalk_core.schemas import Page

projects_router = APIRouter(prefix="/projects", tags=["Projekte"])
work_packages_router = APIRouter(prefix="/work-packages", tags=["Arbeitspakete"])
dependencies_router = APIRouter(prefix="/work-package-dependencies", tags=["Abhängigkeiten"])


@projects_router.get("", summary="Projekte listen")
def list_projects(
    ctx: Context,
    _key: ApiKey,
    customer_id: uuid.UUID | None = None,
    project_status: Annotated[str | None, Query(alias="status")] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page[ProjectRead]:
    """Listet Projekte mit Paging."""
    return service.list_projects(
        ctx, customer_id=customer_id, status=project_status, limit=limit, offset=offset
    )


@projects_router.post("", status_code=status.HTTP_201_CREATED, summary="Projekt anlegen")
def create_project(ctx: Context, _key: ApiKey, data: ProjectCreate) -> ProjectRead:
    """Legt ein Projekt an und vergibt bei Bedarf die nächste Projektnummer."""
    return service.create_project(ctx, data)


@projects_router.get("/by-number/{number}", summary="Projekt über seine Nummer lesen")
def get_project_by_number(ctx: Context, _key: ApiKey, number: str) -> ProjectRead:
    """Liest ein Projekt anhand seiner lesbaren Nummer."""
    return service.get_project_by_number(ctx, number)


@projects_router.get("/{project_id}", summary="Projekt lesen")
def get_project(ctx: Context, _key: ApiKey, project_id: uuid.UUID) -> ProjectRead:
    """Liest ein Projekt."""
    return service.get_project(ctx, project_id)


@projects_router.patch("/{project_id}", summary="Projekt ändern")
def update_project(
    ctx: Context,
    _key: ApiKey,
    project_id: uuid.UUID,
    data: ProjectUpdate,
    expected_version: int | None = None,
) -> ProjectRead:
    """Ändert ein Projekt."""
    return service.update_project(ctx, project_id, data, expected_version)


@projects_router.delete("/{project_id}", summary="Projekt löschen (Soft Delete)")
def delete_project(
    ctx: Context, _key: ApiKey, project_id: uuid.UUID, expected_version: int | None = None
) -> ProjectRead:
    """Markiert ein Projekt als gelöscht."""
    return service.delete_project(ctx, project_id, expected_version)


@work_packages_router.get("", summary="Arbeitspakete listen")
def list_work_packages(
    ctx: Context,
    _key: ApiKey,
    project_id: uuid.UUID | None = None,
    package_status: Annotated[str | None, Query(alias="status")] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page[WorkPackageRead]:
    """Listet Arbeitspakete mit Paging."""
    return service.list_work_packages(
        ctx, project_id=project_id, status=package_status, limit=limit, offset=offset
    )


@work_packages_router.post("", status_code=status.HTTP_201_CREATED, summary="Arbeitspaket anlegen")
def create_work_package(ctx: Context, _key: ApiKey, data: WorkPackageCreate) -> WorkPackageRead:
    """Legt ein Arbeitspaket in einem Projekt an."""
    return service.create_work_package(ctx, data)


@work_packages_router.get("/{work_package_id}", summary="Arbeitspaket lesen")
def get_work_package(ctx: Context, _key: ApiKey, work_package_id: uuid.UUID) -> WorkPackageRead:
    """Liest ein Arbeitspaket."""
    return service.get_work_package(ctx, work_package_id)


@work_packages_router.patch("/{work_package_id}", summary="Arbeitspaket ändern")
def update_work_package(
    ctx: Context,
    _key: ApiKey,
    work_package_id: uuid.UUID,
    data: WorkPackageUpdate,
    expected_version: int | None = None,
) -> WorkPackageRead:
    """Ändert ein Arbeitspaket."""
    return service.update_work_package(ctx, work_package_id, data, expected_version)


@work_packages_router.delete("/{work_package_id}", summary="Arbeitspaket löschen (Soft Delete)")
def delete_work_package(
    ctx: Context, _key: ApiKey, work_package_id: uuid.UUID, expected_version: int | None = None
) -> WorkPackageRead:
    """Markiert ein Arbeitspaket als gelöscht; seine Abhängigkeiten werden mitgelöst."""
    return service.delete_work_package(ctx, work_package_id, expected_version)


@dependencies_router.get("", summary="Abhängigkeiten listen")
def list_dependencies(
    ctx: Context,
    _key: ApiKey,
    project_id: uuid.UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page[WorkPackageDependencyRead]:
    """Listet Abhängigkeiten zwischen Arbeitspaketen."""
    return service.list_dependencies(ctx, project_id=project_id, limit=limit, offset=offset)


@dependencies_router.post("", status_code=status.HTTP_201_CREATED, summary="Abhängigkeit anlegen")
def create_dependency(
    ctx: Context, _key: ApiKey, data: WorkPackageDependencyCreate
) -> WorkPackageDependencyRead:
    """Verknüpft zwei Arbeitspakete; Ringschlüsse werden abgewiesen."""
    return service.create_dependency(ctx, data)


@dependencies_router.delete("/{dependency_id}", summary="Abhängigkeit löschen (Soft Delete)")
def delete_dependency(
    ctx: Context, _key: ApiKey, dependency_id: uuid.UUID, expected_version: int | None = None
) -> WorkPackageDependencyRead:
    """Markiert eine Abhängigkeit als gelöscht."""
    return service.delete_dependency(ctx, dependency_id, expected_version)
