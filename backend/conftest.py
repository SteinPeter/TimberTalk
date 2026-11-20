# Gemeinsame Hilfen für alle Tests – für tests/ genauso wie für die Tests in den Feature-Ordnern.
# pytest lädt diese Datei von selbst. Ein Test bekommt eine Hilfe, indem er ihren Namen als
# Parameter nennt, z. B. def test_kunde_anlegen(client): ...

import os

# Vor allem anderen: Tests arbeiten nie mit der echten Datenbank-Datei, sondern im Arbeitsspeicher.
os.environ["TIMBERTALK_DATABASE_URL"] = "sqlite://"

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import Engine  # noqa: E402
from sqlmodel import Session, SQLModel  # noqa: E402

from timbertalk.db import IN_MEMORY_URL, get_session, make_engine  # noqa: E402
from timbertalk.main import app  # noqa: E402


@pytest.fixture
def engine() -> Iterator[Engine]:
    """Eine frische, leere Datenbank im Arbeitsspeicher – für jeden Test eine neue."""
    engine = make_engine(IN_MEMORY_URL)
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """Eine Datenbank-Sitzung auf der frischen Datenbank – zum Testen von service.py."""
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(engine: Engine) -> Iterator[TestClient]:
    """Ein nachgespielter Browser für die API. Alle Anfragen nutzen die frische Datenbank."""

    def session_for_test() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = session_for_test
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
