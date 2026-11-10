"""Zeitquelle des Backends; alle Zeitstempel sind zeitzonenbewusst in UTC."""

from __future__ import annotations

from datetime import UTC, date, datetime


def utc_now() -> datetime:
    """Liefert den aktuellen Zeitpunkt als zeitzonenbewussten UTC-Wert."""
    return datetime.now(UTC)


def today() -> date:
    """Liefert den heutigen Kalendertag (UTC) als reines Datum."""
    return utc_now().date()
