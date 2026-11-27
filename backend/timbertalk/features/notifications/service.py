# Die Logik des Features „Mitteilungen“ als einfache Funktionen.
# Andere Features rufen notify() auf, um Personen etwas mitzuteilen. Ist eine Mitteilung eine
# Aufgabe (z. B. „bitte Urlaubsantrag entscheiden“), bekommt sie ein Thema; ist die Aufgabe
# erledigt, entfernt resolve() sie bei allen. Andere Mitteilungen entfernt jede Person selbst.

from collections.abc import Iterable
from datetime import UTC, datetime

from sqlmodel import Session, col, delete, func, select, update

from timbertalk.features.notifications.models import Notification, NotificationTopic

# So viele Mitteilungen zeigt die Liste höchstens (die neuesten zuerst).
LIST_LIMIT = 30


def notify(
    session: Session, account_ids: Iterable[int], text: str, link: str = "", topic: str = ""
) -> None:
    """Schickt text an jede Person in account_ids (doppelte nur einmal).

    link: wohin ein Klick auf die Mitteilung führt, z. B. „#start“ für das Dashboard.
    topic: Thema einer Aufgabe, z. B. „absence-request:12“ – resolve(topic) entfernt sie wieder.
    """
    now = datetime.now(UTC)
    added = []
    for account_id in dict.fromkeys(account_ids):
        message = Notification(account_id=account_id, text=text, link=link, created_at=now)
        session.add(message)
        added.append(message)
    session.commit()
    if topic:
        for message in added:
            session.add(NotificationTopic(notification_id=message.id, topic=topic))
        session.commit()


def resolve(session: Session, topic: str) -> None:
    """Die Aufgabe topic ist erledigt: Ihre Mitteilungen verschwinden bei allen Personen."""
    ids = list(
        session.exec(
            select(NotificationTopic.notification_id).where(NotificationTopic.topic == topic)
        )
    )
    session.exec(delete(Notification).where(col(Notification.id).in_(ids)))
    session.exec(delete(NotificationTopic).where(NotificationTopic.topic == topic))
    session.commit()


def dismiss(session: Session, account_id: int, notification_id: int) -> None:
    """Entfernt eine eigene Mitteilung. Fremde oder unbekannte: LookupError."""
    message = session.get(Notification, notification_id)
    if message is None or message.account_id != account_id:
        raise LookupError(f"Die Mitteilung {notification_id} gibt es nicht.")
    session.delete(message)
    session.exec(
        delete(NotificationTopic).where(NotificationTopic.notification_id == notification_id)
    )
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
