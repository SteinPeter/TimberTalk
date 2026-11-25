# Die Logik des Features „Projekte“ (F3) als einfache Funktionen.
# Jede Funktion bekommt als ersten Parameter die Datenbank-Sitzung: `session: Session`.
# Andere Features (z. B. Team B über S-03, F2 Kunden, F4 Stunden, F5 Material, F12 Planung)
# benutzen dieses Feature ausschließlich über die Funktionen in dieser Datei.

import json
from datetime import date, timedelta
from typing import Any

from sqlmodel import Session, select, update

from timbertalk.features.customers import service as customers_service
from timbertalk.features.projects.models import (
    DRAFT_STATUS_CONFIRMED,
    DRAFT_STATUS_OPEN,
    DRAFT_STATUS_REJECTED,
    PROJECT_STATUSES,
    STATUS_ANGEFRAGT,
    STATUS_IN_ARBEIT,
    CustomerInfo,
    CustomerLookupResponse,
    CustomerProjects,
    Project,
    ProjectDraft,
    ProjectInfo,
)

# Höchstzahl für KI-Suchen nach S-09 („höchstens 10 Treffer“).
MAX_SEARCH_RESULTS = 10
# Obergrenze für geplante Projektdauer in Tagen (10 Jahre).
MAX_DURATION_DAYS = 3650
# Größte Nummer, die SQLite speichern kann. Größere Zahlen führen sonst zum Absturz.
MAX_ID = 2**63 - 1

# Felder, die `update_project` und `update_project_draft` annehmen.
_UPDATE_FIELDS = {
    "customer_id",
    "customer_name",
    "name",
    "baustelle",
    "status",
    "start_date",
    "duration_days",
    "end_date",
    "notes",
    "archived",
}

# Weitere Schreibweisen für den Status „in_arbeit“.
_STATUS_ALIASES = {
    "in arbeit": STATUS_IN_ARBEIT,
    "in-arbeit": STATUS_IN_ARBEIT,
}


# --- Prüfungen und Hilfen -------------------------------------------------------


def _is_id(value: Any) -> bool:
    """Wahr, wenn der Wert eine ganze Zahl ist, die als Nummer in der Datenbank stehen kann."""
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= MAX_ID


def _require_id(value: Any, label: str) -> int:
    """Prüft, dass eine Nummer eine ganze Zahl ab 1 ist (keine bool, kein Text)."""
    if not _is_id(value):
        raise ValueError(f"{label} muss eine ganze Zahl ab 1 sein.")
    return value


