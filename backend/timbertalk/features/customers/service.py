# Die Logik des Features „Kunden“ als einfache Funktionen.
# Jede Funktion bekommt als ersten Parameter die Datenbank-Sitzung: session: Session.
# Andere Features benutzen dieses Feature nur über die Funktionen in dieser Datei.
#
# Für F3 (Projekte) wichtig: get_customer() und list_customers() liefern Kunden mit `id` (ganze
# Zahl) und `name`; get_customer() gibt bei unbekannter Nummer None zurück.
# Die KI-Werkzeuge (S-09) und die Bestätigung (S-10) sind noch nicht angeschlossen; die Funktionen
# hier sind so geschnitten, dass ein Werkzeug sie später direkt aufrufen kann (Steckbrief F2).

import csv
import io

from sqlmodel import Session, select

from timbertalk.features.customers.models import (
    Customer,
    CustomerInput,
    CustomerUpdate,
    now_utc,
)


class CustomerError(ValueError):
    """Ein fachlicher Fehler mit kurzem Code (für API und Werkzeuge) und deutscher Meldung."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


# --- Hilfen ---------------------------------------------------------------------------


def _clean(data: CustomerInput) -> CustomerInput:
    """Entfernt Leerzeichen am Anfang und Ende jedes Textfelds."""
    values = data.model_dump()
    for field, value in values.items():
        if isinstance(value, str):
            values[field] = value.strip()
    return CustomerInput(**values)


def _display_name(data: CustomerInput) -> str:
    """Der Anzeigename: Firmenname bei Firmen, sonst „Vorname Nachname“."""
    if data.customer_type == "business":
        return data.company_name
    return f"{data.first_name} {data.last_name}".strip()


def _search_text(customer: Customer) -> str:
    """Der Text, in dem die Suche sucht – kleingeschrieben, auch für Umlaute (casefold)."""
    parts = [customer.name, customer.zip, customer.city, customer.phone, customer.email]
    return " ".join(part for part in parts if part).casefold()


def _apply(customer: Customer, data: CustomerInput) -> None:
    """Überträgt geprüfte Angaben auf den Kunden und bildet Name und Suchtext neu."""
    for field, value in data.model_dump().items():
        setattr(customer, field, value)
    customer.name = _display_name(data)
    customer.search_text = _search_text(customer)


def require_customer(session: Session, customer_id: int) -> Customer:
    """Holt den Kunden oder meldet mit CustomerError „nicht_gefunden“, dass es ihn nicht gibt.

    Anders als get_customer() gibt diese Funktion nie None zurück – für die API (404).
    """
    customer = session.get(Customer, customer_id)
    if customer is None:
        raise CustomerError("nicht_gefunden", f"Kunde {customer_id} gibt es nicht.")
    return customer


def _save(session: Session, customer: Customer) -> Customer:
    """Speichert den Kunden und liest ihn frisch aus der Datenbank zurück."""
    session.add(customer)
    session.commit()
    session.refresh(customer)
    return customer


# --- Prüfen ---------------------------------------------------------------------------


def check_customer_input(data: CustomerInput) -> CustomerInput:
    """Prüft die Angaben, ohne etwas zu speichern, und gibt sie bereinigt zurück.

    Pflicht ist bei Privatkunden der Nachname, bei Firmen der Firmenname (Steckbrief D7).
    Gedacht auch als Vorschau für eine spätere Bestätigung (S-10).
    """
    cleaned = _clean(data)
    if cleaned.customer_type == "business" and not cleaned.company_name:
        raise CustomerError("ungueltig", "Bei einer Firma ist der Firmenname Pflicht.")
    if cleaned.customer_type == "private" and not cleaned.last_name:
        raise CustomerError("ungueltig", "Bei einem Privatkunden ist der Nachname Pflicht.")
    return cleaned


# --- Lesen ----------------------------------------------------------------------------


def get_customer(session: Session, customer_id: int) -> Customer | None:
    """Ein Kunde nach Nummer – auch archivierte. Unbekannte Nummer: None."""
    return session.get(Customer, customer_id)


def list_customers(
    session: Session, query: str | None = None, include_archived: bool = False
) -> list[Customer]:
    """Kunden alphabetisch nach Name, ohne archivierte, außer include_archived ist gesetzt.

    query sucht in Name, PLZ, Ort, Telefon und E-Mail, ohne Rücksicht auf Groß- und
    Kleinschreibung. Mehrere Wörter müssen alle vorkommen („beispiel musterstadt“).
    """
    statement = select(Customer)
    if not include_archived:
        statement = statement.where(Customer.archived == False)  # noqa: E712
    for word in (query or "").casefold().split():
        # autoescape: % und _ im Suchwort sind normale Zeichen, keine Platzhalter.
        statement = statement.where(Customer.search_text.contains(word, autoescape=True))
    customers = session.exec(statement).all()
    return sorted(customers, key=lambda customer: (customer.name.casefold(), customer.id))


# --- Schreiben ------------------------------------------------------------------------


def create_customer(session: Session, data: CustomerInput) -> Customer:
    """Legt einen Kunden an und gibt ihn mit seiner neuen Nummer zurück."""
    cleaned = check_customer_input(data)
    customer = Customer(name="")
    _apply(customer, cleaned)
    return _save(session, customer)


def check_customer_update(
    session: Session, customer_id: int, changes: CustomerUpdate
) -> CustomerInput:
    """Wie sähe der Kunde nach der Änderung aus? Prüft alles, speichert aber nichts.

    Gedacht auch als Vorschau für eine spätere Bestätigung (S-10).
    """
    customer = require_customer(session, customer_id)
    current = CustomerInput.model_validate(customer, from_attributes=True).model_dump()
    current.update(changes.model_dump(exclude_unset=True, exclude_none=True))
    return check_customer_input(CustomerInput(**current))


def update_customer(session: Session, customer_id: int, changes: CustomerUpdate) -> Customer:
    """Ändert die mitgeschickten Felder. Danach müssen die Pflichtangaben noch stimmen."""
    cleaned = check_customer_update(session, customer_id, changes)
    customer = require_customer(session, customer_id)
    _apply(customer, cleaned)
    customer.updated_at = now_utc()
    return _save(session, customer)


def archive_customer(session: Session, customer_id: int) -> Customer:
    """Blendet den Kunden aus. Seine Daten bleiben unverändert erhalten."""
    customer = require_customer(session, customer_id)
    customer.archived = True
    customer.updated_at = now_utc()
    return _save(session, customer)


def restore_customer(session: Session, customer_id: int) -> Customer:
    """Holt einen archivierten Kunden zurück in die Liste."""
    customer = require_customer(session, customer_id)
    customer.archived = False
    customer.updated_at = now_utc()
    return _save(session, customer)


def delete_customer(session: Session, customer_id: int) -> None:
    """Löscht einen Kunden endgültig.

    Vorläufige Regel (Steckbrief D3): nur archivierte Kunden. Ob zusätzlich Projekte geprüft
    werden und wie eine DSGVO-Löschung abläuft, ist noch offen.
    """
    customer = require_customer(session, customer_id)
    if not customer.archived:
        raise CustomerError(
            "nicht_archiviert",
            "Nur archivierte Kunden lassen sich löschen. Bitte erst archivieren.",
        )
    session.delete(customer)
    session.commit()


# --- Exportieren ----------------------------------------------------------------------

# Spalten der CSV-Datei: Überschrift → Wert je Kunde. Vorläufig, bis S-11 geklärt ist (D4).
EXPORT_COLUMNS = {
    "Kundennummer": lambda c: str(c.id),
    "Art": lambda c: "Firma" if c.customer_type == "business" else "Privat",
    "Name": lambda c: c.name,
    "Firma": lambda c: c.company_name,
    "Vorname": lambda c: c.first_name,
    "Nachname": lambda c: c.last_name,
    "Straße": lambda c: c.street,
    "PLZ": lambda c: c.zip,
    "Ort": lambda c: c.city,
    "Telefon": lambda c: c.phone,
    "E-Mail": lambda c: c.email,
    "Notiz": lambda c: c.note,
    "Archiviert": lambda c: "ja" if c.archived else "nein",
}

# Beginnt ein Wert mit einem dieser Zeichen, würde Excel ihn als Formel ausführen.
_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def _safe_cell(value: str) -> str:
    """Setzt ein ' vor Werte, die Excel sonst als Formel lesen würde (z. B. „=…“)."""
    return f"'{value}" if value.startswith(_FORMULA_START) else value


def export_customers_csv(session: Session, include_archived: bool = False) -> bytes:
    """Die Kundenliste als CSV-Datei für Excel: Semikolon, UTF-8 mit BOM (für Umlaute)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    writer.writerow(EXPORT_COLUMNS.keys())
    for customer in list_customers(session, include_archived=include_archived):
        writer.writerow(_safe_cell(column(customer)) for column in EXPORT_COLUMNS.values())
    return buffer.getvalue().encode("utf-8-sig")
