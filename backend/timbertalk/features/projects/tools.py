# Die Werkzeuge des Features „Projekte“ (F3) nach Werkzeug-Standard S-09 und Schnittstelle S-12:
# Projekte suchen, anlegen, ändern, Status setzen und archivieren.
# Jedes Werkzeug ruft nur Funktionen aus service.py auf.
#
# Bis der gemeinsame Dekorator `@werkzeug` im Kern (AP-0.5 / F7) im Repository liegt, nutzt
# dieses Feature einen kleinen eigenen Katalog `TOOLS` mit exakt denselben Feldern wie in S-09.
# Sobald der gemeinsame Baustein da ist, wird nur der Dekorator getauscht.

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlmodel import Session

from timbertalk.features.projects import service
from timbertalk.features.projects.models import PROJECT_STATUSES, ProjectInfo

KIND_READ = "lesen"  # führt direkt aus
KIND_DRAFT = "entwurf"  # legt nur einen Entwurf an, der Mensch bestätigt (S-10)


@dataclass(frozen=True)
class Tool:
    """Ein registriertes Werkzeug mit Beschreibung, JSON-Schemata und prüfbarem Beispiel (S-09)."""

    name: str
    beschreibung: str
    art: str
    schema_ein: dict
    schema_aus: dict
    beispiel: dict
    modul: str
    function: Callable


# Der Katalog: Name → Werkzeug.
TOOLS: dict[str, Tool] = {}


def werkzeug(
    *,
    name: str,
    beschreibung: str,
    art: str,
    schema_ein: dict,
    schema_aus: dict,
    beispiel: dict,
    modul: str = "A",
):
    """Registriert eine Funktion als Werkzeug nach dem Standard S-09."""

    def register(function: Callable) -> Callable:
        if name in TOOLS:
            raise RuntimeError(f"Das Werkzeug „{name}“ ist schon registriert.")
        TOOLS[name] = Tool(
            name, beschreibung, art, schema_ein, schema_aus, beispiel, modul, function
        )
        return function

    return register


# --- Antworten und Umwandlungen -------------------------------------------------


def _ok(**fields) -> dict:
    return {"status": "ok", **fields}


def _question(field: str, question: str, options: list | None = None) -> dict:
    """Antwort mit Rückfrage nach S-09: Feld, Frage und mögliche Antworten."""
    return {
        "status": "rueckfrage",
        "rueckfrage": {"feld": field, "frage": question, "optionen": options or []},
    }


def _error(code: str, message: str) -> dict:
    return {"status": "fehler", "fehler": {"code": code, "meldung": message}}


def _parse_date(value: str | None) -> date | None:
    """Liest ein Datum im Format JJJJ-MM-TT (S-09)."""
    if value is None:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    raise ValueError(f"„{value}“ ist kein Datum. Erwartet wird JJJJ-MM-TT.")


# Die Typnamen aus JSON-Schema und was sie in Python sind.
_JSON_TYPES: dict[str, type] = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "boolean": bool,
    "null": type(None),
}


def schema_violation(value: Any, schema: dict, field: str = "") -> str | None:
    """Prüft einen Wert gegen ein JSON-Schema und nennt den ersten Verstoß mit Feldnamen.

    Kann nur, was die Schemata dieser Datei benutzen: type, enum, properties,
    additionalProperties und items. Eine Bibliothek dafür gibt es im Projekt nicht.
    """
    label = f"„{field}“" if field else "Die Eingabe"
    allowed = schema.get("type")
    if allowed is not None:
        names = allowed if isinstance(allowed, list) else [allowed]
        # `type(...) is` statt isinstance, weil True in Python auch eine Zahl wäre.
        if not any(type(value) is _JSON_TYPES[name] for name in names):
            return f"{label} hat den falschen Typ, erwartet: {' oder '.join(names)}."
    if "enum" in schema and value not in schema["enum"]:
        choices = ", ".join(schema["enum"])
        return f"{label} muss einer dieser Werte sein: {choices}."
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for key, item in value.items():
            path = f"{field}.{key}" if field else key
            if key in properties:
                violation = schema_violation(item, properties[key], path)
                if violation:
                    return violation
            elif schema.get("additionalProperties") is False:
                return f"„{path}“ ist kein bekanntes Feld."
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            violation = schema_violation(item, schema["items"], f"{field}[{index}]")
            if violation:
                return violation
    return None


