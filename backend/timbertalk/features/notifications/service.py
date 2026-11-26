# Die Logik des Features „Mitteilungen“ als einfache Funktionen.
# Andere Features rufen notify() auf, um Personen etwas mitzuteilen.

from collections.abc import Iterable
from datetime import UTC, datetime

from sqlmodel import Session, col, func, select, update

from timbertalk.features.notifications.models import Notification

# So viele Mitteilungen zeigt die Liste höchstens (die neuesten zuerst).
LIST_LIMIT = 30


def notify(session: Session, account_ids: Iterable[int], text: str) -> None:
    """Schickt text an jede Person in account_ids (doppelte nur einmal)."""
    now = datetime.now(UTC)
    for account_id in dict.fromkeys(account_ids):
        session.add(Notification(account_id=account_id, text=text, created_at=now))
    session.commit()


def list_notifications(session: Session, account_id: int) -> list[Notification]:
    """Die neuesten Mitteilungen einer Person, gelesene und ungelesene."""
    statement = (
        select(Notification)
        .where(Notification.account_id == account_id)
        .order_by(col(Notification.created_at).desc(), col(Notification.id).desc())
        .limit(LIST_LIMIT)
    )
    return list(session.exec(statement))


def unread_count(session: Session, account_id: int) -> int:
    statement = select(func.count()).where(
        Notification.account_id == account_id, col(Notification.read_at).is_(None)
    )
    return session.exec(statement).one()


def mark_all_read(session: Session, account_id: int) -> None:
    """Markiert alle Mitteilungen einer Person als gelesen."""
    session.exec(
        update(Notification)
        .where(Notification.account_id == account_id, col(Notification.read_at).is_(None))
        .values(read_at=datetime.now(UTC))
    )
    session.commit()
