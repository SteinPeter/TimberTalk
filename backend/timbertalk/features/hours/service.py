# Die Logik des Features „Stunden buchen“ (F4) als einfache Funktionen.
# Fehler: ValueError – die Angabe passt nicht (422), LookupError – gibt es nicht (404),
# PermissionError – das darf diese Person nicht (403).
# Kalender (F8) und Konten (F10) werden nur über deren service.py benutzt.

from datetime import UTC, date, datetime, time
from decimal import ROUND_HALF_UP, Decimal

from sqlmodel import Session, col, select

from timbertalk.features.accounts import service as accounts
from timbertalk.features.hours.models import HoursEntry, HoursIn, HoursInfo, Suggestion
from timbertalk.features.planning import service as planning
from timbertalk.features.planning.models import ABSENCE_KINDS

# Ohne Uhrzeit im Kalender schlagen wir einen normalen Arbeitstag vor.
DEFAULT_DAY_MINUTES = 8 * 60
# Gesetzliche Pause (Arbeitszeitgesetz §4): ab 6 Stunden 30 Minuten, ab 9 Stunden 45 Minuten.
BREAKS = [(9 * 60, 45), (6 * 60, 30)]
MAX_MINUTES_PER_ENTRY = 16 * 60
MAX_RANGE_DAYS = 62


