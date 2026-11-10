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
from timbertalk_core.config import Settings
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


TEST_API_KEY = "test-schluessel"
"""Platzhalter-Schlüssel, den die Tests in der Kopfzeile X-API-Key senden."""


@pytest.fixture
def api_settings() -> Settings:
    """Einstellungen für die API-Tests."""
    return Settings(_env_file=None, api_key=TEST_API_KEY, environment="test")  # type: ignore[call-arg]


@pytest.fixture
def app(session_factory: sessionmaker[Session], api_settings: Settings) -> FastAPI:
    """FastAPI-Anwendung auf der Testdatenbank."""
    return create_app(settings=api_settings, session_factory=session_factory)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """HTTP-Client, der Schlüssel und Akteur mitsendet."""
    with TestClient(app) as test_client:
        test_client.headers.update(
            {
                "X-API-Key": TEST_API_KEY,
                "X-Actor": str(TEST_ACTOR_ID),
                "X-Actor-Type": "user",
                "X-Source": "manual",
            }
        )
        yield test_client


@pytest.fixture
def agent_client(app: FastAPI) -> Iterator[TestClient]:
    """HTTP-Client, der sich als KI-Agent ausgibt."""
    with TestClient(app) as test_client:
        test_client.headers.update(
            {
                "X-API-Key": TEST_API_KEY,
                "X-Actor": str(TEST_ACTOR_ID),
                "X-Actor-Type": "agent",
                "X-Source": "agent",
            }
        )
        yield test_client
