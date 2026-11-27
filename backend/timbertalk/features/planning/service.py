# Die Logik des Features „Planung: Kalender je Mitarbeiter“ (F8) als einfache Funktionen:
# Termine eintragen, ändern, löschen und für einen Zeitraum lesen – für alle oder nur für sich
# selbst – und beim Einplanen auf Überschneidungen hinweisen.
#
# Jede Funktion bekommt als ersten Parameter die Datenbank-Sitzung: session: Session.
# Fehler: ValueError – die Angabe passt nicht (422), LookupError – gibt es nicht (404).
# Die Personen kommen aus F10 und nur über dessen service.py (list_people()).
# Wer ein-, aus- oder umgeplant wird, bekommt eine Mitteilung (Feature notifications) – außer der
# Person, die gerade plant.

import hashlib
import secrets
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlmodel import Session, col, delete, select

from timbertalk.features.accounts import service as accounts
from timbertalk.features.accounts.models import Person
from timbertalk.features.notifications import service as notifications
from timbertalk.features.planning.models import (
    ABSENCE_KINDS,
    KINDS,
    REQUEST_STATUS,
    RESOURCE_CATEGORIES,
    AbsenceRequest,
    CalendarAssignment,
    CalendarEntry,
    Decision,
    EntryIn,
    EntryInfo,
    IcalLink,
    IcalToken,
    KindInfo,
    PersonRef,
    RequestIn,
    RequestInfo,
    Resource,
    ResourceAssignment,
    ResourceIn,
    ResourceInfo,
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
    resources = list(dict.fromkeys(data.resources))
    if data.project_id is not None and data.project_id < 1:
        raise ValueError("Die Projektnummer muss eine positive Zahl sein.")
    if not people and not resources:
        raise ValueError("Bitte mindestens eine Person oder ein Fahrzeug/eine Maschine einplanen.")
    known = _names(session)
    for account_id in people:
        if account_id not in known:
            raise ValueError(f"Die Person {account_id} gibt es nicht oder sie ist gesperrt.")
    usable = _resource_names(session)
    for resource_id in resources:
        if resource_id not in usable:
            raise ValueError(f"Das Fahrzeug/die Maschine {resource_id} gibt es nicht (mehr).")
    return data.model_copy(
        update={
            "title": title,
            "end_date": end_date,
            "location": data.location.strip(),
            "note": data.note.strip(),
            "people": people,
            "resources": resources,
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

    # Dasselbe für Fahrzeuge und Maschinen: ein Kran kann nicht auf zwei Baustellen stehen.
    resource_names = _resource_names(session)
    statement = (
        select(CalendarEntry, ResourceAssignment.resource_id)
        .join(ResourceAssignment, ResourceAssignment.entry_id == CalendarEntry.id)
        .where(
            col(ResourceAssignment.resource_id).in_(data.resources),
            CalendarEntry.start_date <= data.end_date,
            CalendarEntry.end_date >= data.start_date,
        )
        .order_by(CalendarEntry.start_date)
    )
    for entry, resource_id in session.exec(statement):
        if entry.id == except_id or not _overlaps(entry, data):
            continue
        day = _format_date(max(entry.start_date, data.start_date))
        name = resource_names.get(resource_id, f"Fahrzeug {resource_id}")
        warnings.append(f"{name} ist am {day} schon verplant: {entry.title}.")
    return warnings


# --- Lesen ----------------------------------------------------------------------


def _info(session: Session, entry: CalendarEntry, names: dict[int, str]) -> EntryInfo:
    statement = select(CalendarAssignment.account_id).where(CalendarAssignment.entry_id == entry.id)
    people = [
        PersonRef(id=account_id, display_name=names.get(account_id, f"Person {account_id}"))
        for account_id in session.exec(statement)
    ]
    people.sort(key=lambda person: person.display_name)
    resource_names = _resource_names(session, include_inactive=True)
    statement = select(ResourceAssignment.resource_id).where(
        ResourceAssignment.entry_id == entry.id
    )
    resources = [
        PersonRef(id=resource_id, display_name=resource_names.get(resource_id, "?"))
        for resource_id in session.exec(statement)
    ]
    resources.sort(key=lambda resource: resource.display_name)
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
        project_id=entry.project_id,
        people=people,
        resources=resources,
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


def _assign(session: Session, entry_id: int, data: EntryIn) -> None:
    """Speichert, wer und was zu einem Termin eingeplant ist (ersetzt die bisherige Liste)."""
    session.exec(delete(CalendarAssignment).where(CalendarAssignment.entry_id == entry_id))
    session.exec(delete(ResourceAssignment).where(ResourceAssignment.entry_id == entry_id))
    for account_id in data.people:
        session.add(CalendarAssignment(entry_id=entry_id, account_id=account_id))
    for resource_id in data.resources:
        session.add(ResourceAssignment(entry_id=entry_id, resource_id=resource_id))


def create_entry(
    session: Session, data: EntryIn, created_by: int | None, notify: bool = True
) -> SavedEntry:
    """Trägt einen Termin ein. Gibt ihn mit Hinweisen auf Überschneidungen zurück.

    notify=False: keine Mitteilung „neu eingeplant“ (z. B. bei genehmigtem Urlaub, dort gibt es
    eine eigene Mitteilung).
    """
    data = _clean(session, data)
    warnings = _warnings(session, data, except_id=None)
    entry = CalendarEntry(
        **data.model_dump(exclude={"people", "resources"}),
        created_by=created_by,
        created_at=datetime.now(UTC),
    )
    session.add(entry)
    session.flush()  # damit entry.id feststeht
    _assign(session, entry.id, data)
    session.commit()
    session.refresh(entry)
    if notify:
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
    for key, value in data.model_dump(exclude={"people", "resources"}).items():
        setattr(entry, key, value)
    session.add(entry)
    _assign(session, entry.id, data)
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
    session.exec(delete(ResourceAssignment).where(ResourceAssignment.entry_id == entry_id))
    session.delete(entry)
    session.commit()
    notifications.notify(session, people, text)


# --- Fahrzeuge und Maschinen ------------------------------------------------------


def _resource_names(session: Session, include_inactive: bool = False) -> dict[int, str]:
    statement = select(Resource)
    if not include_inactive:
        statement = statement.where(col(Resource.active).is_(True))
    return {resource.id: resource.name for resource in session.exec(statement)}


def _resource_info(resource: Resource, show_rates: bool = True) -> ResourceInfo:
    return ResourceInfo(
        id=resource.id,
        name=resource.name,
        category=resource.category,
        category_label=RESOURCE_CATEGORIES.get(resource.category, resource.category),
        active=resource.active,
        rate_per_km=resource.rate_per_km if show_rates else None,
    )


def list_resources(
    session: Session, include_inactive: bool = False, show_rates: bool = True
) -> list[ResourceInfo]:
    """Fahrzeuge und Maschinen, erst nach Art, dann nach Namen sortiert.

    show_rates=False: ohne Kilometersatz – für Konten ohne „finance.view“.
    """
    statement = select(Resource).order_by(Resource.category.desc(), Resource.name)
    if not include_inactive:
        statement = statement.where(col(Resource.active).is_(True))
    return [_resource_info(resource, show_rates) for resource in session.exec(statement)]


# Höchster erlaubter Kilometersatz in Euro – schützt vor Tippfehlern wie 55 statt 0,55.
MAX_RATE_PER_KM = Decimal("10")


def set_vehicle_rate(session: Session, resource_id: int, rate: Decimal | None) -> ResourceInfo:
    """Trägt den Kilometersatz eines Fahrzeugs ein (Euro netto je km). None löscht ihn."""
    resource = session.get(Resource, resource_id)
    if resource is None:
        raise LookupError(f"Das Fahrzeug {resource_id} gibt es nicht.")
    if resource.category != "vehicle":
        raise ValueError("Einen Kilometersatz haben nur Fahrzeuge, keine Maschinen.")
    if rate is not None and (not rate.is_finite() or rate <= 0 or rate > MAX_RATE_PER_KM):
        raise ValueError("Der Kilometersatz muss zwischen 0 und 10 Euro liegen, z. B. 0,55.")
    resource.rate_per_km = rate
    session.add(resource)
    session.commit()
    session.refresh(resource)
    return _resource_info(resource)


def vehicles_with_rate(session: Session) -> list[ResourceInfo]:
    """Alle Fahrzeuge im Einsatz mit eingetragenem Kilometersatz – damit bucht F5 Fahrten."""
    return [
        info
        for info in list_resources(session)
        if info.category == "vehicle" and info.rate_per_km is not None
    ]


def vehicle_rate(session: Session, resource_id: int | None) -> tuple[int, str, Decimal]:
    """Nummer, Name und Kilometersatz des Fahrzeugs für eine Fahrt (F5).

    Ohne resource_id: Gibt es genau ein Fahrzeug mit Satz, wird es genommen – sonst Fehler.
    """
    usable = vehicles_with_rate(session)
    if resource_id is None:
        if len(usable) == 1:
            return usable[0].id, usable[0].name, usable[0].rate_per_km
        if not usable:
            raise ValueError(
                "Für Fahrten fehlt ein Fahrzeug mit Kilometersatz "
                "(Einstellungen → Fahrzeuge und Maschinen)."
            )
        raise ValueError("Bitte angeben, mit welchem Fahrzeug gefahren wurde.")
    for info in usable:
        if info.id == resource_id:
            return info.id, info.name, info.rate_per_km
    resource = session.get(Resource, resource_id)
    if resource is None or resource.category != "vehicle" or not resource.active:
        raise LookupError(f"Das Fahrzeug {resource_id} gibt es nicht (mehr).")
    raise ValueError(
        f"Für „{resource.name}“ ist noch kein Kilometersatz eingetragen "
        "(Einstellungen → Fahrzeuge und Maschinen)."
    )


def resource_name(session: Session, resource_id: int) -> str:
    """Der Name eines Fahrzeugs oder einer Maschine, auch wenn es ausgemustert ist."""
    resource = session.get(Resource, resource_id)
    return resource.name if resource is not None else f"Fahrzeug {resource_id}"


def _clean_resource(data: ResourceIn) -> ResourceIn:
    name = data.name.strip()
    if not name:
        raise ValueError("Bitte einen Namen angeben, z. B. „Transporter“ oder „Autokran“.")
    if data.category not in RESOURCE_CATEGORIES:
        raise ValueError(f"Die Art „{data.category}“ gibt es nicht.")
    return data.model_copy(update={"name": name})


def create_resource(session: Session, data: ResourceIn) -> ResourceInfo:
    """Legt ein Fahrzeug oder eine Maschine an."""
    data = _clean_resource(data)
    resource = Resource(**data.model_dump())
    session.add(resource)
    session.commit()
    session.refresh(resource)
    return _resource_info(resource)


def update_resource(session: Session, resource_id: int, data: ResourceIn) -> ResourceInfo:
    """Ändert Name, Art oder ob es ausgemustert ist. Bisherige Termine behalten es."""
    resource = session.get(Resource, resource_id)
    if resource is None:
        raise LookupError(f"Das Fahrzeug/die Maschine {resource_id} gibt es nicht.")
    data = _clean_resource(data)
    for key, value in data.model_dump().items():
        setattr(resource, key, value)
    session.add(resource)
    session.commit()
    session.refresh(resource)
    return _resource_info(resource)


# --- Urlaubsanträge -----------------------------------------------------------------


def _days_text(start: date, end: date) -> str:
    if start == end:
        return _short_day(start)
    return f"{_short_day(start)}–{_short_day(end)}"


def _request_entry(request: AbsenceRequest | RequestIn, account_id: int) -> EntryIn:
    """Der Termin, der aus einem Antrag würde – für Hinweise und beim Genehmigen."""
    return EntryIn(
        title="Urlaub",
        kind="vacation",
        start_date=request.start_date,
        end_date=request.end_date,
        note=request.note,
        people=[account_id],
    )


def _request_info(session: Session, request: AbsenceRequest, names: dict[int, str]) -> RequestInfo:
    conflicts = []
    if request.status == "pending":
        conflicts = _warnings(session, _request_entry(request, request.account_id), None)
    return RequestInfo(
        id=request.id,
        person=PersonRef(
            id=request.account_id,
            display_name=names.get(request.account_id, f"Person {request.account_id}"),
        ),
        start_date=request.start_date,
        end_date=request.end_date,
        days=(request.end_date - request.start_date).days + 1,
        note=request.note,
        status=request.status,
        status_label=REQUEST_STATUS[request.status],
        decision_note=request.decision_note,
        conflicts=conflicts,
    )


def request_absence(session: Session, account_id: int, data: RequestIn) -> RequestInfo:
    """Stellt einen Urlaubsantrag. Wer genehmigen darf, bekommt eine Mitteilung."""
    if data.end_date < data.start_date:
        raise ValueError("Der letzte Urlaubstag liegt vor dem ersten.")
    if (data.end_date - data.start_date).days >= MAX_ENTRY_DAYS:
        raise ValueError("Ein Antrag darf höchstens ein Jahr umfassen.")
    request = AbsenceRequest(
        account_id=account_id,
        start_date=data.start_date,
        end_date=data.end_date,
        note=data.note.strip(),
        created_at=datetime.now(UTC),
    )
    session.add(request)
    session.commit()
    session.refresh(request)
    names = _names(session)
    approvers = [
        p
        for p in accounts.people_with_permission(session, "calendar.approve_absence")
        if p != account_id
    ]
    notifications.notify(
        session,
        approvers,
        f"Urlaubsantrag von {names.get(account_id, '?')}: "
        f"{_days_text(request.start_date, request.end_date)} – "
        "bitte auf dem Dashboard entscheiden.",
        link="#start",
        topic=_request_topic(request.id),
    )
    return _request_info(session, request, names)


def _request_topic(request_id: int) -> str:
    """Thema der Mitteilung „bitte entscheiden“ – sie verschwindet, sobald entschieden ist."""
    return f"absence-request:{request_id}"


def list_requests(session: Session, viewer_id: int, may_approve: bool) -> list[RequestInfo]:
    """Wer genehmigen darf, sieht alle Anträge; alle anderen nur die eigenen. Offene zuerst."""
    statement = select(AbsenceRequest)
    if not may_approve:
        statement = statement.where(AbsenceRequest.account_id == viewer_id)
    requests = list(session.exec(statement))
    requests.sort(key=lambda r: (r.status != "pending", r.start_date, r.id))
    names = _names(session)
    return [_request_info(session, request, names) for request in requests]


def _pending_request(session: Session, request_id: int) -> AbsenceRequest:
    request = session.get(AbsenceRequest, request_id)
    if request is None:
        raise LookupError(f"Den Antrag {request_id} gibt es nicht.")
    if request.status != "pending":
        raise ValueError("Über diesen Antrag ist schon entschieden.")
    return request


def decide_request(
    session: Session, request_id: int, approve: bool, acting_id: int, note: str = ""
) -> Decision:
    """Genehmigt oder lehnt einen Antrag ab. Genehmigt entsteht ein Termin „Urlaub“.

    Die Person bekommt eine Mitteilung; beim Genehmigen kommen Hinweise zurück, falls sie in der
    Zeit schon eingeplant ist (die Einsätze bleiben – der Planende entscheidet, was damit wird).
    """
    request = _pending_request(session, request_id)
    days = _days_text(request.start_date, request.end_date)
    warnings: list[str] = []
    if approve:
        saved = create_entry(
            session, _request_entry(request, request.account_id), acting_id, notify=False
        )
        request.entry_id = saved.entry.id
        warnings = saved.warnings
    request.status = "approved" if approve else "rejected"
    request.decided_by = acting_id
    request.decided_at = datetime.now(UTC)
    request.decision_note = note.strip()
    session.add(request)
    session.commit()
    session.refresh(request)
    text = f"Urlaub {'genehmigt' if approve else 'abgelehnt'}: {days}"  # endet auf „.“
    if request.decision_note:
        text += f" {request.decision_note}"
    notifications.resolve(session, _request_topic(request.id))
    notifications.notify(session, [request.account_id], text)
    info = _request_info(session, request, _names(session))
    return Decision(request=info, warnings=warnings)


def withdraw_request(session: Session, request_id: int, account_id: int) -> None:
    """Zieht einen eigenen, noch offenen Antrag zurück."""
    request = _pending_request(session, request_id)
    if request.account_id != account_id:
        raise LookupError(f"Den Antrag {request_id} gibt es nicht.")
    session.delete(request)
    session.commit()
    notifications.resolve(session, _request_topic(request_id))


# --- Kalender-Abo (iCal) ------------------------------------------------------------
#
# Kalender-Apps (iPhone, Android, Outlook) können einen Kalender über eine Adresse abonnieren und
# holen ihn regelmäßig neu. Die Adresse enthält einen langen geheimen Schlüssel; in der Datenbank
# steht nur sein Hash. Das Format ist iCalendar (RFC 5545): reiner Text, eine Angabe je Zeile.

# Das Abo zeigt die Termine ab so vielen Tagen vor heute bis so viele Tage danach.
ICAL_DAYS_BACK = 60
ICAL_DAYS_AHEAD = 365


def _ical_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def ical_link(session: Session, account_id: int) -> IcalLink:
    """Ob diese Person einen Abo-Link hat (die Adresse selbst wird nie wieder gezeigt)."""
    return IcalLink(active=session.get(IcalToken, account_id) is not None)


def new_ical_link(session: Session, account_id: int) -> IcalLink:
    """Erzeugt einen neuen Abo-Link. Ein alter Link hört damit auf zu funktionieren."""
    token = secrets.token_urlsafe(32)
    stored = session.get(IcalToken, account_id) or IcalToken(account_id=account_id, token_hash="")
    stored.token_hash = _ical_hash(token)
    stored.created_at = datetime.now(UTC)
    session.add(stored)
    session.commit()
    return IcalLink(active=True, path=f"/api/planning/ical/{token}.ics")


def delete_ical_link(session: Session, account_id: int) -> None:
    """Macht den Abo-Link ungültig."""
    stored = session.get(IcalToken, account_id)
    if stored is not None:
        session.delete(stored)
        session.commit()


def _ical_text(value: str) -> str:
    """Text so schreiben, wie iCalendar ihn erwartet: \\, Komma, Semikolon und Zeilenumbruch."""
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _fold(line: str) -> str:
    """iCalendar erlaubt höchstens 75 Byte je Zeile; längere werden mit Leerzeichen fortgesetzt."""
    data = line.encode()
    parts = []
    limit = 75
    while len(data) > limit:
        cut = limit
        while (data[cut] & 0xC0) == 0x80:  # nie mitten in einem Umlaut trennen
            cut -= 1
        parts.append(data[:cut].decode())
        data = data[cut:]
        limit = 74  # Fortsetzungszeilen beginnen mit einem Leerzeichen
    parts.append(data.decode())
    return "\r\n ".join(parts)


def ical_feed(session: Session, token: str) -> str:
    """Der Kalender einer Person als iCalendar-Text – für ihren geheimen Abo-Link."""
    statement = select(IcalToken).where(IcalToken.token_hash == _ical_hash(token))
    stored = session.exec(statement).first()
    names = _names(session)
    if stored is None or stored.account_id not in names:
        raise LookupError("Diesen Kalender gibt es nicht (mehr).")
    today = date.today()
    entries = session.exec(
        select(CalendarEntry)
        .join(CalendarAssignment, CalendarAssignment.entry_id == CalendarEntry.id)
        .where(
            CalendarAssignment.account_id == stored.account_id,
            CalendarEntry.end_date >= today - timedelta(days=ICAL_DAYS_BACK),
            CalendarEntry.start_date <= today + timedelta(days=ICAL_DAYS_AHEAD),
        )
        .order_by(CalendarEntry.start_date)
    )
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//TimberTalk//Kalender//DE",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{_ical_text('TimberTalk – ' + names[stored.account_id])}",
        "REFRESH-INTERVAL;VALUE=DURATION:PT1H",
        "X-PUBLISHED-TTL:PT1H",
    ]
    for entry in entries:
        info = _info(session, entry, names)
        with_whom = [p.display_name for p in info.people + info.resources]
        details = [info.kind_label, "Mit: " + ", ".join(with_whom), entry.note]
        lines += [
            "BEGIN:VEVENT",
            f"UID:planning-entry-{entry.id}@timbertalk",
            f"DTSTAMP:{stamp}",
            f"SUMMARY:{_ical_text(entry.title)}",
        ]
        if entry.start_time is None:
            # Ganztägig: das Ende ist in iCalendar der Tag NACH dem letzten Tag.
            lines += [
                f"DTSTART;VALUE=DATE:{entry.start_date:%Y%m%d}",
                f"DTEND;VALUE=DATE:{entry.end_date + timedelta(days=1):%Y%m%d}",
            ]
        else:
            # Mit Uhrzeit über mehrere Tage: jeden Tag dieselbe Zeit (Wiederholung täglich).
            # Ohne Zeitzone = Ortszeit des Handys, so wie es auf der Plantafel steht.
            day = f"{entry.start_date:%Y%m%d}"
            lines += [
                f"DTSTART:{day}T{entry.start_time:%H%M%S}",
                f"DTEND:{day}T{entry.end_time:%H%M%S}",
            ]
            count = (entry.end_date - entry.start_date).days + 1
            if count > 1:
                lines.append(f"RRULE:FREQ=DAILY;COUNT={count}")
        if entry.location:
            lines.append(f"LOCATION:{_ical_text(entry.location)}")
        description = "\n".join(part for part in details if part and part != "Mit: ")
        lines += [f"DESCRIPTION:{_ical_text(description)}", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"