def _require_text(value: Any, label: str) -> str:
    """Prüft, dass ein Pflichttext nicht leer ist, und entfernt Ränder."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} darf nicht leer sein.")
    return value.strip()


def _clean_text(value: Any) -> str:
    """Säubert einen optionalen Text."""
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError("Textangabe erwartet.")
    return value.strip()


def _require_status(value: Any) -> str:
    """Prüft den Projektstatus und normalisiert die Schreibweise „in Arbeit“ → „in_arbeit“."""
    if not isinstance(value, str):
        raise ValueError("Status muss ein Text sein.")
    cleaned = value.strip().lower()
    cleaned = _STATUS_ALIASES.get(cleaned, cleaned)
    if cleaned not in PROJECT_STATUSES:
        allowed = ", ".join(PROJECT_STATUSES)
        raise ValueError(f"Unbekannter Status „{value}“. Erlaubt sind: {allowed}.")
    return cleaned


def _require_date(value: Any, label: str) -> date | None:
    """Prüft, dass ein Datum wirklich ein Datum (oder leer) ist."""
    if value is not None and type(value) is not date:
        raise ValueError(f"{label} muss ein Datum sein.")
    return value


def _validate_schedule(
    start_date: date | None,
    duration_days: int | None,
    end_date: date | None,
) -> tuple[date | None, int | None, date | None]:
    """Prüft Beginn, Dauer und Ende und ergänzt das Enddatum, wenn Beginn und Dauer bekannt sind."""
    _require_date(start_date, "Startdatum")
    _require_date(end_date, "Enddatum")
    if duration_days is not None and (
        isinstance(duration_days, bool)
        or not isinstance(duration_days, int)
        or duration_days < 1
        or duration_days > MAX_DURATION_DAYS
    ):
        raise ValueError(
            f"Die Dauer muss eine ganze Zahl zwischen 1 und {MAX_DURATION_DAYS} Tagen sein."
        )
    if start_date is not None and end_date is not None and end_date < start_date:
        raise ValueError("Das Enddatum darf nicht vor dem Startdatum liegen.")
    if start_date is not None and duration_days is not None:
        try:
            computed = start_date + timedelta(days=duration_days - 1)
        except OverflowError:
            raise ValueError("Das Enddatum liegt zu weit in der Zukunft.") from None
        if end_date is None:
            end_date = computed
        elif end_date != computed:
            raise ValueError("Dauer und Enddatum passen nicht zusammen.")
    return start_date, duration_days, end_date


def _merge_schedule(
    project: Project,
    changes: dict[str, Any],
) -> tuple[date | None, int | None, date | None]:
    """Verbindet geänderte Angaben zum Zeitraum mit den gespeicherten.

    Maßgeblich ist, was sich wirklich ändert: Bei neuem Beginn oder neuer Dauer rückt das Ende
    nach, bei neuem Ende (und gleicher Dauer) rückt die Dauer nach. Ein unverändert
    mitgeschicktes Feld zählt nicht als Änderung.
    """
    start = _require_date(changes.get("start_date", project.start_date), "Startdatum")
    duration = changes.get("duration_days", project.duration_days)
    end = _require_date(changes.get("end_date", project.end_date), "Enddatum")

    duration_changed = duration != project.duration_days
    start_changed = start != project.start_date
    end_changed = end != project.end_date

    if start is not None and duration is not None and end is not None:
        if not end_changed and (start_changed or duration_changed):
            end = None  # wird aus Beginn und Dauer neu berechnet
        elif end_changed and not duration_changed and end >= start:
            duration = (end - start).days + 1
    return _validate_schedule(start, duration, end)


def _customer_from_object(raw: Any) -> CustomerInfo | None:
    """Übersetzt ein Kundenobjekt aus F2 in `CustomerInfo` (id, name)."""
    if raw is None:
        return None
    customer_id = getattr(raw, "id", None)
    if customer_id is None and isinstance(raw, dict):
        customer_id = raw.get("id")
    if customer_id is None:
        return None

    name = getattr(raw, "name", None)
    if not name:
        name = getattr(raw, "display_name", None)
    if not name and isinstance(raw, dict):
        name = raw.get("name") or raw.get("display_name")
    if not name:
        company = getattr(raw, "company_name", "") or ""
        first = getattr(raw, "first_name", "") or ""
        last = getattr(raw, "last_name", "") or ""
        name = company.strip() or f"{first} {last}".strip() or f"Kunde #{customer_id}"
    return CustomerInfo(id=int(customer_id), name=str(name).strip())


def customers_from_f2_available() -> bool:
    """Meldet, ob der Service von Feature F2 (`customers/service.py`) schon bereitsteht."""
    return callable(getattr(customers_service, "get_customer", None))


def _resolve_customer_for_write(
    session: Session,
    customer_id: Any,
    fallback_name: str = "",
) -> tuple[int, str]:
    """Prüft die Kundennummer beim Speichern.

    Ist F2 (`customers/service.py`) vorhanden, wird geprüft, ob der Kunde dort existiert, und sein
    aktueller Name übernommen. Ohne F2 ist zumindest eine gültige Kundennummer ab 1 Pflicht.
    """
    if customer_id is None:
        raise ValueError(
            "Ein Projekt braucht einen Kunden und lässt sich ohne Kunde nicht speichern."
        )
    cid = _require_id(customer_id, "Kunde")
    cleaned_name = _clean_text(fallback_name)

    if customers_from_f2_available():
        customer = get_customer(session, cid)
        if customer is None:
            raise LookupError(f"Kunde {cid} gibt es nicht.")
        return cid, customer.name

    # Übergangsweise ohne F2: Ist derselbe Kunde schon an einem Projekt bekannt, Namen übernehmen.
    if not cleaned_name:
        existing = get_customer(session, cid)
        if existing is not None:
            cleaned_name = existing.name
    return cid, cleaned_name or f"Kunde #{cid}"


def _customer_name_map(session: Session) -> dict[int, str]:
    """Baut eine Zuordnung Kundennummer → Name aus F2 (wenn vorhanden)."""
    if not callable(getattr(customers_service, "list_customers", None)):
        return {}
    mapping: dict[int, str] = {}
    for raw in customers_service.list_customers(session):
        info = _customer_from_object(raw)
        if info is not None:
            mapping[info.id] = info.name
    return mapping


def _to_project_info(
    session: Session,
    project: Project,
    customer_names: dict[int, str] | None = None,
) -> ProjectInfo:
    """Macht aus einer Tabellenzeile das Antwortobjekt `ProjectInfo` (inkl. S-03-Felder)."""
    name = ""
    if customer_names is not None and project.customer_id in customer_names:
        name = customer_names[project.customer_id]
    elif customers_from_f2_available():
        customer = get_customer(session, project.customer_id)
        if customer is not None:
            name = customer.name
    if not name:
        name = project.customer_name or f"Kunde #{project.customer_id}"

    return ProjectInfo(
        id=project.id,  # type: ignore[arg-type]
        name=project.name,
        customer_id=project.customer_id,
        customer_name=name,
        baustelle=project.site_address,
        status=project.status,
        start_date=project.start_date,
        duration_days=project.duration_days,
        end_date=project.end_date,
        notes=project.notes,
        archived=project.archived,
    )


def _get_project_row(session: Session, project_id: int) -> Project:
    """Holt eine Projektzeile oder meldet LookupError."""
    pid = _require_id(project_id, "Projektnummer")
    project = session.get(Project, pid)
    if project is None:
        raise LookupError(f"Projekt {pid} gibt es nicht.")
    return project


# --- Schnittstelle S-03 (für Team B und andere Features) ------------------------


def get_project(session: Session, project_id: int) -> ProjectInfo | None:
    """Liefert ein Projekt mit Kunde und Baustelle (S-03). Unbekannte ID → None."""
    if not _is_id(project_id):
        return None
    project = session.get(Project, project_id)
    if project is None:
        return None
    return _to_project_info(session, project)


def get_customer(session: Session, customer_id: int) -> CustomerInfo | None:
    """Liefert einen Kunden mit id und name (S-03). Unbekannte ID → None.

    Delegiert an `customers/service.py` (F2), sobald dort `get_customer` existiert.
    Bis dahin liest die Funktion den Kunden aus bereits angelegten Projekten.
    """
    if not _is_id(customer_id):
        return None
    f2_get = getattr(customers_service, "get_customer", None)
    if callable(f2_get):
        return _customer_from_object(f2_get(session, customer_id))

    statement = (
        select(Project)
        .where(Project.customer_id == customer_id)
        .order_by(Project.id.desc())  # type: ignore[union-attr]
        .limit(1)
    )
    project = session.exec(statement).first()
    if project is None:
        return None
    name = project.customer_name or f"Kunde #{customer_id}"
    return CustomerInfo(id=customer_id, name=name)


def list_customers(session: Session) -> CustomerLookupResponse:
    """Liefert bekannte Kunden für die Auswahl im Frontend (aus F2 oder aus Projekten)."""
    f2_list = getattr(customers_service, "list_customers", None)
    if callable(f2_list):
        items = []
        for raw in f2_list(session):
            info = _customer_from_object(raw)
            if info is not None:
                items.append(info)
        items.sort(key=lambda item: (item.name.casefold(), item.id))
        return CustomerLookupResponse(source="customers", customers=items)

    rows = session.exec(
        select(Project).order_by(Project.id.desc())  # type: ignore[union-attr]
    ).all()
    seen: dict[int, CustomerInfo] = {}
    for row in rows:
        if row.customer_id not in seen:
            seen[row.customer_id] = CustomerInfo(
                id=row.customer_id,
                name=row.customer_name or f"Kunde #{row.customer_id}",
            )
    items = sorted(seen.values(), key=lambda item: (item.name.casefold(), item.id))
    return CustomerLookupResponse(source="fallback", customers=items)


# --- Projekte lesen und suchen --------------------------------------------------


def list_projects(
    session: Session,
    *,
    text: str | None = None,
    customer_id: int | None = None,
    status: str | None = None,
    include_archived: bool = False,
    limit: int | None = None,
) -> list[ProjectInfo]:
    """Sucht und filtert Projekte nach Text, Kunde, Status und Archiv-Kennzeichen."""
    statement = select(Project)
    if not include_archived:
        statement = statement.where(Project.archived == False)  # noqa: E712
    if customer_id is not None:
        cid = _require_id(customer_id, "Kunde")
        statement = statement.where(Project.customer_id == cid)
    if text is not None and not isinstance(text, str):
        raise ValueError("Der Suchtext muss ein Text sein.")
    if status is not None and status != "":
        checked_status = _require_status(status)
        statement = statement.where(Project.status == checked_status)

    statement = statement.order_by(
        Project.archived.asc(),  # type: ignore[attr-defined]
        Project.id.desc(),  # type: ignore[union-attr]
    )
    rows = session.exec(statement).all()
    customer_names = _customer_name_map(session)
    infos = [_to_project_info(session, row, customer_names) for row in rows]

    if text is not None and text.strip():
        terms = [term for term in text.casefold().split() if term]
        infos = [
            info
            for info in infos
            if all(
                term
                in (
                    f"{info.name} {info.customer_name} {info.baustelle} {info.notes} #{info.id}"
                ).casefold()
                for term in terms
            )
        ]

    if limit is not None:
        return infos[:limit]
    return infos


def list_projects_for_customer(
    session: Session,
    customer_id: int,
    *,
    include_archived: bool = False,
) -> list[ProjectInfo]:
    """Liefert alle Projekte eines Kunden (u. a. für die Kundenliste in F2)."""
    return list_projects(
        session,
        customer_id=customer_id,
        include_archived=include_archived,
    )


def list_customer_projects(
    session: Session,
    *,
    include_archived: bool = False,
) -> list[CustomerProjects]:
    """Gruppiert Projekte je Kunde – zeigt auch Kunden ohne Projekt, wenn F2 aktiv ist."""
    lookup = list_customers(session)
    all_projects = list_projects(session, include_archived=include_archived)
    by_customer: dict[int, list[ProjectInfo]] = {}
    for project in all_projects:
        by_customer.setdefault(project.customer_id, []).append(project)

    result: list[CustomerProjects] = []
    seen_ids: set[int] = set()
    for customer in lookup.customers:
        seen_ids.add(customer.id)
        projects = by_customer.get(customer.id, [])
        if lookup.source == "customers" or projects:
            result.append(CustomerProjects(customer=customer, projects=projects))

    # Falls noch Projekte zu Kundennummern existieren, die nicht in der Kundenliste stehen.
    for cid, projects in sorted(by_customer.items()):
        if cid not in seen_ids:
            customer = CustomerInfo(id=cid, name=projects[0].customer_name)
            result.append(CustomerProjects(customer=customer, projects=projects))
    return result


# --- Projekte anlegen, ändern, Status setzen, archivieren -----------------------


def create_project(
    session: Session,
    *,
    customer_id: int,
    name: str,
    baustelle: str = "",
    status: str = STATUS_ANGEFRAGT,
    start_date: date | None = None,
    duration_days: int | None = None,
    end_date: date | None = None,
    notes: str = "",
    customer_name: str = "",
) -> ProjectInfo:
    """Legt ein neues Projekt zu einem Kunden an. Ohne Kunde wird abgelehnt."""
    cid, resolved_customer_name = _resolve_customer_for_write(session, customer_id, customer_name)
    cleaned_name = _require_text(name, "Projektname")
    cleaned_site = _clean_text(baustelle)
    checked_status = _require_status(status)
    cleaned_notes = _clean_text(notes)
    start_date, duration_days, end_date = _validate_schedule(start_date, duration_days, end_date)

    project = Project(
        customer_id=cid,
        customer_name=resolved_customer_name,
        name=cleaned_name,
        site_address=cleaned_site,
        status=checked_status,
        start_date=start_date,
        duration_days=duration_days,
        end_date=end_date,
        notes=cleaned_notes,
        archived=False,
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return _to_project_info(session, project)


def _clean_changes(
    session: Session,
    project: Project,
    fields: dict[str, Any],
) -> dict[str, Any]:
    """Prüft die Änderungen an einem Projekt und gibt sie gesäubert zurück.

    Das Projekt selbst wird dabei nicht angefasst: So bleibt bei einer abgelehnten Änderung
    nichts Halbes in der Sitzung zurück. Der Zeitraum wird erst in `_merge_schedule` geprüft.
    """
    if not isinstance(fields, dict) or not fields:
        raise ValueError("Es wurde kein Feld zum Ändern angegeben.")
    unknown = sorted(set(fields) - _UPDATE_FIELDS)
    if unknown:
        raise ValueError(f"Unbekannte Felder: {', '.join(unknown)}.")

    changes: dict[str, Any] = {}
    new_customer = "customer_id" in fields and fields["customer_id"] != project.customer_id
    if new_customer:
        fallback = fields.get("customer_name", "")
        cid, resolved_name = _resolve_customer_for_write(session, fields["customer_id"], fallback)
        changes["customer_id"] = cid
        changes["customer_name"] = resolved_name
    elif "customer_name" in fields and not customers_from_f2_available():
        cleaned = _clean_text(fields["customer_name"])
        changes["customer_name"] = cleaned or project.customer_name
    elif "customer_id" in fields:
        # Derselbe Kunde wie bisher: nicht erneut gegen F2 prüfen, sonst ließe sich ein Projekt
        # eines inzwischen entfernten Kunden gar nicht mehr ändern.
        changes["customer_id"] = _require_id(fields["customer_id"], "Kunde")

    if "name" in fields:
        changes["name"] = _require_text(fields["name"], "Projektname")
    if "baustelle" in fields:
        changes["baustelle"] = _clean_text(fields["baustelle"])
    if "status" in fields:
        changes["status"] = _require_status(fields["status"])
    if "notes" in fields:
        changes["notes"] = _clean_text(fields["notes"])
    if "archived" in fields:
        if not isinstance(fields["archived"], bool):
            raise ValueError("Archiviert muss wahr oder falsch sein.")
        changes["archived"] = fields["archived"]
    for key in ("start_date", "duration_days", "end_date"):
        if key in fields:
            changes[key] = fields[key]
    return changes


def update_project(
    session: Session,
    project_id: int,
    fields: dict[str, Any],
) -> ProjectInfo:
    """Ändert die übergebenen Felder eines Projekts."""
    project = _get_project_row(session, project_id)
    changes = _clean_changes(session, project, fields)
    start_date, duration_days, end_date = _merge_schedule(project, changes)

    # Ab hier ist alles geprüft.
    if "baustelle" in changes:
        changes["site_address"] = changes.pop("baustelle")
    changes |= {"start_date": start_date, "duration_days": duration_days, "end_date": end_date}
    for attribute, value in changes.items():
        setattr(project, attribute, value)

    session.add(project)
    session.commit()
    session.refresh(project)
    return _to_project_info(session, project)


def set_project_status(session: Session, project_id: int, status: str) -> ProjectInfo:
    """Setzt den Status eines Projekts."""
    return update_project(session, project_id, {"status": status})


def archive_project(session: Session, project_id: int, *, archived: bool = True) -> ProjectInfo:
    """Archiviert ein Projekt oder stellt es wieder her."""
    return update_project(session, project_id, {"archived": archived})


# --- Entwürfe für KI-Werkzeuge (S-09 / S-10, Übergang bis F7) -------------------


def _serialize_payload(data: dict[str, Any]) -> str:
    """Speichert Entwurfsdaten als JSON; `date`-Werte werden als ISO-Text abgelegt."""
    serializable = {
        key: (value.isoformat() if isinstance(value, date) else value)
        for key, value in data.items()
    }
    return json.dumps(serializable, ensure_ascii=False)


def _deserialize_payload(payload_json: str) -> dict[str, Any]:
    """Liest Entwurfsdaten zurück und wandelt Datumsfelder wieder in `date`."""
    data = json.loads(payload_json)
    for key in ("start_date", "end_date"):
        if key in data and isinstance(data[key], str):
            data[key] = date.fromisoformat(data[key])
    return data


def create_project_draft(
    session: Session,
    *,
    customer_id: int,
    name: str,
    baustelle: str = "",
    status: str = STATUS_ANGEFRAGT,
    start_date: date | None = None,
    duration_days: int | None = None,
    end_date: date | None = None,
    notes: str = "",
) -> int:
    """Prüft alle Angaben und legt das neue Projekt als Entwurf an (S-09 / S-10)."""
    cid, resolved_name = _resolve_customer_for_write(session, customer_id)
    cleaned_name = _require_text(name, "Projektname")
    cleaned_site = _clean_text(baustelle)
    checked_status = _require_status(status)
    cleaned_notes = _clean_text(notes)
    start_date, duration_days, end_date = _validate_schedule(start_date, duration_days, end_date)

    payload = {
        "customer_id": cid,
        "customer_name": resolved_name,
        "name": cleaned_name,
        "baustelle": cleaned_site,
        "status": checked_status,
        "start_date": start_date,
        "duration_days": duration_days,
        "end_date": end_date,
        "notes": cleaned_notes,
    }
    draft = ProjectDraft(action="create", project_id=None, payload_json=_serialize_payload(payload))
    session.add(draft)
    session.commit()
    session.refresh(draft)
    return draft.id  # type: ignore[return-value]


def update_project_draft(session: Session, project_id: int, fields: dict[str, Any]) -> int:
    """Prüft die Änderungen und legt sie als Entwurf zu einem bestehenden Projekt an.

    Der Entwurf merkt sich nur die verlangten Änderungen. Berechnete Werte wie das Enddatum
    entstehen erst beim Bestätigen – aus dem Stand, den das Projekt dann hat.
    """
    project = _get_project_row(session, project_id)
    changes = _clean_changes(session, project, fields)
    if not changes:
        raise ValueError("Es wurde kein Feld zum Ändern angegeben.")
    _merge_schedule(project, changes)  # nur prüfen

    draft = ProjectDraft(
        action="update",
        project_id=project.id,
        payload_json=_serialize_payload(changes),
    )
    session.add(draft)
    session.commit()
    session.refresh(draft)
    return draft.id  # type: ignore[return-value]


def set_project_status_draft(session: Session, project_id: int, status: str) -> int:
    """Prüft Projekt und Status und legt die Statusänderung als Entwurf an."""
    project = _get_project_row(session, project_id)
    checked_status = _require_status(status)
    draft = ProjectDraft(
        action="set_status",
        project_id=project.id,
        payload_json=_serialize_payload({"status": checked_status}),
    )
    session.add(draft)
    session.commit()
    session.refresh(draft)
    return draft.id  # type: ignore[return-value]


def archive_project_draft(session: Session, project_id: int, *, archived: bool = True) -> int:
    """Prüft das Projekt und legt das Archivieren als Entwurf an."""
    project = _get_project_row(session, project_id)
    if not isinstance(archived, bool):
        raise ValueError("Archiviert muss wahr oder falsch sein.")
    draft = ProjectDraft(
        action="archive",
        project_id=project.id,
        payload_json=_serialize_payload({"archived": archived}),
    )
    session.add(draft)
    session.commit()
    session.refresh(draft)
    return draft.id  # type: ignore[return-value]


def _close_draft(session: Session, draft_id: int, new_status: str) -> ProjectDraft:
    """Schließt einen offenen Entwurf ab (noch ohne commit).

    Die Änderung greift nur, solange der Entwurf offen ist. So lässt er sich auch bei zwei
    gleichzeitigen Aufrufen nur einmal bestätigen oder verwerfen.
    """
    did = _require_id(draft_id, "Entwurfsnummer")
    draft = session.get(ProjectDraft, did)
    if draft is None:
        raise LookupError(f"Entwurf {did} gibt es nicht.")
    statement = (
        update(ProjectDraft)
        .where(ProjectDraft.id == did, ProjectDraft.status == DRAFT_STATUS_OPEN)
        .values(status=new_status)
    )
    if session.exec(statement).rowcount != 1:
        session.refresh(draft)
        raise ValueError(f"Entwurf {did} ist bereits abgeschlossen ({draft.status}).")
    return draft


def confirm_draft(session: Session, draft_id: int) -> ProjectInfo:
    """Bestätigt einen offenen Entwurf und führt die gespeicherte Aktion aus (für F7).

    Aktion und Abschluss des Entwurfs werden gemeinsam gespeichert. Schlägt die Aktion fehl,
    bleibt der Entwurf offen.
    """
    draft = _close_draft(session, draft_id, DRAFT_STATUS_CONFIRMED)
    try:
        payload = _deserialize_payload(draft.payload_json)
        if draft.action == "create":
            result = create_project(session, **payload)
            draft.project_id = result.id
            session.add(draft)
            session.commit()
        elif draft.action == "update":
            result = update_project(session, draft.project_id, payload)  # type: ignore[arg-type]
        elif draft.action == "set_status":
            result = set_project_status(
                session,
                draft.project_id,  # type: ignore[arg-type]
                payload["status"],
            )
        elif draft.action == "archive":
            result = archive_project(
                session,
                draft.project_id,  # type: ignore[arg-type]
                archived=payload["archived"],
            )
        else:
            raise ValueError(f"Unbekannte Entwurfsaktion „{draft.action}“.")
    except Exception:
        session.rollback()
        raise
    return result


def reject_draft(session: Session, draft_id: int) -> None:
    """Verwirft einen offenen Entwurf ohne Änderung an den Projekten (für F7)."""
    _close_draft(session, draft_id, DRAFT_STATUS_REJECTED)
    session.commit()
