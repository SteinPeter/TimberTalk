"""Prüft ServiceContext und die fachlichen Fehler."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from timbertalk_core.context import ActorType, ServiceContext, Source
from timbertalk_core.errors import (
    Conflict,
    InvalidState,
    NotFound,
    PermissionDenied,
    TimberTalkError,
    ValidationFailed,
)


def test_require_human_erlaubt_nur_benutzer(session: Session) -> None:
    human = ServiceContext(session=session, actor_type=ActorType.USER)
    human.require_human("Bestätigen")

    for actor_type in (ActorType.AGENT, ActorType.SYSTEM):
        context = ServiceContext(session=session, actor_type=actor_type)
        with pytest.raises(PermissionDenied, match="nur durch einen Menschen"):
            context.require_human("Bestätigen")


def test_standardwerte_des_kontexts(session: Session) -> None:
    context = ServiceContext(session=session)
    assert context.actor_type is ActorType.SYSTEM
    assert context.source is Source.SYSTEM
    assert isinstance(context.correlation_id, uuid.UUID)
    assert context.action_hint is None


def test_not_found_nennt_entitaet_und_kennung() -> None:
    entity_id = uuid.uuid4()
    error = NotFound.for_entity("Projekt", entity_id)
    assert "Projekt" in str(error)
    assert str(entity_id) in str(error)
    assert error.details["entity_type"] == "Projekt"
    assert error.http_status == 404


@pytest.mark.parametrize(
    ("error", "code", "status"),
    [
        (Conflict("doppelt"), "conflict", 409),
        (InvalidState("gesperrt"), "invalid_state", 409),
        (ValidationFailed("ungültig"), "validation_failed", 422),
        (PermissionDenied("verboten"), "permission_denied", 403),
    ],
)
def test_fehlercodes_und_status(error: TimberTalkError, code: str, status: int) -> None:
    assert isinstance(error, TimberTalkError)
    assert error.code == code
    assert error.http_status == status


def test_validation_failed_traegt_feldfehler() -> None:
    error = ValidationFailed("ungültig", errors={"zip": "Postleitzahl fehlt"}, entity_type="customers")
    assert error.errors == {"zip": "Postleitzahl fehlt"}
    assert error.details["entity_type"] == "customers"
