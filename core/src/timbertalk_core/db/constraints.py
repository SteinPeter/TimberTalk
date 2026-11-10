"""Hilfsmittel für Datenbank-Constraints, die mit Soft Delete zusammenarbeiten."""

from __future__ import annotations

from sqlalchemy import Index, text

ACTIVE_CONDITION = "deleted_at IS NULL"
"""Bedingung, die gelöschte Datensätze von der Eindeutigkeitsprüfung ausnimmt."""


def unique_active(name: str, *columns: str) -> Index:
    """Erzeugt einen eindeutigen Teilindex, der nur aktive Datensätze umfasst.

    Teilindizes gibt es sowohl auf SQLite als auch auf Postgres. So blockiert ein
    gelöschter Datensatz seinen Code nicht mehr.

    Parameter:
        name: Name des Index, z. B. `uq_units_code_active`.
        columns: Spalten, die zusammen eindeutig sein müssen.
    """
    condition = text(ACTIVE_CONDITION)
    return Index(
        name,
        *columns,
        unique=True,
        sqlite_where=condition,
        postgresql_where=condition,
    )
