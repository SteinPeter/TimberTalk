# Die Logik des Features „Planung: Kalender je Mitarbeiter“ (F8) als einfache Funktionen:
# Termine eintragen, ändern, löschen und für einen Zeitraum lesen – für alle oder nur für sich
# selbst – und beim Einplanen auf Überschneidungen hinweisen.
#
# Jede Funktion bekommt als ersten Parameter die Datenbank-Sitzung: session: Session.
# Fehler: ValueError – die Angabe passt nicht (422), LookupError – gibt es nicht (404).
# Die Personen kommen aus F10 und nur über dessen service.py (list_people()).
# Wer ein-, aus- oder umgeplant wird, bekommt eine Mitteilung (Feature notifications) – außer der
# Person, die gerade plant.

from datetime import UTC, date, datetime

from sqlmodel import Session, col, delete, select

from timbertalk.features.accounts import service as accounts
from timbertalk.features.accounts.models import Person
from timbertalk.features.notifications import service as notifications
from timbertalk.features.planning.models import (
    ABSENCE_KINDS,
    KINDS,
    CalendarAssignment,
    CalendarEntry,
    EntryIn,
    EntryInfo,
    KindInfo,
    PersonRef,
    SavedEntry,
)

# Ein Termin dauert höchstens ein Jahr; gelesen werden höchstens zwei Monate auf einmal.
MAX_ENTRY_DAYS = 366
MAX_RANGE_DAYS = 62


def _format_date(day: date) -> str:
    return day.strftime("%d.%m.%Y")


_WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def _short_day(day: date) -> str:
    return f"{_WEEKDAYS[day.weekday()]} {day.strftime('%d.%m.')}"


def describe(entry: CalendarEntry) -> str:
    """Ein Termin in einer Zeile, z. B. „Carport Berger, Mo 30.11.–Mi 02.12., Potsdam“."""
    parts = [entry.title]
    days = _short_day(entry.start_date)
    if entry.end_date != entry.start_date:
        days += f"–{_short_day(entry.end_date)}"
    parts.append(days)
    if entry.start_time is not None:
        parts.append(f"{entry.start_time:%H:%M}–{entry.end_time:%H:%M} Uhr")
    if entry.location:
        parts.append(entry.location)
    return ", ".join(parts)


def kinds() -> list[KindInfo]:
    """Alle Arten von Terminen für die Auswahl im Formular."""
    return [
        KindInfo(kind=key, label=label, absence=key in ABSENCE_KINDS)
        for key, label in KINDS.items()
    ]


# --- Personen -------------------------------------------------------------------


def visible_people(session: Session, viewer_id: int, view_all: bool) -> list[Person]:
    """Die Personen, deren Kalender diese Person sehen darf: alle oder nur sich selbst."""
    people = accounts.list_people(session)
    if view_all:
        return people
    return [person for person in people if person.id == viewer_id]


def _names(session: Session) -> dict[int, str]:
    return {person.id: person.display_name for person in accounts.list_people(session)}


# --- Prüfen ---------------------------------------------------------------------


def _clean(session: Session, data: EntryIn) -> EntryIn:
    """Prüft die Eingabe und gibt sie bereinigt zurück."""
    title = data.title.strip()
    if not title:
        raise ValueError("Bitte angeben, worum es geht – z. B. „Carport Berger“.")
    if data.kind not in KINDS:
        raise ValueError(f"Die Art „{data.kind}“ gibt es nicht.")
    end_date = data.end_date or data.start_date
    if end_date < data.start_date:
        raise ValueError("Der letzte Tag liegt vor dem ersten Tag.")
    if (end_date - data.start_date).days >= MAX_ENTRY_DAYS:
        raise ValueError("Ein Termin darf höchstens ein Jahr dauern.")
    if (data.start_time is None) != (data.end_time is None):
        raise ValueError("Bitte Beginn und Ende angeben – oder beides leer lassen (ganzer Tag).")
    if (
        data.start_time is not None
        and end_date == data.start_date
        and data.end_time <= data.start_time
    ):
        raise ValueError("Das Ende liegt vor dem Beginn.")
    people = list(dict.fromkeys(data.people))  # doppelte entfernen, Reihenfolge behalten
    if not people:
        raise ValueError("Bitte mindestens eine Person einplanen.")
    known = _names(session)
    for account_id in people:
        if account_id not in known:
            raise ValueError(f"Die Person {account_id} gibt es nicht oder sie ist gesperrt.")
    return data.model_copy(
        update={
            "title": title,
            "end_date": end_date,
            "location": data.location.strip(),
            "note": data.note.strip(),
            "people": people,
        }
    )


