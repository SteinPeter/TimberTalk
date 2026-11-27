# Die Endpunkte des Features „Projekte“ (F3) unter /api/projects.
# Ein Endpunkt nimmt die Anfrage an, ruft eine Funktion aus service.py auf und gibt das Ergebnis
# zurück – sonst nichts. Die Sitzung kommt aus Depends(get_session).
# Meldet der Service einen Fehler (LookupError → 404, ValueError → 422), wird daraus eine Antwort
# mit deutschem Text. Das Objekt `router` muss bleiben: load_features() hängt es an die App.

# ruff meldet B008 bei `Depends(...)` im Parameter; FastAPI und CLAUDE.md verlangen genau das.
# ruff: noqa: B008

from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from timbertalk.db import get_session
from timbertalk.features.projects import service
from timbertalk.features.projects.models import (
    CustomerLookupResponse,
    CustomerProjects,
    ProjectArchiveIn,
    ProjectCreate,
    ProjectInfo,
    ProjectStatusIn,
    ProjectUpdate,
)

router = APIRouter(prefix="/api/projects", tags=["Projekte"])


def _run(function: Callable, *args, **kwargs):
    """Ruft eine Service-Funktion auf und übersetzt ihre Fehler in HTTP-Antworten."""
    try:
        return function(*args, **kwargs)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("")
def list_projects(
    text: str | None = None,
    customer_id: int | None = None,
    status: str | None = None,
    include_archived: bool = False,
    session: Session = Depends(get_session),
) -> list[ProjectInfo]:
    return _run(
        service.list_projects,
        session,
        text=text,
        customer_id=customer_id,
        status=status,
        include_archived=include_archived,
    )


@router.post("", status_code=201)
def create_project(
    data: ProjectCreate,
    session: Session = Depends(get_session),
) -> ProjectInfo:
    return _run(
        service.create_project,
        session,
        customer_id=data.customer_id,
        name=data.name,
        baustelle=data.baustelle,
        status=data.status,
        start_date=data.start_date,
        duration_days=data.duration_days,
        end_date=data.end_date,
        notes=data.notes,
        customer_name=data.customer_name,
    )


@router.get("/customers")
def list_customers(session: Session = Depends(get_session)) -> CustomerLookupResponse:
    return service.list_customers(session)


@router.get("/by-customer")
def list_customer_projects(
    include_archived: bool = False,
    session: Session = Depends(get_session),
) -> list[CustomerProjects]:
    return service.list_customer_projects(session, include_archived=include_archived)


@router.get("/{project_id}")
def get_project(
    project_id: int,
    session: Session = Depends(get_session),
) -> ProjectInfo:
    project = service.get_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Projekt {project_id} gibt es nicht.")
    return project


@router.patch("/{project_id}")
def update_project(
    project_id: int,
    data: ProjectUpdate,
    session: Session = Depends(get_session),
) -> ProjectInfo:
    fields = data.model_dump(exclude_unset=True)
    return _run(service.update_project, session, project_id, fields)


@router.patch("/{project_id}/status")
def set_project_status(
    project_id: int,
    data: ProjectStatusIn,
    session: Session = Depends(get_session),
) -> ProjectInfo:
    return _run(service.set_project_status, session, project_id, data.status)


@router.post("/{project_id}/archive")
def archive_project(
    project_id: int,
    data: ProjectArchiveIn,
    session: Session = Depends(get_session),
) -> ProjectInfo:
    return _run(service.archive_project, session, project_id, archived=data.archived)
