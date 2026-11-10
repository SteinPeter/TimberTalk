"""Fachliche Fehler des Backends; die API bildet sie auf Problem-JSON ab."""

from __future__ import annotations

from typing import Any


class TimberTalkError(Exception):
    """Oberklasse aller fachlichen Fehler; trägt Code, deutsche Meldung und Details."""

    code = "error"
    http_status = 400

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = details

    def __str__(self) -> str:
        return self.message


class NotFound(TimberTalkError):
    """Der angeforderte Datensatz existiert nicht oder ist gelöscht."""

    code = "not_found"
    http_status = 404

    @classmethod
    def for_entity(cls, entity_type: str, entity_id: Any) -> NotFound:
        """Erzeugt den Fehler für eine Entität mit bekannter Kennung."""
        return cls(
            f"{entity_type} mit der Kennung {entity_id} wurde nicht gefunden.",
            entity_type=entity_type,
            entity_id=str(entity_id),
        )


class Conflict(TimberTalkError):
    """Der Vorgang widerspricht dem aktuellen Datenstand (Doppelung, Versionskonflikt)."""

    code = "conflict"
    http_status = 409


class InvalidState(TimberTalkError):
    """Der Vorgang ist im aktuellen Status nicht erlaubt (z. B. Buchung ist `locked`)."""

    code = "invalid_state"
    http_status = 409


class ValidationFailed(TimberTalkError):
    """Die Eingabe ist fachlich ungültig; `errors` nennt die betroffenen Felder."""

    code = "validation_failed"
    http_status = 422

    def __init__(self, message: str, errors: dict[str, str] | None = None, **details: Any) -> None:
        super().__init__(message, **details)
        self.errors: dict[str, str] = errors or {}


class PermissionDenied(TimberTalkError):
    """Der Akteur darf diesen Vorgang nicht ausführen (z. B. Bestätigen durch `agent`)."""

    code = "permission_denied"
    http_status = 403
