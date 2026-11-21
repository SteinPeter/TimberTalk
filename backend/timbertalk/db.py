# Die Datenbank: eine SQLite-Datei, auf die wir über SQLModel zugreifen.
# Alle Features teilen sich diese eine Datenbank; jedes Feature bringt eigene Tabellen mit.

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, text
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from timbertalk.settings import DATA_DIR, get_settings

# Diese Adresse bedeutet: Datenbank nur im Arbeitsspeicher, ohne Datei. So laufen die Tests.
IN_MEMORY_URL = "sqlite://"


def make_engine(database_url: str) -> Engine:
    """Baut eine Verbindung zur Datenbank unter database_url."""
    if database_url.startswith("sqlite:///"):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    if database_url == IN_MEMORY_URL:
        # Im Arbeitsspeicher hätte jede neue Verbindung eine eigene, leere Datenbank.
        # StaticPool sorgt dafür, dass alle dieselbe Verbindung und damit dieselben Tabellen sehen.
        return create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    # check_same_thread=False: der Webserver beantwortet Anfragen in mehreren Threads.
    return create_engine(database_url, connect_args={"check_same_thread": False})


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Die Verbindung zur Datenbank aus den Einstellungen – einmal gebaut, danach gemerkt."""
    return make_engine(get_settings().database_url)


def get_session() -> Iterator[Session]:
    """Gibt einer Anfrage ihre Datenbank-Sitzung und schließt sie danach wieder.

    In api.py so verwenden: session: Session = Depends(get_session)
    Die Tests tauschen diese Funktion gegen eine Sitzung auf einer leeren Datenbank aus.
    """
    with Session(get_engine()) as session:
        yield session


def create_tables() -> None:
    """Legt fehlende Tabellen an. Richtige Migrationen kommen erst mit Feature F3."""
    SQLModel.metadata.create_all(get_engine())


def database_ok() -> bool:
    """Prüft mit einer einfachen Abfrage, ob die Datenbank antwortet."""
    try:
        with Session(get_engine()) as session:
            session.exec(text("SELECT 1"))
    except Exception:
        return False
    return True
