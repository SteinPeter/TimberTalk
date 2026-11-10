"""Alembic-Umgebung; die Datenbank-URL kommt aus den Einstellungen des Backends."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection

from timbertalk_core.config import get_settings
from timbertalk_core.db.metadata import get_metadata
from timbertalk_core.db.session import create_db_engine

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = get_metadata()


def _database_url() -> str:
    override = context.get_x_argument(as_dictionary=True).get("url")
    if override:
        return str(override)
    configured = config.get_main_option("sqlalchemy.url", default=None)
    if configured:
        return configured
    return get_settings().database_url


def run_migrations_offline() -> None:
    """Erzeugt SQL-Anweisungen ohne Verbindung zur Datenbank."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        render_as_batch=connection.dialect.name == "sqlite",
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Führt die Migrationen gegen die konfigurierte Datenbank aus."""
    connectable = config.attributes.get("connection", None)
    if connectable is not None:
        _run(connectable)
        return
    settings = get_settings().model_copy(update={"database_url": _database_url()})
    engine = create_db_engine(settings)
    try:
        with engine.connect() as connection:
            _run(connection)
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
