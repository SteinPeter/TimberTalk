# S-09-Metadaten und explizite Registrierung beim gemeinsamen Werkzeugkatalog.
from . import integration, service

REGISTERED = False


def register_available_tools():
    """Beim Start registrieren, sobald der gemeinsame S-09-Service vorhanden ist."""
    global REGISTERED
    decorator = getattr(integration.drafts, "werkzeug", None)
    if not REGISTERED and callable(decorator):
        register_tools(decorator)
        REGISTERED = True


DESCRIPTIONS = {
    "projekt_suchen": "Sucht nach Text, Kunde oder Status. Liefert höchstens zehn Projekte.",
    "projekt_anlegen": "Bereitet ein neues Projekt für einen vorhandenen Kunden vor.",
    "projekt_aendern": "Bereitet Änderungen an den Feldern eines Projekts zur Bestätigung vor.",
    "projekt_status_setzen": "Bereitet einen neuen Projektstatus zur Bestätigung vor.",
    "projekt_archivieren": "Bereitet die Archivierung vor. Projekt und Status bleiben erhalten.",
}
EXAMPLES = {
    "projekt_suchen": {"text": "Berger Carport"},
    "projekt_anlegen": {
        "kunde_id": 4,
        "name": "Carport",
        "baustelle_ort": "Potsdam",
        "dauer_tage": 4,
    },
    "projekt_aendern": {"projekt_id": 12, "feldern": {"baustelle_ort": "Berlin"}},
    "projekt_status_setzen": {"projekt_id": 12, "status": "in_arbeit"},
    "projekt_archivieren": {"projekt_id": 12},
}
SEARCH_OUTPUT = {
    "type": "object",
    "required": ["treffer", "gesamt", "weitere"],
    "properties": {
        "treffer": {
            "type": "array",
            "maxItems": 10,
            "items": {
                "type": "object",
                "required": [
                    "projekt_id",
                    "name",
                    "kunde",
                    "baustelle_ort",
                    "status",
                    "start",
                    "ende",
                ],
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
        },
        "gesamt": {"type": "integer"},
        "weitere": {"type": "boolean"},
    },
}


def tool_definitions():
    return [
        {
            "name": name,
            "beschreibung": DESCRIPTIONS[name],
            "art": "lesen" if name == "projekt_suchen" else "entwurf",
            "schema_ein": model.model_json_schema(),
            "schema_aus": SEARCH_OUTPUT if name == "projekt_suchen" else {"type": "object"},
            "beispiel": EXAMPLES[name],
            "modul": "A",
        }
        for name, model in service.INPUTS.items()
    ]


def register_tools(werkzeug):
    """Vom S-09-Start aufrufen, sobald dessen Aufrufkonvention abgestimmt ist.

    Handler erwarten die serverseitig eingesetzte Session; diese steht nie im JSON-Schema.
    Keine private Ersatzregistrierung und keine doppelten Einträge beim Import.
    """
    handlers = {}
    for definition in tool_definitions():
        name = definition["name"]

        def make_handler(tool_name):
            def handler(session, args, quelle="ki", originaltext=None):
                return service.execute_project_tool(session, tool_name, args, quelle, originaltext)

            return handler

        handlers[name] = werkzeug(**definition)(make_handler(name))
    return handlers
