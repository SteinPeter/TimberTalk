"""Abhängigkeiten der API: Session, Akteur und Schlüsselprüfung.

Die Authentifizierung ist bewusst ein Platzhalter: ein fester Schlüssel aus `.env`
und der Akteur aus Kopfzeilen. Die Service-Schicht arbeitet trotzdem schon mit
einem vollständigen `ServiceContext`, damit eine echte Anmeldung später nur diese
Stelle ersetzt.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from timbertalk_core.config import Settings, get_settings
from timbertalk_core.context import ActorType, ServiceContext, Source
from timbertalk_core.errors import PermissionDenied, ValidationFailed

API_KEY_HEADER = "X-API-Key"
ACTOR_HEADER = "X-Actor"
ACTOR_TYPE_HEADER = "X-Actor-Type"
SOURCE_HEADER = "X-Source"
CORRELATION_HEADER = "X-Correlation-Id"


def settings_dep(request: Request) -> Settings:
    """Liefert die Einstellungen dieser Anwendung.

    Die Anwendung legt ihre Einstellungen beim Start in `app.state` ab. Dadurch
    arbeiten Tests und abweichende Installationen mit ihren eigenen Werten statt
    mit denen des Prozesses.
    """
    aus_app = getattr(request.app.state, "settings", None)
    if isinstance(aus_app, Settings):
        return aus_app
    return get_settings()


def require_api_key(
    settings: Annotated[Settings, Depends(settings_dep)],
    x_api_key: Annotated[str | None, Header(alias=API_KEY_HEADER)] = None,
) -> None:
    """Prüft den Platzhalter-Schlüssel aus `.env`.

    Parameter:
        settings: Einstellungen mit dem erwarteten Schlüssel.
        x_api_key: Schlüssel aus der Kopfzeile `X-API-Key`.
    """
    if not settings.api_key or x_api_key != settings.api_key:
        raise PermissionDenied("Der API-Schlüssel fehlt oder ist falsch; bitte Kopfzeile X-API-Key setzen.")


def get_session(request: Request) -> Iterator[Session]:
    """Stellt eine Session bereit und schreibt bzw. verwirft die Transaktion am Ende."""
    factory = request.app.state.session_factory
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _parse_uuid(value: str | None, feld: str) -> uuid.UUID | None:
    if value is None or not value.strip():
        return None
    try:
        return uuid.UUID(value.strip())
    except ValueError as exc:
        raise ValidationFailed(
            f"Die Kopfzeile {feld} muss eine UUID enthalten.",
            errors={feld: "keine gültige UUID"},
        ) from exc


def get_context(
    session: Annotated[Session, Depends(get_session)],
    x_actor: Annotated[str | None, Header(alias=ACTOR_HEADER)] = None,
    x_actor_type: Annotated[str | None, Header(alias=ACTOR_TYPE_HEADER)] = None,
    x_source: Annotated[str | None, Header(alias=SOURCE_HEADER)] = None,
    x_correlation_id: Annotated[str | None, Header(alias=CORRELATION_HEADER)] = None,
) -> ServiceContext:
    """Baut den Aufrufkontext aus den Kopfzeilen der Anfrage.

    Parameter:
        session: offene Session der Anfrage.
        x_actor: Kennung des Akteurs (UUID) aus `X-Actor`.
        x_actor_type: Art des Akteurs (`user`, `agent`, `system`) aus `X-Actor-Type`.
        x_source: Herkunft des Aufrufs aus `X-Source`.
        x_correlation_id: Korrelations-Kennung aus `X-Correlation-Id`.
    """
    try:
        actor_type = ActorType(x_actor_type) if x_actor_type else ActorType.USER
    except ValueError as exc:
        raise ValidationFailed(
            f"Unbekannte Akteur-Art '{x_actor_type}'; erlaubt sind user, agent oder system.",
            errors={ACTOR_TYPE_HEADER: "unbekannte Akteur-Art"},
        ) from exc
    try:
        source = Source(x_source) if x_source else Source.MANUAL
    except ValueError as exc:
        raise ValidationFailed(
            f"Unbekannte Quelle '{x_source}'; erlaubt sind manual, agent, voice, import, cad oder system.",
            errors={SOURCE_HEADER: "unbekannte Quelle"},
        ) from exc

    return ServiceContext(
        session=session,
        actor_id=_parse_uuid(x_actor, ACTOR_HEADER),
        actor_type=actor_type,
        source=source,
        correlation_id=_parse_uuid(x_correlation_id, CORRELATION_HEADER) or uuid.uuid4(),
    )


Context = Annotated[ServiceContext, Depends(get_context)]
"""Abkürzung für den Aufrufkontext in Routen."""

ApiKey = Annotated[None, Depends(require_api_key)]
"""Abkürzung für die Schlüsselprüfung in Routen."""