def to_hours(minutes: int) -> Decimal:
    """Minuten als Stunden mit zwei Nachkommastellen, z. B. 450 → 7.50."""
    return (Decimal(minutes) / 60).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def to_minutes(hours: Decimal) -> int:
    """Stunden als ganze Minuten, z. B. 7.5 → 450."""
    return int((hours * 60).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def working_minutes(start: time, end: time) -> int:
    """Arbeitszeit zwischen Beginn und Ende, abzüglich der gesetzlichen Pause."""
    total = (end.hour * 60 + end.minute) - (start.hour * 60 + start.minute)
    for threshold, pause in BREAKS:
        if total > threshold:
            return total - pause
    return total


# --- Vorschläge aus dem Kalender ----------------------------------------------------


def suggestions(session: Session, account_id: int, day: date) -> list[Suggestion]:
    """Was diese Person laut Kalender an diesem Tag gearbeitet hat – ohne Urlaub, krank, Schule."""
    booked = set(
        session.exec(
            select(HoursEntry.calendar_entry_id).where(
                HoursEntry.account_id == account_id, HoursEntry.work_date == day
            )
        )
    )
    result = []
    for entry in planning.list_entries(session, day, day, account_id, view_all=False):
        if entry.kind in ABSENCE_KINDS:
            continue
        if entry.start_time is not None:
            minutes = working_minutes(entry.start_time, entry.end_time)
            span = f"{entry.start_time:%H:%M}–{entry.end_time:%H:%M}"
        else:
            minutes = DEFAULT_DAY_MINUTES
            span = "ganzer Tag"
        result.append(
            Suggestion(
                calendar_entry_id=entry.id,
                title=entry.title,
                project_id=entry.project_id,
                hours=to_hours(minutes),
                time=span,
                booked=entry.id in booked,
            )
        )
    return result


# --- Buchen ---------------------------------------------------------------------


def book(session: Session, data: HoursIn, acting_id: int, may_manage: bool) -> HoursInfo:
    """Bucht Stunden – für sich selbst oder, mit „hours.manage“, für jemand anderen."""
    entry = _new_entry(session, data, acting_id, may_manage)
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return _info(entry, _names(session))


def confirm_day(
    session: Session, items: list[HoursIn], acting_id: int, may_manage: bool
) -> list[HoursInfo]:
    """Bucht mehrere Vorschläge auf einmal – alle oder keiner (bei einem Fehler gar nichts)."""
    if not items:
        raise ValueError("Bitte mindestens einen Eintrag auswählen.")
    entries = [_new_entry(session, item, acting_id, may_manage) for item in items]
    for entry in entries:
        session.add(entry)
    session.commit()
    names = _names(session)
    for entry in entries:
        session.refresh(entry)
    return [_info(entry, names) for entry in entries]


def _new_entry(session: Session, data: HoursIn, acting_id: int, may_manage: bool) -> HoursEntry:
    account_id = data.account_id or acting_id
    if account_id != acting_id and not may_manage:
        raise PermissionError("Stunden für andere bucht nur, wer „Stunden für andere buchen“ darf.")
    if account_id not in _names(session):
        raise ValueError(f"Die Person {account_id} gibt es nicht oder sie ist gesperrt.")
    if not data.hours.is_finite() or data.hours <= 0:
        raise ValueError("Bitte die Stunden als Zahl größer als 0 angeben, z. B. 7,5.")
    minutes = to_minutes(data.hours)
    if minutes > MAX_MINUTES_PER_ENTRY:
        raise ValueError("Mehr als 16 Stunden in einem Eintrag gehen nicht.")
    if data.project_id is not None and data.project_id < 1:
        raise ValueError("Die Projektnummer muss eine positive Zahl sein.")
    title = data.title.strip()
    if not title and data.project_id is None:
        raise ValueError("Bitte angeben, wofür: Projektnummer oder kurze Beschreibung.")
    if data.calendar_entry_id is not None:
        duplicate = session.exec(
            select(HoursEntry).where(
                HoursEntry.account_id == account_id,
                HoursEntry.work_date == data.work_date,
                HoursEntry.calendar_entry_id == data.calendar_entry_id,
            )
        ).first()
        if duplicate is not None:
            raise ValueError(f"„{title or duplicate.title}“ ist für diesen Tag schon gebucht.")
    return HoursEntry(
        account_id=account_id,
        work_date=data.work_date,
        minutes=minutes,
        project_id=data.project_id,
        title=title,
        note=data.note.strip(),
        calendar_entry_id=data.calendar_entry_id,
        created_by=acting_id,
        created_at=datetime.now(UTC),
    )


def delete_hours(session: Session, hours_id: int, acting_id: int, may_manage: bool) -> None:
    """Löscht eine Buchung: die eigene – oder, mit „hours.manage“, jede."""
    entry = session.get(HoursEntry, hours_id)
    if entry is None or (entry.account_id != acting_id and not may_manage):
        raise LookupError(f"Die Buchung {hours_id} gibt es nicht.")
    session.delete(entry)
    session.commit()


# --- Lesen ----------------------------------------------------------------------


def _names(session: Session) -> dict[int, str]:
    return {person.id: person.display_name for person in accounts.list_people(session)}


def _info(entry: HoursEntry, names: dict[int, str]) -> HoursInfo:
    return HoursInfo(
        id=entry.id,
        account_id=entry.account_id,
        person=names.get(entry.account_id, f"Person {entry.account_id}"),
        work_date=entry.work_date,
        hours=to_hours(entry.minutes),
        project_id=entry.project_id,
        title=entry.title,
        note=entry.note,
    )


def list_hours(
    session: Session,
    start: date,
    end: date,
    viewer_id: int,
    view_all: bool,
    account_id: int | None = None,
) -> list[HoursInfo]:
    """Gebuchte Stunden im Zeitraum. Ohne view_all nur die eigenen, mit account_id eine Person."""
    if end < start:
        raise ValueError("Das Ende des Zeitraums liegt vor dem Anfang.")
    if (end - start).days > MAX_RANGE_DAYS:
        raise ValueError(f"Bitte höchstens {MAX_RANGE_DAYS} Tage auf einmal abfragen.")
    if not view_all:
        account_id = viewer_id
    statement = select(HoursEntry).where(HoursEntry.work_date >= start, HoursEntry.work_date <= end)
    if account_id is not None:
        statement = statement.where(HoursEntry.account_id == account_id)
    statement = statement.order_by(HoursEntry.work_date, col(HoursEntry.id))
    names = _names(session)
    return [_info(entry, names) for entry in session.exec(statement)]


def minutes_per_day(session: Session, account_id: int, start: date, end: date) -> dict[date, int]:
    """Gebuchte Minuten einer Person je Tag von start bis end – für das Stundenkonto (employees).

    Anders als list_hours() ohne Höchstdauer: Das Stundenkonto rechnet über ein ganzes Jahr.
    """
    statement = select(HoursEntry).where(
        HoursEntry.account_id == account_id,
        HoursEntry.work_date >= start,
        HoursEntry.work_date <= end,
    )
    totals: dict[date, int] = {}
    for entry in session.exec(statement):
        totals[entry.work_date] = totals.get(entry.work_date, 0) + entry.minutes
    return totals
