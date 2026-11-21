# Die Werkzeuge dieses Features nach dem Werkzeug-Standard S-09 und der Schnittstelle S-14:
# Aktionen, die die KI aufrufen kann – Material suchen, Material und Fahrten buchen, Kosten
# abfragen. Jedes Werkzeug ruft nur Funktionen aus service.py auf.
#
# Der gemeinsame Baustein `@werkzeug` mit dem Katalog (AP-0.5) liegt noch nicht im Repository.
# Bis dahin gibt es hier einen kleinen Katalog `TOOLS` mit demselben Dekorator und denselben
# Feldern wie in S-09. Sobald der gemeinsame Baustein da ist, wird nur der Dekorator getauscht.
#
# Regeln aus S-09: Namen deutsch in snake_case mit Verb. Geld und Mengen als Dezimal-Text
# („12.50“), Datum als JJJJ-MM-TT, Nummern als Zahl. Fehlt eine Angabe, antwortet das Werkzeug
# mit „rueckfrage“, statt zu raten. Jedes Werkzeug hat ein Beispiel, das ein Test aufruft.

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from sqlmodel import Session

from timbertalk.features.materials import service

ART_LESEN = "lesen"  # führt direkt aus
ART_ENTWURF = "entwurf"  # legt nur einen Entwurf an, der Mensch bestätigt (S-10)


@dataclass(frozen=True)
class Tool:
    """Ein registriertes Werkzeug mit allem, was die KI und der Test darüber wissen müssen."""

    name: str
    beschreibung: str  # 1–2 Sätze für das Modell, deutsch
    art: str
    schema_ein: dict  # JSON-Schema der Eingaben
    schema_aus: dict  # JSON-Schema von „daten“
    beispiel: dict  # {"args": Beispielaufruf, "ergebnis": das dokumentierte Ergebnis}
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
    """Registriert eine Funktion als Werkzeug (so wie @werkzeug in S-09)."""

    def register(function: Callable) -> Callable:
        if name in TOOLS:
            raise RuntimeError(f"Das Werkzeug „{name}“ ist schon registriert.")
        TOOLS[name] = Tool(
            name, beschreibung, art, schema_ein, schema_aus, beispiel, modul, function
        )
        return function

    return register


# --- Antworten --------------------------------------------------------------------


def _ok(**fields) -> dict:
    return {"status": "ok", **fields}


def _rueckfrage(feld: str, frage: str, optionen: list | None = None) -> dict:
    return {
        "status": "rueckfrage",
        "rueckfrage": {"feld": feld, "frage": frage, "optionen": optionen or []},
    }


def _fehler(code: str, meldung: str) -> dict:
    return {"status": "fehler", "fehler": {"code": code, "meldung": meldung}}


def _geld(value: Decimal) -> str:
    return str(service.to_cents(value))


def _material_dict(info) -> dict:
    return {
        "material_id": info.id,
        "name": info.name,
        "einheit": info.einheit,
        "preis": _geld(info.preis) if info.preis is not None else None,
        "gueltig_ab": info.gueltig_ab.isoformat() if info.gueltig_ab else None,
    }


def _datum(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"„{value}“ ist kein Datum. Erwartet wird JJJJ-MM-TT.") from None


def _dezimal(value, label: str) -> Decimal:
    try:
        return Decimal(str(value))
    except InvalidOperation:
        raise ValueError(f"{label}: „{value}“ ist keine Zahl.") from None


# --- Die Werkzeuge ----------------------------------------------------------------


@werkzeug(
    name="material_suchen",
    beschreibung="Sucht Material im Materialstamm nach Name oder Kategorie und nennt den "
    "aktuellen Preis. Höchstens 10 Treffer.",
    art=ART_LESEN,
    schema_ein={
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    },
    schema_aus={
        "type": "object",
        "properties": {
            "treffer": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "material_id": {"type": "integer"},
                        "name": {"type": "string"},
                        "einheit": {"type": "string"},
                        "preis": {"type": ["string", "null"]},
                        "gueltig_ab": {"type": ["string", "null"]},
                    },
                },
            }
        },
    },
    beispiel={
        "args": {"text": "vollholz"},
        "ergebnis": {
            "status": "ok",
            "daten": {
                "treffer": [
                    {
                        "material_id": 1,
                        "name": "Konstruktionsvollholz C24",
                        "einheit": "m³",
                        "preis": "450.00",
                        "gueltig_ab": "2026-01-01",
                    }
                ]
            },
        },
    },
)
def material_suchen(session: Session, text: str) -> dict:
    treffer = [_material_dict(info) for info in service.search_materials(session, text)]
    return _ok(daten={"treffer": treffer})


