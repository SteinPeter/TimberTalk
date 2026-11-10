"""Prüft die eigenen Spaltentypen: UUIDv7, Money und Quantity."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import Engine, MetaData, String, create_engine, select, text
from sqlalchemy.dialects.sqlite import dialect as sqlite_dialect
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from timbertalk_core.db.base import NAMING_CONVENTION
from timbertalk_core.db.mixins import EntityMixin
from timbertalk_core.db.types import Money, Quantity, UtcDateTime, to_decimal, uuid7

SQLITE_DIALECT = sqlite_dialect()


class SampleBase(DeclarativeBase):
    """Eigene Basis, damit Test-Tabellen nicht in `Base.metadata` des Backends landen."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Sample(EntityMixin, SampleBase):
    """Nur für Tests: Tabelle mit Geld- und Mengenspalte."""

    __tablename__ = "sample_values"

    label: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(Money(), nullable=True)
    qty: Mapped[Decimal | None] = mapped_column(Quantity(), nullable=True)


@pytest.fixture
def engine() -> Iterator[Engine]:
    db = create_engine("sqlite+pysqlite:///:memory:")
    Sample.__table__.create(db)
    yield db
    db.dispose()


@pytest.mark.parametrize(
    "raw",
    ["489.5000", "0.30", "0", "1", "-12.345678", "999999999999.123456", "0.000001"],
)
def test_decimal_rundreise_ist_verlustfrei(engine: Engine, raw: str) -> None:
    value = Decimal(raw)
    with Session(engine) as session:
        row = Sample(label="rundreise", amount=value, qty=value)
        session.add(row)
        session.commit()
        row_id = row.id

    with Session(engine) as session:
        loaded = session.get(Sample, row_id)
        assert loaded is not None
        assert loaded.amount == value
        assert loaded.qty == value
        # Auf SQLite bleibt auch die Anzahl der Nachkommastellen erhalten.
        assert str(loaded.amount) == raw
        assert str(loaded.qty) == raw


def test_sqlite_speichert_als_text(engine: Engine) -> None:
    with Session(engine) as session:
        session.add(Sample(label="text", amount=Decimal("489.5000")))
        session.commit()
    with engine.connect() as connection:
        stored = connection.execute(text("SELECT typeof(amount), amount FROM sample_values")).one()
    assert stored[0] == "text"
    assert stored[1] == "489.5000"


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (1.5, "Gleitkommazahlen"),
        (Decimal("1.1234567"), "Nachkommastellen"),
        (Decimal("1234567890123.0"), "vor dem Komma"),
    ],
)
def test_ungueltige_geldwerte_werden_abgelehnt(value: object, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        Money().process_bind_param(value, SQLITE_DIALECT)


def test_ungueltiger_wert_scheitert_auch_ueber_die_session(engine: Engine) -> None:
    with Session(engine) as session, pytest.raises(StatementError, match="Gleitkommazahlen"):
        session.add(Sample(label="float", amount=1.5))  # type: ignore[arg-type]
        session.commit()


def test_zeitstempel_ohne_zeitzone_wird_abgelehnt() -> None:
    with pytest.raises(ValueError, match="ohne Zeitzone"):
        UtcDateTime().process_bind_param(datetime(2026, 1, 1, 12, 0), SQLITE_DIALECT)  # noqa: DTZ001
    with pytest.raises(ValueError, match="Zeitstempel erwartet"):
        UtcDateTime().process_bind_param("2026-01-01", SQLITE_DIALECT)


def test_zeitstempel_wird_nach_utc_umgerechnet() -> None:
    berlin_noon = datetime(2026, 7, 1, 14, 0, tzinfo=timezone(timedelta(hours=2)))
    stored = UtcDateTime().process_bind_param(berlin_noon, SQLITE_DIALECT)
    assert stored == datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    naive_from_db = datetime(2026, 7, 1, 12, 0)  # noqa: DTZ001
    assert UtcDateTime().process_result_value(naive_from_db, SQLITE_DIALECT) == berlin_noon


def test_to_decimal_akzeptiert_komma_und_ganzzahl() -> None:
    assert to_decimal("12,50") == Decimal("12.50")
    assert to_decimal(7) == Decimal("7")
    with pytest.raises(ValueError, match="gültige Dezimalzahl"):
        to_decimal("keine zahl")
    with pytest.raises(ValueError, match="Wahrheitswert"):
        to_decimal(True)
    with pytest.raises(ValueError, match="NaN"):
        to_decimal(Decimal("NaN"))


def test_uuid7_ist_zeitlich_sortierbar() -> None:
    ids = [uuid7() for _ in range(200)]
    assert all(i.version == 7 for i in ids)
    assert ids == sorted(ids)
    assert len(set(ids)) == len(ids)


def test_guid_rundreise(engine: Engine) -> None:
    with Session(engine) as session:
        row = Sample(label="guid")
        session.add(row)
        session.commit()
        row_id = row.id
    assert isinstance(row_id, uuid.UUID)
    with Session(engine) as session:
        loaded = session.scalar(select(Sample).where(Sample.id == row_id))
        assert loaded is not None
        assert loaded.id == row_id
        assert loaded.version == 1
        assert loaded.deleted_at is None
        assert loaded.created_at.tzinfo is not None