def _project_treffer(info: ProjectInfo) -> dict:
    """Formatiert ein Projekt für die Trefferliste von `projekt_suchen` (S-12)."""
    return {
        "projekt_id": info.id,
        "name": info.name,
        "kunde": info.customer_name,
        "baustelle_ort": info.baustelle,
        "status": info.status,
        "start": info.start_date.isoformat() if info.start_date else None,
        "ende": info.end_date.isoformat() if info.end_date else None,
    }


# Übersetzt deutsche Werkzeug-Feldnamen aus `projekt_aendern` in die Feldnamen von `service.py`.
_UPDATE_FIELD_MAP = {
    "kunde_id": "customer_id",
    "name": "name",
    "baustelle_ort": "baustelle",
    "status": "status",
    "start": "start_date",
    "dauer_tage": "duration_days",
    "ende": "end_date",
    "notiz": "notes",
    "archiviert": "archived",
}


# --- Die Werkzeuge (S-12 + LA-03) -----------------------------------------------


@werkzeug(
    name="projekt_suchen",
    beschreibung="Sucht Projekte nach Text (Projektname, Kunde oder Baustelle), Kundennummer "
    "oder Status. Liefert höchstens 10 Treffer.",
    art=KIND_READ,
    schema_ein={
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "kunde_id": {"type": "integer"},
            "status": {"type": "string", "enum": list(PROJECT_STATUSES)},
            "archivierte_anzeigen": {"type": "boolean"},
        },
        "additionalProperties": False,
    },
    schema_aus={
        "type": "object",
        "properties": {
            "treffer": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "projekt_id": {"type": "integer"},
                        "name": {"type": "string"},
                        "kunde": {"type": "string"},
                        "baustelle_ort": {"type": "string"},
                        "status": {"type": "string"},
                        "start": {"type": ["string", "null"]},
                        "ende": {"type": ["string", "null"]},
                    },
                },
            }
        },
    },
    beispiel={
        "args": {"text": "Berger Carport"},
        "ergebnis": {
            "status": "ok",
            "daten": {
                "treffer": [
                    {
                        "projekt_id": 1,
                        "name": "Carport",
                        "kunde": "Berger",
                        "baustelle_ort": "Potsdam",
                        "status": "geplant",
                        "start": "2026-12-01",
                        "ende": "2026-12-04",
                    }
                ]
            },
        },
    },
)
def projekt_suchen(
    session: Session,
    text: str | None = None,
    kunde_id: int | None = None,
    status: str | None = None,
    archivierte_anzeigen: bool = False,
) -> dict:
    hits = service.list_projects(
        session,
        text=text,
        customer_id=kunde_id,
        status=status,
        include_archived=archivierte_anzeigen,
        limit=service.MAX_SEARCH_RESULTS,
    )
    return _ok(daten={"treffer": [_project_treffer(info) for info in hits]})


@werkzeug(
    name="projekt_anlegen",
    beschreibung="Legt ein neues Projekt zu einem Kunden als Entwurf an, den der Zimmerer "
    "noch bestätigt. Ohne Kundennummer wird zurückgefragt.",
    art=KIND_DRAFT,
    schema_ein={
        "type": "object",
        "properties": {
            "kunde_id": {"type": "integer"},
            "name": {"type": "string"},
            "baustelle_ort": {"type": "string"},
            "start": {"type": "string", "format": "date"},
            "dauer_tage": {"type": "integer"},
        },
        "required": ["kunde_id", "name"],
        "additionalProperties": False,
    },
    schema_aus={"type": "object", "properties": {}},
    beispiel={
        "args": {
            "kunde_id": 4,
            "name": "Carport",
            "baustelle_ort": "Potsdam",
            "dauer_tage": 4,
        },
        "ergebnis": {"status": "ok", "entwurf_id": 1},
    },
)
def projekt_anlegen(
    session: Session,
    kunde_id: int,
    name: str,
    baustelle_ort: str = "",
    start: str | None = None,
    dauer_tage: int | None = None,
) -> dict:
    draft_id = service.create_project_draft(
        session,
        customer_id=kunde_id,
        name=name,
        baustelle=baustelle_ort,
        start_date=_parse_date(start),
        duration_days=dauer_tage,
    )
    return _ok(entwurf_id=draft_id)


