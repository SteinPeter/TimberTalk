"""Eigene Spaltentypen: zeitlich sortierbare UUIDs sowie verlustfreie Geld- und Mengenwerte.

Geld und Mengen werden niemals als `float` geführt. In Python sind sie immer `Decimal`,
in der Datenbank auf SQLite als TEXT (zeichengenau, also verlustfrei inklusive Nachkommastellen)
und auf Postgres als NUMERIC. Auf Postgres wird die Skala auf `SCALE` Nachkommastellen
normalisiert; der Zahlenwert bleibt identisch, nur angehängte Nullen können sich ändern.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, ClassVar

import uuid_utils
from sqlalchemy import CHAR, DateTime, Dialect, Numeric, Text
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import TypeDecorator

MAX_PRECISION = 18
"""Gesamtzahl der Stellen, die auf Postgres in NUMERIC passen muss."""

MAX_SCALE = 6
"""Zulässige Nachkommastellen für Geld- und Mengenwerte."""

MONEY_SCALE = Decimal(1).scaleb(-MAX_SCALE)
"""Kleinste Einheit, die eine Geld- oder Mengenspalte darstellen kann (0.000001)."""

MAX_INTEGER_DIGITS = MAX_PRECISION - MAX_SCALE
"""Zulässige Stellen vor dem Komma bei Geld- und Mengenwerten."""


def uuid7() -> uuid.UUID:
    """Erzeugt eine zeitlich sortierbare UUID der Version 7 (RFC 9562)."""
    return uuid.UUID(bytes=uuid_utils.uuid7().bytes)


def new_id() -> uuid.UUID:
    """Liefert die Vorgabe-Kennung für neue Datensätze (UUIDv7)."""
    return uuid7()


class GUID(TypeDecorator[uuid.UUID]):
    """UUID-Spalte: nativ auf Postgres, als 36-Zeichen-Text auf allen anderen Datenbanken."""

    impl = CHAR(36)
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value: Any, dialect: Dialect) -> Any:
        if value is None:
            return None
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(str(value))
        if dialect.name == "postgresql":
            return value
        return str(value)

    def process_result_value(self, value: Any, dialect: Dialect) -> uuid.UUID | None:
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


class UtcDateTime(TypeDecorator[datetime]):
    """Zeitstempel-Spalte: speichert immer UTC und liest immer zeitzonenbewusst zurück.

    SQLite kennt keine Zeitzonen. Darum wird beim Schreiben nach UTC umgerechnet und
    beim Lesen die UTC-Zeitzone wieder angehängt, damit nie ein naiver Zeitstempel
    in die Anwendung gelangt.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if not isinstance(value, datetime):
            raise ValueError(f"Zeitstempel erwartet, nicht {type(value).__name__}.")
        if value.tzinfo is None:
            raise ValueError("Zeitstempel ohne Zeitzone sind nicht erlaubt; bitte UTC verwenden.")
        return value.astimezone(UTC)

    def process_result_value(self, value: Any, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if not isinstance(value, datetime):
            raise ValueError(f"Zeitstempel erwartet, nicht {type(value).__name__}.")
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


def to_decimal(value: Any, *, field: str = "Wert") -> Decimal:
    """Wandelt eine Eingabe verlustfrei in `Decimal`; `float` wird abgelehnt.

    Parameter:
        value: Zahl als `Decimal`, `int` oder Zeichenkette.
        field: Feldname für die Fehlermeldung.
    """
    if isinstance(value, Decimal):
        decimal_value = value
    elif isinstance(value, bool):
        raise ValueError(f"{field}: Wahrheitswert ist kein gültiger Zahlenwert.")
    elif isinstance(value, int):
        decimal_value = Decimal(value)
    elif isinstance(value, str):
        try:
            decimal_value = Decimal(value.strip().replace(",", "."))
        except InvalidOperation as exc:
            raise ValueError(f"{field}: '{value}' ist keine gültige Dezimalzahl.") from exc
    elif isinstance(value, float):
        raise ValueError(
            f"{field}: Gleitkommazahlen sind für Geld und Mengen nicht erlaubt. "
            "Bitte Decimal oder Zeichenkette verwenden."
        )
    else:
        raise ValueError(f"{field}: Typ {type(value).__name__} ist kein gültiger Zahlenwert.")

    if not decimal_value.is_finite():
        raise ValueError(f"{field}: Unendliche Werte oder NaN sind nicht erlaubt.")
    return decimal_value


def quantize_money(value: Decimal) -> Decimal:
    """Rundet einen gerechneten Geldbetrag kaufmännisch auf `MAX_SCALE` Nachkommastellen.

    Eine Multiplikation addiert die Nachkommastellen beider Werte: Menge mal Preis
    hat also leicht mehr Stellen, als eine Geldspalte und die Schemas zulassen.
    Gerechnete Beträge laufen darum immer über diese Funktion.

    Parameter:
        value: der gerechnete Betrag.
    """
    return value.quantize(MONEY_SCALE, rounding=ROUND_HALF_UP)


class _DecimalAsText(TypeDecorator[Decimal]):
    """Gemeinsame Grundlage für Geld- und Mengenspalten."""

    impl = Text
    cache_ok = True

    precision: ClassVar[int] = MAX_PRECISION
    scale: ClassVar[int] = MAX_SCALE
    label: ClassVar[str] = "Wert"

    def load_dialect_impl(self, dialect: Dialect) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Numeric(precision=self.precision, scale=self.scale))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: Any, dialect: Dialect) -> Any:
        if value is None:
            return None
        decimal_value = to_decimal(value, field=self.label)
        exponent = decimal_value.as_tuple().exponent
        decimals = -int(exponent) if isinstance(exponent, int) and exponent < 0 else 0
        if decimals > self.scale:
            raise ValueError(
                f"{self.label}: höchstens {self.scale} Nachkommastellen erlaubt, "
                f"'{decimal_value}' hat {decimals}."
            )
        digits = len(decimal_value.as_tuple().digits)
        if digits - decimals > self.precision - self.scale:
            raise ValueError(f"{self.label}: '{decimal_value}' hat zu viele Stellen vor dem Komma.")
        if dialect.name == "postgresql":
            return decimal_value
        return format(decimal_value, "f")

    def process_result_value(self, value: Any, dialect: Dialect) -> Decimal | None:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))


class Money(_DecimalAsText):
    """Geldbetrag als `Decimal`; verlustfrei auf SQLite, NUMERIC auf Postgres."""

    cache_ok = True
    label = "Geldbetrag"


class Quantity(_DecimalAsText):
    """Menge als `Decimal` (Stunden, Kilometer, Kubikmeter, Prozent …)."""

    cache_ok = True
    label = "Menge"
