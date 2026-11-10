"""Prüft, dass die Alembic-Migrationen laufen und zum Datenmodell passen."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.command import downgrade, upgrade
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import Engine, create_engine, inspect

from timbertalk_core.db.metadata import get_metadata

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def alembic_config(url: str) -> Config:
    """Alembic-Konfiguration für eine konkrete Datenbank-URL."""
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", url)
    return config


def _pending_changes(engine: Engine) -> list[object]:
    with engine.connect() as connection:
        context = MigrationContext.configure(
            connection,
            opts={"compare_type": True, "target_metadata": get_metadata()},
        )
        return list(compare_metadata(context, get_metadata()))


def test_upgrade_downgrade_upgrade_auf_sqlite(tmp_path: Path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'migration.db'}"
    config = alembic_config(url)

    upgrade(config, "head")
    engine = create_engine(url)
    try:
        tabellen_nach_upgrade = set(inspect(engine).get_table_names())
        assert tabellen_nach_upgrade >= set(get_metadata().tables)
        assert not _pending_changes(engine), "Migrationen und Modelle weichen voneinander ab"

        downgrade(config, "base")
        assert set(inspect(engine).get_table_names()) <= {"alembic_version"}

        upgrade(config, "head")
        assert set(inspect(engine).get_table_names()) == tabellen_nach_upgrade
    finally:
        engine.dispose()


@pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"),
    reason="Postgres-Test nur mit gesetzter TEST_DATABASE_URL",
)
def test_upgrade_downgrade_upgrade_auf_postgres() -> None:
    url = os.environ["TEST_DATABASE_URL"]
    config = alembic_config(url)
    engine = create_engine(url)
    try:
        upgrade(config, "head")
        assert set(inspect(engine).get_table_names()) >= set(get_metadata().tables)
        assert not _pending_changes(engine)
        downgrade(config, "base")
        upgrade(config, "head")
    finally:
        engine.dispose()
