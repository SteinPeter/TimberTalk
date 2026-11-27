# Vorbereitung der KI-Werkzeuge aus S-11 (Entwurf Version 0.1) für das Feature „Kunden“.
#
# Diese Datei übersetzt nur die Eingaben aus S-11 (deutsche Namen) in die Service-Funktionen.
# Sie ist KEIN Werkzeugkatalog und registriert nichts: Das macht der gemeinsame Katalog aus S-09
# (AP-0.5, Feature `drafts`), den es noch nicht gibt. Sie bestätigt auch nichts: Schreibende
# Werkzeuge („entwurf“) bestätigt S-10. Hier gibt es deshalb nur Lesen und Prüfen ohne Speichern.
#
# Stand der S-11-Werkzeuge für Kunden (Steckbrief F2, Abschnitt KI-Werkzeuge):
#   kunde_suchen      (lesen)   text                     → search_customers()      vorbereitet
#   kunde_aendern     (entwurf) kunde_id, felder         → preview_customer_change() nur Vorschau
#   kunde_archivieren (entwurf) kunde_id                 → preview_customer_archive() nur Vorschau
#   kunde_anlegen     (entwurf) name, strasse, plz, …    → OFFEN (D9): S-11 kennt nur `name`,
#                                                          F2 unterscheidet Privat/Firma.
# Offen für alle: Antwortformat, JSON-Schema, Registrierung (S-09), Bestätigung (S-10).

from sqlmodel import Session

from timbertalk.features.customers import service
from timbertalk.features.customers.models import Customer, CustomerInput, CustomerUpdate

# Feldnamen aus S-11 → Feldnamen im Kundenmodell. `name` fehlt mit Absicht: Der Anzeigename wird
# aus Vor- und Nachname bzw. Firmenname gebildet (Steckbrief D9, mit S-11 zu klären).
S11_FIELDS = {
    "strasse": "street",
    "plz": "zip",
    "ort": "city",
    "telefon": "phone",
    "email": "email",
}


def changes_from_s11(fields: dict) -> CustomerUpdate:
    """Übersetzt `felder` aus S-11 in eine CustomerUpdate. Unbekannte Felder werden abgewiesen.

    Werte prüft pydantic (Text, Höchstlänge); falsche Werte → ValidationError.
    """
    if not isinstance(fields, dict) or not fields:
        raise service.CustomerError("ungueltig", "Bitte mindestens ein zu änderndes Feld angeben.")
    if "name" in fields:
        raise service.CustomerError(
            "offen",
            "Den Namen über ein Werkzeug zu ändern ist noch nicht festgelegt (S-11, D9).",
        )
    unknown = sorted(set(fields) - set(S11_FIELDS))
    if unknown:
        raise service.CustomerError(
            "ungueltig", f"Diese Felder kennt das Werkzeug nicht: {', '.join(unknown)}."
        )
    return CustomerUpdate(**{S11_FIELDS[key]: value for key, value in fields.items()})


def search_customers(session: Session, text: str) -> list[Customer]:
    """kunde_suchen: Kunden zum Suchtext, ohne archivierte. Antwortformat: offen (S-09)."""
    return service.list_customers(session, query=text)


def preview_customer_change(session: Session, customer_id: int, fields: dict) -> CustomerInput:
    """kunde_aendern: zeigt, wie der Kunde nach der Änderung aussähe. Speichert NICHTS.

    Nach Bestätigung durch S-10 wäre dann service.update_customer() mit
    changes_from_s11(fields) aufzurufen – wie S-10 das tut, ist noch nicht festgelegt.
    """
    return service.check_customer_update(session, customer_id, changes_from_s11(fields))


def preview_customer_archive(session: Session, customer_id: int) -> Customer:
    """kunde_archivieren: prüft, dass es den Kunden gibt, und gibt ihn zurück. Speichert NICHTS.

    Nach Bestätigung durch S-10 wäre service.archive_customer() aufzurufen.
    """
    return service.require_customer(session, customer_id)