def _overlaps(entry: CalendarEntry, data: EntryIn) -> bool:
    """Überschneiden sich der gespeicherte Termin und der neue?"""
    if entry.start_date > data.end_date or entry.end_date < data.start_date:
        return False
    # Zwei Termine am selben einzelnen Tag mit Uhrzeiten, die sich nicht treffen, sind kein Problem.
    same_single_day = (
        entry.start_date == entry.end_date == data.start_date == data.end_date
        and entry.start_time is not None
        and data.start_time is not None
    )
    if same_single_day:
        return entry.start_time < data.end_time and data.start_time < entry.end_time
    return True


def _warnings(session: Session, data: EntryIn, except_id: int | None) -> list[str]:
    """Hinweise, wenn eine eingeplante Person zur selben Zeit schon etwas anderes hat.

    Gespeichert wird trotzdem – der Chef entscheidet. Bei Abwesenheit steht das deutlich dabei.
    """
    names = _names(session)
    warnings = []
    statement = (
        select(CalendarEntry, CalendarAssignment.account_id)
        .join(CalendarAssignment, CalendarAssignment.entry_id == CalendarEntry.id)
        .where(
            col(CalendarAssignment.account_id).in_(data.people),
            CalendarEntry.start_date <= data.end_date,
            CalendarEntry.end_date >= data.start_date,
        )
        .order_by(CalendarEntry.start_date)
    )
    for entry, account_id in session.exec(statement):
        if entry.id == except_id or not _overlaps(entry, data):
            continue
        day = _format_date(max(entry.start_date, data.start_date))
        name = names.get(account_id, f"Person {account_id}")
        if entry.kind in ABSENCE_KINDS:
            warnings.append(f"{name} ist ab {day} abwesend: {KINDS[entry.kind]}.")
        else:
            warnings.append(f"{name} ist am {day} schon eingeplant: {entry.title}.")
    return warnings


# --- Lesen ----------------------------------------------------------------------


def _info(session: Session, entry: CalendarEntry, names: dict[int, str]) -> EntryInfo:
    statement = select(CalendarAssignment.account_id).where(CalendarAssignment.entry_id == entry.id)
    people = [
        PersonRef(id=account_id, display_name=names.get(account_id, f"Person {account_id}"))
        for account_id in session.exec(statement)
    ]
    people.sort(key=lambda person: person.display_name)
    return EntryInfo(
        id=entry.id,
        title=entry.title,
        kind=entry.kind,
        kind_label=KINDS.get(entry.kind, entry.kind),
        start_date=entry.start_date,
        end_date=entry.end_date,
        start_time=entry.start_time,
        end_time=entry.end_time,
        location=entry.location,
        note=entry.note,
        people=people,
    )


def get_entry(session: Session, entry_id: int) -> CalendarEntry:
    entry = session.get(CalendarEntry, entry_id)
    if entry is None:
        raise LookupError(f"Den Termin {entry_id} gibt es nicht.")
    return entry


