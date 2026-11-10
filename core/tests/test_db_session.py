"""Prüft Engine-Erzeugung, SQLite-Pragmas und den Session-Kontext."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

from timbertalk_core.config import Settings
from timbertalk_core.db.session import create_db_engine, create_session_factory, session_scope


def _settings(url: str) -> Settings:
    return Settings(_env_file=None, database_url=url)  # type: ignore[call-arg]


def test_sqlite_pragmas_sind_aktiv(tmp_path: Path) -> None:
    engine = create_db_engine(_settings(f"sqlite+pysqlite:///{tmp_path / 'tt.db'}"))
    try:
        with engine.connect() as connection:
            assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1
            assert str(connection.execute(text("PRAGMA journal_mode")).scalar()).lower() == "wal"
    finally:
        engine.dispose()


def test_verzeichnis_wird_angelegt(tmp_path: Path) -> None:
    db_path = tmp_path / "neu" / "tief" / "tt.db"
    engine = create_db_engine(_settings(f"sqlite+pysqlite:///{db_path}"))
    try:
        assert db_path.parent.is_dir()
    finally:
        engine.dispose()


def test_session_scope_schreibt_und_verwirft(tmp_path: Path) -> None:
    engine = create_db_engine(_settings(f"sqlite+pysqlite:///{tmp_path / 'tt.db'}"))
    factory = create_session_factory(engine)
    try:
        with session_scope(factory) as session:
            session.execute(text("CREATE TABLE probe (wert INTEGER)"))
            session.execute(text("INSERT INTO probe VALUES (1)"))

        with (
            pytest.raises(RuntimeError, match="absichtlich"),
            session_scope(factory) as session,
        ):
            session.execute(text("INSERT INTO probe VALUES (2)"))
            raise RuntimeError("absichtlich")

        with session_scope(factory) as session:
            assert session.execute(text("SELECT count(*) FROM probe")).scalar() == 1
    finally:
        engine.dispose()
