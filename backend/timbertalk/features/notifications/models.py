# Tabelle des Features „Mitteilungen“ als SQLModel-Klasse. Der Tabellenname beginnt mit
# `notifications_`.

from datetime import datetime

from sqlmodel import Field, SQLModel


class Notification(SQLModel, table=True):
    """Eine Mitteilung an eine Person (ein Konto aus F10)."""

    __tablename__ = "notifications_message"

    id: int | None = Field(default=None, primary_key=True)
    account_id: int = Field(index=True)  # an wen
    text: str
    link: str = ""  # wohin ein Klick führt, z. B. „#start“ (Dashboard); leer: nirgendwohin
    created_at: datetime
    read_at: datetime | None = None  # None: noch nicht gelesen


class NotificationTopic(SQLModel, table=True):
    """Worum es in einer Mitteilung geht, die eine Aufgabe ist – z. B. „absence-request:12“.

    Ist die Aufgabe erledigt (Antrag entschieden), löscht resolve() alle Mitteilungen mit diesem
    Thema bei allen Personen. Eine eigene Tabelle statt einer neuen Spalte, damit vorhandene
    Datenbanken ohne Migration weiterlaufen (Migrationen kommen erst mit F3).
    """

    __tablename__ = "notifications_topic"

    notification_id: int = Field(primary_key=True)
    topic: str = Field(index=True)


class UnreadCount(SQLModel):
    """Antwort: wie viele Mitteilungen noch ungelesen sind."""

    unread: int