def list_entries(
    session: Session,
    start: date,
    end: date,
    viewer_id: int,
    view_all: bool,
    account_id: int | None = None,
) -> list[EntryInfo]:
    """Alle Termine, die zwischen start und end (beide eingeschlossen) liegen oder hineinragen.

    Ohne view_all nur die eigenen. Mit account_id nur die dieser Person (persönlicher Kalender).
    """
    if end < start:
        raise ValueError("Das Ende des Zeitraums liegt vor dem Anfang.")
    if (end - start).days > MAX_RANGE_DAYS:
        raise ValueError(f"Bitte höchstens {MAX_RANGE_DAYS} Tage auf einmal abfragen.")
    if not view_all:
        account_id = viewer_id
    statement = select(CalendarEntry).where(
        CalendarEntry.start_date <= end, CalendarEntry.end_date >= start
    )
    if account_id is not None:
        statement = statement.join(
            CalendarAssignment, CalendarAssignment.entry_id == CalendarEntry.id
        ).where(CalendarAssignment.account_id == account_id)
    statement = statement.order_by(
        CalendarEntry.start_date, CalendarEntry.start_time, CalendarEntry.id
    )
    names = _names(session)
    return [_info(session, entry, names) for entry in session.exec(statement)]


# --- Schreiben ------------------------------------------------------------------


def _assigned(session: Session, entry_id: int) -> list[int]:
    statement = select(CalendarAssignment.account_id).where(CalendarAssignment.entry_id == entry_id)
    return list(session.exec(statement))


def _assign(session: Session, entry_id: int, people: list[int]) -> None:
    session.exec(delete(CalendarAssignment).where(CalendarAssignment.entry_id == entry_id))
    for account_id in people:
        session.add(CalendarAssignment(entry_id=entry_id, account_id=account_id))


def create_entry(session: Session, data: EntryIn, created_by: int | None) -> SavedEntry:
    """Trägt einen Termin ein. Gibt ihn mit Hinweisen auf Überschneidungen zurück."""
    data = _clean(session, data)
    warnings = _warnings(session, data, except_id=None)
    entry = CalendarEntry(
        **data.model_dump(exclude={"people"}),
        created_by=created_by,
        created_at=datetime.now(UTC),
    )
    session.add(entry)
    session.flush()  # damit entry.id feststeht
    _assign(session, entry.id, data.people)
    session.commit()
    session.refresh(entry)
    others = [p for p in data.people if p != created_by]
    notifications.notify(session, others, f"Neu eingeplant: {describe(entry)}.")
    return SavedEntry(entry=_info(session, entry, _names(session)), warnings=warnings)


def update_entry(
    session: Session, entry_id: int, data: EntryIn, acting_id: int | None = None
) -> SavedEntry:
    """Ändert einen Termin. Gibt ihn mit Hinweisen auf Überschneidungen zurück.

    Mitteilungen: Neue Personen „neu eingeplant“, entfernte „ausgeplant“, alle anderen
    „geändert“ – aber nur, wenn sich für sie wirklich etwas geändert hat.
    """
    entry = get_entry(session, entry_id)
    data = _clean(session, data)
    warnings = _warnings(session, data, except_id=entry_id)
    before = describe(entry)
    old_people = _assigned(session, entry_id)
    for key, value in data.model_dump(exclude={"people"}).items():
        setattr(entry, key, value)
    session.add(entry)
    _assign(session, entry.id, data.people)
    session.commit()
    session.refresh(entry)

    after = describe(entry)
    added = [p for p in data.people if p not in old_people and p != acting_id]
    removed = [p for p in old_people if p not in data.people and p != acting_id]
    stayed = [p for p in data.people if p in old_people and p != acting_id]
    notifications.notify(session, added, f"Neu eingeplant: {after}.")
    notifications.notify(session, removed, f"Ausgeplant: {before}.")
    if after != before:
        notifications.notify(session, stayed, f"Geändert: {after} (vorher: {before}).")
    return SavedEntry(entry=_info(session, entry, _names(session)), warnings=warnings)


def delete_entry(session: Session, entry_id: int, acting_id: int | None = None) -> None:
    """Löscht einen Termin mit allen Einplanungen. Die Eingeplanten erfahren es."""
    entry = get_entry(session, entry_id)
    text = f"Abgesagt: {describe(entry)}."
    people = [p for p in _assigned(session, entry_id) if p != acting_id]
    session.exec(delete(CalendarAssignment).where(CalendarAssignment.entry_id == entry_id))
    session.delete(entry)
    session.commit()
    notifications.notify(session, people, text)