@werkzeug(
    name="material_buchen",
    beschreibung="Bucht Material auf ein Projekt – als Entwurf, den der Zimmerer noch bestätigt. "
    "Menge als Dezimal-Text, Einheit wie im Materialstamm.",
    art=ART_ENTWURF,
    schema_ein={
        "type": "object",
        "properties": {
            "projekt_id": {"type": "integer"},
            "datum": {"type": "string", "format": "date"},
            "positionen": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "material_id": {"type": "integer"},
                        "menge": {"type": "string"},
                        "einheit": {"type": "string"},
                    },
                    "required": ["material_id", "menge", "einheit"],
                },
            },
        },
        "required": ["projekt_id", "datum", "positionen"],
    },
    schema_aus={"type": "object", "properties": {}},
    beispiel={
        "args": {
            "projekt_id": 12,
            "datum": "2026-12-03",
            "positionen": [{"material_id": 1, "menge": "2.5", "einheit": "m³"}],
        },
        "ergebnis": {"status": "ok", "entwurf_id": 1},
    },
)
def material_buchen(session: Session, projekt_id: int, datum: str, positionen: list) -> dict:
    try:
        entwurf_id = service.book_material_draft(session, projekt_id, positionen, _datum(datum))
    except LookupError:
        # Material unbekannt: die Nummer ist falsch, also die vorhandenen Materialien anbieten.
        optionen = [_material_dict(info) for info in service.list_materials(session)]
        return _rueckfrage(
            "positionen",
            "Dieses Material kenne ich nicht. Welches ist gemeint?",
            optionen[: service.MAX_SEARCH_RESULTS],
        )
    return _ok(entwurf_id=entwurf_id)


@werkzeug(
    name="fahrt_buchen",
    beschreibung="Bucht eine Fahrt (Strecke in km) auf ein Projekt – als Entwurf, den der "
    "Zimmerer noch bestätigt.",
    art=ART_ENTWURF,
    schema_ein={
        "type": "object",
        "properties": {
            "projekt_id": {"type": "integer"},
            "datum": {"type": "string", "format": "date"},
            "km": {"type": "string"},
        },
        "required": ["projekt_id", "datum", "km"],
    },
    schema_aus={"type": "object", "properties": {}},
    beispiel={
        "args": {"projekt_id": 12, "datum": "2026-12-03", "km": "40"},
        "ergebnis": {"status": "ok", "entwurf_id": 1},
    },
)
def fahrt_buchen(session: Session, projekt_id: int, datum: str, km: str) -> dict:
    entwurf_id = service.book_travel_draft(
        session, projekt_id, _dezimal(km, "Strecke"), _datum(datum)
    )
    return _ok(entwurf_id=entwurf_id)


@werkzeug(
    name="projekt_kosten",
    beschreibung="Nennt die Kosten eines Projekts in Euro netto: Stunden, Material, Fahrten "
    "und die Summe. Nur bestätigte Buchungen zählen.",
    art=ART_LESEN,
    schema_ein={
        "type": "object",
        "properties": {"projekt_id": {"type": "integer"}},
        "required": ["projekt_id"],
    },
    schema_aus={
        "type": "object",
        "properties": {
            "stunden": {"type": "string"},
            "material": {"type": "string"},
            "fahrten": {"type": "string"},
            "gesamt_netto": {"type": "string"},
        },
    },
    beispiel={
        "args": {"projekt_id": 12},
        "ergebnis": {
            "status": "ok",
            "daten": {
                "stunden": "0.00",
                "material": "900.00",
                "fahrten": "5.00",
                "gesamt_netto": "905.00",
            },
        },
    },
)
def projekt_kosten(session: Session, projekt_id: int) -> dict:
    costs = service.project_costs(session, projekt_id)
    return _ok(
        daten={
            "stunden": _geld(costs.hours),
            "material": _geld(costs.material),
            "fahrten": _geld(costs.travel),
            "gesamt_netto": _geld(costs.total_net),
        }
    )


# --- Aufrufen ---------------------------------------------------------------------


def call_tool(session: Session, name: str, args: dict) -> dict:
    """Ruft ein Werkzeug mit seinen Eingaben auf und gibt immer eine Antwort mit `status` zurück.

    Das ist die kleine Fassung des `call_tool` aus S-09: unbekanntes Werkzeug → fehler
    „unbekannt“, fehlende Pflichtangabe → rueckfrage, unpassende Angabe → fehler „ungueltig“.
    """
    tool = TOOLS.get(name)
    if tool is None:
        return _fehler("unbekannt", f"Ein Werkzeug „{name}“ gibt es nicht.")
    for feld in tool.schema_ein.get("required", []):
        if feld not in args:
            return _rueckfrage(feld, f"Es fehlt die Angabe „{feld}“.")
    try:
        return tool.function(session, **args)
    except (ValueError, LookupError) as error:
        return _fehler("ungueltig", str(error))
