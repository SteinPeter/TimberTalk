# Die Logik des Features „Änderungsprotokoll“ als einfache Funktionen.
# record() schreibt einen Eintrag (aufgerufen von middleware.py), list_events() liest sie.

import json
from datetime import UTC, datetime

from sqlmodel import Session, col, select

from timbertalk.features.audit.models import AuditEvent

# So viele Einträge zeigt die Liste höchstens.
LIST_LIMIT = 300

# Lange Werte (z. B. ein Logo als Bild-Text) werden gekürzt, Passwörter nie gespeichert.
MAX_VALUE_LENGTH = 80
SECRET_WORDS = ("password", "token", "secret")


def describe_body(body: bytes) -> str:
    """Die gesendeten Angaben als lesbare Zeile – ohne Passwörter, lange Werte gekürzt."""
    if not body:
        return ""
    try:
        data = json.loads(body)
    except (UnicodeDecodeError, ValueError):
        return ""
    if not isinstance(data, dict):
        return _short(json.dumps(data, ensure_ascii=False))
    parts = []
    for key, value in data.items():
        if any(word in key.lower() for word in SECRET_WORDS):
            value = "•••"
        elif not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False)
        parts.append(f"{key}: {_short(value)}")
    return " · ".join(parts)


def _short(text: str) -> str:
    return text if len(text) <= MAX_VALUE_LENGTH else text[:MAX_VALUE_LENGTH] + "… (gekürzt)"


def describe_target(path_params: dict) -> str:
    """Welcher Datensatz: aus {"material_id": 3} wird „Nr. 3“, aus mehreren „role: … · …“."""
    if not path_params:
        return ""
    if len(path_params) == 1:
        return f"Nr. {next(iter(path_params.values()))}"
    return " · ".join(f"{key}: {value}" for key, value in path_params.items())


def record(
    session: Session,
    *,
    account_id: int | None,
    account_name: str,
    area: str,
    action: str,
    target: str,
    details: str,
    method: str,
    path: str,
) -> None:
    """Schreibt einen Eintrag ins Protokoll."""
    session.add(
        AuditEvent(
            created_at=datetime.now(UTC),
            account_id=account_id,
            account_name=account_name,
            area=area,
            action=action,
            target=target,
            details=details,
            method=method,
            path=path,
        )
    )
    session.commit()


def list_events(session: Session, area: str | None = None) -> list[AuditEvent]:
    """Die neuesten Einträge zuerst, wahlweise nur ein Bereich."""
    statement = select(AuditEvent).order_by(
        col(AuditEvent.created_at).desc(), col(AuditEvent.id).desc()
    )
    if area:
        statement = statement.where(AuditEvent.area == area)
    return list(session.exec(statement.limit(LIST_LIMIT)))


def list_areas(session: Session) -> list[str]:
    """Alle Bereiche, die im Protokoll vorkommen – für die Auswahl in der Oberfläche."""
    statement = select(AuditEvent.area).distinct().order_by(AuditEvent.area)
    return list(session.exec(statement))
