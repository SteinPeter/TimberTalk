# Projektlogik: lesen, Änderungen vorbereiten und nach S-10-Bestätigung anwenden.
from datetime import timedelta

from pydantic import ValidationError
from sqlalchemy import update
from sqlmodel import select

from . import integration
from .models import (
    ArchiveProject,
    ChangeProject,
    CreateProject,
    Project,
    ProjectStatus,
    SearchProjects,
    SetStatus,
)

INPUTS = {
    "projekt_suchen": SearchProjects,
    "projekt_anlegen": CreateProject,
    "projekt_aendern": ChangeProject,
    "projekt_status_setzen": SetStatus,
    "projekt_archivieren": ArchiveProject,
}


class ProjectError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def error_result(code, message):
    return {"status": "fehler", "fehler": {"code": code, "meldung": message}}


def get_project(session, project_id):
    """S-03: Projekt einschließlich archivierter Projekte; unbekannte ID ergibt None."""
    return session.get(Project, project_id)


def get_customer(session, customer_id):
    """S-03: Nur über den Kunden-Service lesen, keine fremde Tabelle abfragen."""
    return integration.get_customer(session, customer_id)


def checked_customer(session, customer_id):
    customer = get_customer(session, customer_id)
    if customer is None:
        raise ProjectError(
            "kunde_unbekannt", "Der Kunde existiert nicht. Bitte wählen Sie einen Kunden."
        )
    return customer


def checked_project(session, project_id):
    project = get_project(session, project_id)
    if project is None:
        raise ProjectError("projekt_unbekannt", "Das Projekt wurde nicht gefunden.")
    return project


def project_data(session, project):
    customer = get_customer(session, project.customer_id)
    end = None
    if project.start and project.dauer_tage:
        # Kalendertage einschließlich des Starttags; siehe Abstimmung im Steckbrief.
        end = (project.start + timedelta(days=project.dauer_tage - 1)).isoformat()
    return {
        "projekt_id": project.id,
        "name": project.name,
        "kunde_id": project.customer_id,
        "kunde": customer.name if customer else "Kunde nicht verfügbar",
        "baustelle_ort": project.baustelle,
        "status": project.status,
        "start": project.start.isoformat() if project.start else None,
        "ende": end,
        "dauer_tage": project.dauer_tage,
        "archiviert": project.archived,
        "version": project.version,
    }


def list_projects(
    session, text="", customer_id=None, status=None, archived=False, offset=0, limit=10
):
    """Stabile Reihenfolge, wörtliche Textsuche und getrennte Archivansicht."""
    query = select(Project).where(Project.archived == archived)
    if customer_id is not None:
        query = query.where(Project.customer_id == customer_id)
    if status is not None:
        query = query.where(Project.status == ProjectStatus(status).value)
    # casefold funktioniert auch für deutsche Namen; keine SQL-Wildcards aus Benutzereingaben.
    words = text.casefold().split()
    matches = []
    for project in session.exec(query.order_by(Project.id)):
        data = project_data(session, project)
        haystack = f"{data['name']} {data['kunde']} {data['baustelle_ort']}".casefold()
        if all(word in haystack for word in words):
            matches.append(data)
    return {
        "treffer": matches[offset : offset + limit],
        "gesamt": len(matches),
        "weitere": len(matches) > offset + limit,
    }


def list_customer_projects(session, customer_id, archived=False):
    checked_customer(session, customer_id)
    return [
        project_data(session, p)
        for p in session.exec(
            select(Project)
            .where(Project.customer_id == customer_id, Project.archived == archived)
            .order_by(Project.id)
        )
    ]


def customer_options(session):
    return [{"id": c.id, "name": c.name} for c in integration.list_customers(session)]


def validate_action(name, args):
    if name not in INPUTS:
        raise ProjectError("unbekannt", "Dieses Projektwerkzeug ist unbekannt.")
    value = INPUTS[name].model_validate(args)
    if isinstance(value, ChangeProject):
        fields = value.feldern.model_dump(exclude_unset=True)
        if not fields:
            raise ProjectError("ungueltig", "Bitte mindestens ein zu änderndes Feld angeben.")
        for field in ("name", "kunde_id", "baustelle_ort"):
            if field in fields and fields[field] is None:
                raise ProjectError("ungueltig", f"Das Feld {field} darf nicht null sein.")
    return value


def validate_dates(values):
    if values.get("start") and values.get("dauer_tage"):
        try:
            values["start"] + timedelta(days=values["dauer_tage"] - 1)
        except OverflowError as exc:
            raise ProjectError(
                "ungueltig", "Das berechnete Enddatum liegt außerhalb des Bereichs."
            ) from exc


