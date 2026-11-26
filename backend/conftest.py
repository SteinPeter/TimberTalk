# Gemeinsame Hilfen für alle Tests – für tests/ genauso wie für die Tests in den Feature-Ordnern.
# pytest lädt diese Datei von selbst. Ein Test bekommt eine Hilfe, indem er ihren Namen als
# Parameter nennt, z. B. def test_kunde_anlegen(client): ...

import os

# Vor allem anderen: Tests arbeiten nie mit der echten Datenbank-Datei, sondern im Arbeitsspeicher.
os.environ["TIMBERTALK_DATABASE_URL"] = "sqlite://"
# Tests laufen ohne Demo-Modus und ohne Demo-Daten (die prüft eigens test_demo.py).
os.environ["TIMBERTALK_DEMO"] = "false"

from collections.abc import Callable, Iterator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import Engine  # noqa: E402
from sqlmodel import Session, SQLModel  # noqa: E402

from timbertalk.db import IN_MEMORY_URL, get_session, make_engine  # noqa: E402
from timbertalk.features.accounts import service as accounts  # noqa: E402
from timbertalk.main import app  # noqa: E402

# Passwort der Test-Konten, die client und client_as anlegen.
TEST_PASSWORD = "test-passwort"


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
def anonymous_client(engine: Engine) -> Iterator[TestClient]:
    """Ein nachgespielter Browser für die API, noch nicht angemeldet.

    Alle Anfragen nutzen die frische Datenbank.
    """

    def session_for_test() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = session_for_test
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def client_as(
    engine: Engine, anonymous_client: TestClient
) -> Iterator[Callable[[str], TestClient]]:
    """Gibt einen Browser zurück, der mit einem neuen Konto der Rolle role angemeldet ist.

    Beispiel: geselle = client_as("journeyman"). Jeder Aufruf legt ein eigenes Konto an.
    """
    made = []

    def make(role: str) -> TestClient:
        with Session(engine) as session:
            account, _ = accounts.create_account(
                session, f"test-{role}-{len(made)}", f"Test {role}", role, None, TEST_PASSWORD
            )
            account.must_change_password = False
            session.add(account)
            session.commit()
            username = account.username
        browser = TestClient(app)
        response = browser.post(
            "/api/accounts/login", json={"identifier": username, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200, response.text
        made.append(browser)
        return browser

    yield make
    for browser in made:
        browser.close()


@pytest.fixture
def client(client_as: Callable[[str], TestClient]) -> TestClient:
    """Ein nachgespielter Browser für die API, angemeldet als Admin (darf alles).

    Alle Anfragen nutzen die frische Datenbank. Für andere Rollen: client_as("journeyman").
    """
    return client_as("admin")
