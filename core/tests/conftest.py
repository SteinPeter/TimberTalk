"""Gemeinsame Test-Fixtures."""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from timbertalk_core.api.app import create_app
from timbertalk_core.context import ActorType, ServiceContext, Source
from timbertalk_core.db.metadata import get_metadata
from timbertalk_core.db.session import create_session_factory

TEST_ACTOR_ID = uuid.UUID("00000000-0000-7000-8000-000000000001")
"""Fester Akteur in Tests, damit Audit-Einträge vergleichbar sind."""


@pytest.fixture
def engine() -> Iterator[Engine]:
    """In-Arbeitsspeicher-Datenbank mit allen Tabellen des Datenmodells."""
    db = create_engine(
        "sqlite+pysqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    get_metadata().create_all(db)
    yield db
    db.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    """Session-Fabrik inklusive zentraler Audit-Erzeugung."""
    return create_session_factory(engine)


@pytest.fixture
def session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """Offene Session für einen Test."""
    with session_factory() as open_session:
        yield open_session


@pytest.fixture
def ctx(session: Session) -> ServiceContext:
    """Kontext eines menschlichen Akteurs mit Quelle `manual`."""
    return ServiceContext(
        session=session,
        actor_id=TEST_ACTOR_ID,
        actor_type=ActorType.USER,
        source=Source.MANUAL,
    )


@pytest.fixture
def agent_ctx(session: Session) -> ServiceContext:
    """Kontext eines KI-Agenten mit Quelle `agent`."""
    return ServiceContext(
        session=session,
        actor_id=TEST_ACTOR_ID,
        actor_type=ActorType.AGENT,
        source=Source.AGENT,
    )


@pytest.fixture
def app() -> FastAPI:
    """Frische FastAPI-Anwendung für einen Test."""
    return create_app()


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """HTTP-Client gegen die Anwendung."""
    with TestClient(app) as test_client:
        yield test_client