def prepare_action(session, name, args):
    """S-10-Hook: prüft ohne zu schreiben und liefert Vorschau plus Versionsstand.

    S-10 muss expected_version im Entwurf speichern und beim Anwenden unverändert übergeben.
    Dies ist ein expliziter Integrationsvorschlag, noch keine bestehende S-10-Implementierung.
    """
    value = validate_action(name, args)
    if name == "projekt_suchen":
        raise ProjectError("ungueltig", "Lesen benötigt keinen Entwurf.")
    if name == "projekt_anlegen":
        checked_customer(session, value.kunde_id)
        values = {
            "name": value.name,
            "customer_id": value.kunde_id,
            "baustelle": value.baustelle_ort,
            "start": value.start,
            "dauer_tage": value.dauer_tage,
            "status": "angefragt",
            "archived": False,
        }
        old = {}
        expected_version = None
    else:
        project = checked_project(session, value.projekt_id)
        if project.archived:
            raise ProjectError("archiviert", "Archivierte Projekte können nicht geändert werden.")
        checked_customer(session, project.customer_id)
        old = project.model_dump(mode="json")
        expected_version = project.version
        if name == "projekt_aendern":
            fields = value.feldern.model_dump(exclude_unset=True)
            mapping = {"kunde_id": "customer_id", "baustelle_ort": "baustelle"}
            values = {mapping.get(k, k): v for k, v in fields.items()}
            if "customer_id" in values:
                checked_customer(session, values["customer_id"])
        elif name == "projekt_status_setzen":
            values = {"status": value.status.value}
        else:
            values = {"archived": True}
        validate_dates({**project.model_dump(), **values})
    validate_dates(values)
    changes = [
        {
            "objekt": "project",
            "feld": key,
            "alt": old.get(key),
            "neu": val.isoformat() if hasattr(val, "isoformat") else val,
        }
        for key, val in values.items()
    ]
    return {
        "values": values,
        "expected_version": expected_version,
        "zusammenfassung": f"{name}: {values.get('name', old.get('name', 'Projekt'))}",
        "aenderungen": changes,
        "braucht_ausdrueckliche_bestaetigung": False,
    }


def apply_confirmed_action(session, name, args, *, expected_version):
    """Nur vom bestätigenden S-10-Service aufrufen, nie direkt aus einer UI-Route.

    S-10 prüft Rechte, Einmaligkeit und Bestätigung und übernimmt Commit/Rollback und Log.
    Kein eigener Commit: Projektänderung und Änderungsprotokoll bleiben atomar.
    """
    prepared = prepare_action(session, name, args)
    if prepared["expected_version"] != expected_version:
        raise ProjectError(
            "veraltet", "Das Projekt wurde geändert. Bitte einen neuen Entwurf anlegen."
        )
    if name == "projekt_anlegen":
        project = Project(**prepared["values"])
        session.add(project)
        session.flush()
    else:
        project_id = args["projekt_id"]
        statement = (
            update(Project)
            .where(Project.id == project_id, Project.version == expected_version)
            .values(**prepared["values"], version=expected_version + 1)
        )
        if session.execute(statement).rowcount != 1:
            raise ProjectError("veraltet", "Das Projekt wurde gleichzeitig geändert.")
        session.flush()
        session.expire_all()
        project = checked_project(session, project_id)
    return {"projekt_id": project.id, "version": project.version}


def execute_project_tool(session, name, args, quelle="ki", originaltext=None):
    """Handler für den gemeinsamen Katalog; schreibt ausschließlich über create_draft."""
    try:
        if quelle not in ("ui", "ki"):
            raise ProjectError("ungueltig", "Die Quelle muss ui oder ki sein.")
        value = validate_action(name, args)
        if name == "projekt_suchen":
            return {
                "status": "ok",
                "daten": list_projects(session, value.text, value.kunde_id, value.status),
            }
        prepare_action(session, name, args)
        draft = integration.create_draft(
            session, name, value.model_dump(mode="json", exclude_unset=True), quelle, originaltext
        )
        return {"status": "ok", **draft}
    except ValidationError as exc:
        issues = exc.errors()
        missing = next((e for e in issues if e["type"] == "missing"), None)
        if missing:
            field = ".".join(map(str, missing["loc"]))
            return {
                "status": "rueckfrage",
                "rueckfrage": {"feld": field, "frage": f"Bitte {field} angeben.", "optionen": []},
            }
        field = ".".join(map(str, issues[0]["loc"]))
        return error_result("ungueltig", f"Ungültige Eingabe für {field}.")
    except ProjectError as exc:
        return error_result(exc.code, str(exc))
    except integration.DependencyUnavailable as exc:
        return error_result("nicht_verfuegbar", str(exc))


def dispatch_tool(session, request):
    # UI und KI nutzen dieselbe zentrale Prüfung; kein unsicherer lokaler Ersatz.
    try:
        if request.name not in INPUTS:
            return error_result("unbekannt", "Dieses Projektwerkzeug ist unbekannt.")
        return integration.call_tool(
            session, request.name, request.args, request.quelle, request.originaltext
        )
    except integration.DependencyUnavailable as exc:
        return error_result("nicht_verfuegbar", str(exc))


def read_response(function, *args, **kwargs):
    try:
        return {"status": "ok", "daten": function(*args, **kwargs)}
    except ProjectError as exc:
        return error_result(exc.code, str(exc))
    except integration.DependencyUnavailable as exc:
        return error_result("nicht_verfuegbar", str(exc))
