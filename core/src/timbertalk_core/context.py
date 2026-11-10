"""Aufrufkontext der Service-Schicht; unabhängig von FastAPI und MCP."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

from timbertalk_core.db.audit import CONTEXT_KEY
from timbertalk_core.errors import PermissionDenied

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class ActorType(StrEnum):
    """Art des Akteurs, der eine Operation auslöst."""

    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


class Source(StrEnum):
    """Herkunft eines Datensatzes oder Aufrufs."""

    MANUAL = "manual"
    AGENT = "agent"
    VOICE = "voice"
    IMPORT = "import"
    CAD = "cad"
    SYSTEM = "system"


@dataclass(slots=True)
class ServiceContext:
    """Akteur, Quelle und Session eines Service-Aufrufs; Grundlage des Audit-Logs.

    Parameter:
        session: offene SQLAlchemy-Session, in der die Operation arbeitet.
        actor_id: Kennung des Akteurs (Mitarbeiter, Agent oder System).
        actor_type: Art des Akteurs (`user`, `agent`, `system`).
        source: Herkunft des Aufrufs (`manual`, `agent`, `voice`, `import`, `cad`, `system`).
        correlation_id: Kennung zur Verknüpfung zusammengehöriger Vorgänge.
    """

    session: Session
    actor_id: uuid.UUID | None = None
    actor_type: ActorType = ActorType.SYSTEM
    source: Source = Source.SYSTEM
    correlation_id: uuid.UUID = field(default_factory=uuid.uuid4)
    action_hint: str | None = None
    """Fachliche Aktion für das Audit-Log (z. B. `confirm`); wird zentral ausgewertet."""

    def __post_init__(self) -> None:
        self.bind()

    def bind(self) -> ServiceContext:
        """Macht diesen Kontext für die Session maßgeblich und liefert ihn zurück.

        Das Änderungsprotokoll liest den Kontext beim Flush aus der Session. Teilen
        sich mehrere Kontexte eine Session – etwa ein Import und ein bestätigender
        Mensch –, muss der gerade handelnde Kontext gebunden sein, sonst landet die
        Änderung unter dem falschen Akteur.
        """
        self.session.info[CONTEXT_KEY] = self
        return self

    def flush(self) -> None:
        """Bindet den Kontext und schreibt die offenen Änderungen in die Datenbank.

        Services rufen immer diese Methode statt `session.flush()`, damit das
        Änderungsprotokoll den tatsächlich handelnden Akteur festhält.
        """
        self.bind()
        self.session.flush()

    def require_human(self, operation_de: str) -> None:
        """Stellt sicher, dass ein Mensch handelt; sonst `PermissionDenied`.

        Parameter:
            operation_de: deutsche Bezeichnung des Vorgangs für die Fehlermeldung.
        """
        if self.actor_type is not ActorType.USER:
            raise PermissionDenied(
                f"{operation_de} ist nur durch einen Menschen erlaubt, "
                f"nicht durch Akteur-Typ '{self.actor_type.value}'.",
                actor_type=self.actor_type.value,
            )

    def with_action(self, action: str) -> ServiceContext:
        """Setzt die fachliche Aktion für das Audit-Log und liefert den Kontext zurück."""
        self.action_hint = action
        return self
