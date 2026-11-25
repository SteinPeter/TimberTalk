# Dünne HTTP-Endpunkte: alle fachlichen Entscheidungen stehen im Service.
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from timbertalk.db import get_session

from . import integration, service, tools
from .models import ProjectStatus, ToolRequest


@asynccontextmanager
async def lifespan(app):
    tools.register_available_tools()
    yield


router = APIRouter(prefix="/api/projects", tags=["Projekte"], lifespan=lifespan)
Database = Annotated[Session, Depends(get_session)]


@router.get("")
def search(
    session: Database,
    text: str = "",
    kunde_id: int | None = None,
    status: ProjectStatus | None = None,
    archiviert: bool = False,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return service.read_response(
        service.list_projects, session, text, kunde_id, status, archiviert, offset
    )


@router.get("/readiness")
def readiness():
    return integration.readiness()


@router.get("/customers")
def customers(session: Database):
    return service.read_response(service.customer_options, session)


@router.get("/customer/{customer_id}")
def for_customer(customer_id: int, session: Database, archiviert: bool = False):
    return service.read_response(service.list_customer_projects, session, customer_id, archiviert)


@router.post("/tools")
def execute(request: ToolRequest, session: Database):
    return service.dispatch_tool(session, request)
