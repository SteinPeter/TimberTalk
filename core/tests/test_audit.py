"""Prüft die zentrale Erzeugung der Audit-Einträge."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import Engine, MetaData, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from timbertalk_core.clock import utc_now
from timbertalk_core.context import ActorType, ServiceContext, Source
from timbertalk_core.db.base import NAMING_CONVENTION
from timbertalk_core.db.metadata import get_metadata
from timbertalk_core.db.mixins import EntityMixin
from timbertalk_core.db.session import create_session_factory
from timbertalk_core.db.types import Money
from timbertalk_core.domain.audit.models import AuditEvent


class ProbeBase(DeclarativeBase):
    """Eigene Basis, damit Test-Tabellen nicht in `Base.metadata` des Backends landen."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class AuditProbe(EntityMixin, ProbeBase):
    """Nur für Tests: einfache Entität, an der das Protokoll geprüft wird."""

    __tablename__ = "audit_probes"

    label: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(Money(), nullable=True)


@pytest.fixture(autouse=True)
def probe_tabelle(engine: Engine) -> None:
    """Legt die Test-Tabelle in der Testdatenbank an."""
    ProbeBase.metadata.create_all(engine)


def _events(session: Session) -> list[AuditEvent]:
    return list(session.scalars(select(AuditEvent).order_by(AuditEvent.occurred_at, AuditEvent.id)))


def test_anlegen_erzeugt_genau_einen_eintrag(ctx: ServiceContext) -> None:
    probe = AuditProbe(label="Dachgaube", amount=Decimal("1200.5000"))
    ctx.session.add(probe)
    ctx.session.commit()

    events = _events(ctx.session)
    assert len(events) == 1
    event = events[0]
    assert event.action == "create"
    assert event.entity_type == "audit_probes"
    assert event.entity_id == probe.id
    assert event.actor_type == ActorType.USER.value
    assert event.actor_id == ctx.actor_id
    assert event.source == Source.MANUAL.value
    assert event.correlation_id == ctx.correlation_id
    assert event.changes["label"] == {"old": None, "new": "Dachgaube"}
    assert event.changes["amount"] == {"old": None, "new": "1200.5000"}
    assert "version" not in event.changes


def test_aendern_protokolliert_nur_geaenderte_felder(ctx: ServiceContext) -> None:
    probe = AuditProbe(label="Carport")
    ctx.session.add(probe)
    ctx.session.commit()

    probe.label = "Carport groß"
    ctx.session.commit()

    events = _events(ctx.session)
    assert [e.action for e in events] == ["create", "update"]
    assert events[1].changes == {"label": {"old": "Carport", "new": "Carport groß"}}
    assert probe.version == 2


def test_ohne_aenderung_kein_eintrag(ctx: ServiceContext) -> None:
    probe = AuditProbe(label="unverändert")
    ctx.session.add(probe)
    ctx.session.commit()

    probe.label = "unverändert"
    ctx.session.commit()

    assert [e.action for e in _events(ctx.session)] == ["create"]


def test_soft_delete_wird_als_delete_protokolliert(ctx: ServiceContext) -> None:
    probe = AuditProbe(label="zu löschen")
    ctx.session.add(probe)
    ctx.session.commit()

    probe.deleted_at = utc_now()
    ctx.session.commit()

    events = _events(ctx.session)
    assert [e.action for e in events] == ["create", "delete"]
    assert events[1].changes["deleted_at"]["old"] is None


def test_fachliche_aktion_wird_uebernommen(ctx: ServiceContext) -> None:
    probe = AuditProbe(label="Buchung")
    ctx.session.add(probe)
    ctx.session.commit()

    probe.label = "Buchung bestätigt"
    ctx.with_action("confirm")
    ctx.session.commit()

    events = _events(ctx.session)
    assert [e.action for e in events] == ["create", "confirm"]
    assert ctx.action_hint is None


def test_mehrere_entitaeten_ergeben_mehrere_eintraege(ctx: ServiceContext) -> None:
    ctx.session.add_all([AuditProbe(label="a"), AuditProbe(label="b")])
    ctx.session.commit()
    assert len(_events(ctx.session)) == 2


def test_schreiben_ohne_kontext_wird_abgelehnt(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        session.add(AuditProbe(label="ohne Kontext"))
        with pytest.raises(RuntimeError, match="ohne ServiceContext"):
            session.commit()


def test_audit_eintraege_erzeugen_keine_eigenen_eintraege(ctx: ServiceContext) -> None:
    ctx.session.add(AuditProbe(label="einmalig"))
    ctx.session.commit()
    ctx.session.commit()
    assert len(_events(ctx.session)) == 1


def test_viele_fabriken_hintereinander_protokollieren_weiter() -> None:
    """Jede neue Session-Fabrik muss protokollieren, auch wenn alte eingesammelt wurden.

    SQLAlchemy verwaltet Ereignis-Ziele anhand der Objekt-Kennung. Wird eine alte
    Fabrik freigegeben und eine neue an derselben Speicheradresse angelegt, darf das
    Protokoll nicht still ausfallen.
    """
    import gc

    for _ in range(40):
        db = create_engine(
            "sqlite+pysqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        get_metadata().create_all(db)
        ProbeBase.metadata.create_all(db)
        factory = create_session_factory(db)
        with factory() as session:
            context = ServiceContext(session=session, actor_type=ActorType.USER)
            session.add(AuditProbe(label="Fabrik"))
            session.commit()
            assert [event.action for event in _events(session)] == ["create"], (
                "Das Änderungsprotokoll ist still ausgefallen"
            )
            assert context.session is session
        db.dispose()
        del factory, db
        gc.collect()


def test_kontext_haengt_sich_an_die_session(engine: Engine) -> None:
    from timbertalk_core.db.audit import CONTEXT_KEY

    with Session(engine) as session:
        context = ServiceContext(session=session)
        assert session.info[CONTEXT_KEY] is context