@werkzeug(
    name="projekt_aendern",
    beschreibung="Ändert Felder eines bestehenden Projekts (z. B. Name, Baustelle, Zeitraum "
    "oder Notiz) als Entwurf zur Bestätigung.",
    art=KIND_DRAFT,
    schema_ein={
        "type": "object",
        "properties": {
            "projekt_id": {"type": "integer"},
            "felder": {
                "type": "object",
                "properties": {
                    "kunde_id": {"type": "integer"},
                    "name": {"type": "string"},
                    "baustelle_ort": {"type": "string"},
                    "status": {"type": "string", "enum": list(PROJECT_STATUSES)},
                    "start": {"type": ["string", "null"], "format": "date"},
                    "dauer_tage": {"type": ["integer", "null"]},
                    "ende": {"type": ["string", "null"], "format": "date"},
                    "notiz": {"type": "string"},
                    "archiviert": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
        },
        "required": ["projekt_id", "felder"],
        "additionalProperties": False,
    },
    schema_aus={"type": "object", "properties": {}},
    beispiel={
        "args": {"projekt_id": 1, "felder": {"baustelle_ort": "Werder"}},
        "ergebnis": {"status": "ok", "entwurf_id": 1},
    },
)
def projekt_aendern(session: Session, projekt_id: int, felder: dict[str, Any]) -> dict:
    if not felder:
        return _question("felder", "Welche Angaben sollen am Projekt geändert werden?")
    mapped: dict[str, Any] = {}
    for key, value in felder.items():
        target = _UPDATE_FIELD_MAP[key]  # unbekannte Felder hat call_tool schon abgelehnt
        mapped[target] = _parse_date(value) if target in ("start_date", "end_date") else value
    draft_id = service.update_project_draft(session, projekt_id, mapped)
    return _ok(entwurf_id=draft_id)


@werkzeug(
    name="projekt_status_setzen",
    beschreibung="Setzt den Status eines Projekts (angefragt, geplant, in_arbeit, "
    "abgeschlossen oder abgerechnet) als Entwurf zur Bestätigung.",
    art=KIND_DRAFT,
    schema_ein={
        "type": "object",
        "properties": {
            "projekt_id": {"type": "integer"},
            "status": {"type": "string", "enum": list(PROJECT_STATUSES)},
        },
        "required": ["projekt_id", "status"],
        "additionalProperties": False,
    },
    schema_aus={"type": "object", "properties": {}},
    beispiel={
        "args": {"projekt_id": 1, "status": "in_arbeit"},
        "ergebnis": {"status": "ok", "entwurf_id": 1},
    },
)
def projekt_status_setzen(session: Session, projekt_id: int, status: str) -> dict:
    draft_id = service.set_project_status_draft(session, projekt_id, status)
    return _ok(entwurf_id=draft_id)


@werkzeug(
    name="projekt_archivieren",
    beschreibung="Archiviert ein Projekt (oder stellt es mit archiviert=false wieder her) – "
    "als Entwurf zur Bestätigung.",
    art=KIND_DRAFT,
    schema_ein={
        "type": "object",
        "properties": {
            "projekt_id": {"type": "integer"},
            "archiviert": {"type": "boolean"},
        },
        "required": ["projekt_id"],
        "additionalProperties": False,
    },
    schema_aus={"type": "object", "properties": {}},
    beispiel={
        "args": {"projekt_id": 1},
        "ergebnis": {"status": "ok", "entwurf_id": 1},
    },
)
def projekt_archivieren(session: Session, projekt_id: int, archiviert: bool = True) -> dict:
    draft_id = service.archive_project_draft(session, projekt_id, archived=archiviert)
    return _ok(entwurf_id=draft_id)


# --- Aufrufen -------------------------------------------------------------------


def call_tool(session: Session, name: str, args: dict) -> dict:
    """Ruft ein Werkzeug mit seinen Eingaben auf und gibt immer eine Antwort mit `status` zurück.

    Entspricht `call_tool` aus S-09: unbekanntes Werkzeug → fehler „unbekannt“, fehlende
    Pflichtangabe → rueckfrage, Verstoß gegen das Schema → fehler „ungueltig“ mit Feldname.
    Eine freiwillige Angabe mit dem Wert null gilt als nicht gemacht.
    """
    tool = TOOLS.get(name)
    if tool is None:
        return _error("unbekannt", f"Ein Werkzeug „{name}“ gibt es nicht.")
    if not isinstance(args, dict):
        return _error("ungueltig", "Die Eingaben müssen ein Objekt mit benannten Feldern sein.")

    for field in tool.schema_ein.get("required", []):
        value = args.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            return _question(field, f"Es fehlt die Angabe „{field}“.")

    given = {key: value for key, value in args.items() if value is not None}
    violation = schema_violation(given, tool.schema_ein)
    if violation:
        return _error("ungueltig", violation)

    try:
        return tool.function(session, **given)
    except (ValueError, LookupError) as error:
        return _error("ungueltig", str(error))
