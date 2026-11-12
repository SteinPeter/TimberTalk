# Die Datenbank: eine SQLite-Datei, auf die wir über SQLModel zugreifen.

from functools import lru_cache

from sqlalchemy import Engine, text
from sqlmodel import Session, SQLModel, create_engine

from timbertalk.settings import DATA_DIR, get_settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Baut die Verbindung zur Datenbank auf und merkt sie sich."""
    settings = get_settings()
    if settings.database_url.startswith("sqlite:///"):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: der Webserver beantwortet Anfragen in mehreren Threads.
    return create_engine(settings.database_url, connect_args={"check_same_thread": False})


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
