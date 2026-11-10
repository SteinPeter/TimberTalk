"""Engine- und Session-Verwaltung inklusive SQLite-Pragmas."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import ConnectionPoolEntry

from timbertalk_core.config import Settings, get_settings
from timbertalk_core.db.audit import install_audit_listener


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def _is_file_sqlite(url: str) -> bool:
    return _is_sqlite(url) and ":memory:" not in url


def _sqlite_file_path(url: str) -> Path | None:
    """Ermittelt den Dateipfad einer SQLite-URL, sofern es eine Datei-Datenbank ist."""
    if not _is_file_sqlite(url):
        return None
    _, _, tail = url.partition(":///")
    return Path(tail) if tail else None


@event.listens_for(Engine, "connect")
def _set_sqlite_pragmas(dbapi_connection: DBAPIConnection, _record: ConnectionPoolEntry) -> None:
    """Aktiviert bei SQLite Fremdschlüssel und das WAL-Journal."""
    if type(dbapi_connection).__module__.split(".")[0] not in {"sqlite3", "pysqlite3"}:
        return
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
    finally:
        cursor.close()


def create_db_engine(settings: Settings | None = None, **kwargs: Any) -> Engine:
    """Erzeugt die SQLAlchemy-Engine für die konfigurierte Datenbank.

    Parameter:
        settings: Einstellungen; ohne Angabe werden die Prozess-Einstellungen verwendet.
        kwargs: zusätzliche Argumente für `create_engine`.
    """
    settings = settings or get_settings()
    url = settings.database_url
    options: dict[str, Any] = {"echo": settings.sql_echo, "future": True}
    if _is_sqlite(url):
        options["connect_args"] = {"check_same_thread": False}
    options.update(kwargs)

    db_path = _sqlite_file_path(url)
    if db_path is not None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(url, **options)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Erzeugt die Session-Fabrik zur Engine, inklusive zentraler Audit-Erzeugung."""
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
    install_audit_listener(factory)
    return factory


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """Stellt eine Session bereit und schreibt bzw. verwirft die Transaktion am Ende."""
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
