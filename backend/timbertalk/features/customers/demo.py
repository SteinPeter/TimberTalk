# Demo-Datensatz (LD-09): Kunden einer erfundenen Zimmerei für Vorführungen.
#
# Alle Namen, Adressen, Telefonnummern und E-Mail-Adressen sind erfunden:
# - Postleitzahlen beginnen mit 00 – die gibt es in Deutschland nicht.
# - Telefonnummern beginnen mit 0000 – keine echte Vorwahl.
# - E-Mail-Adressen nur unter example.com, example.org und example.net (für Beispiele reserviert).
#
# Laden in eine EIGENE Datei, nie in die echte Datenbank (im Ordner backend/):
#   uv run python -m timbertalk.features.customers.demo data/demo.db
# Vorführen mit dieser Datei:
#   PowerShell: $env:TIMBERTALK_DATABASE_URL = "sqlite:///data/demo.db"; uv run timbertalk
#   Bash:       TIMBERTALK_DATABASE_URL=sqlite:///data/demo.db uv run timbertalk
#
# Die Daten werden über service.py angelegt, also genauso geprüft wie Eingaben aus der Oberfläche.

import argparse
import sys
from pathlib import Path

from sqlmodel import Session, SQLModel, func, select

from timbertalk.db import make_engine
from timbertalk.features.customers import service
from timbertalk.features.customers.models import Customer, CustomerInput
from timbertalk.settings import DATA_DIR

# Die erfundene Zimmerei, für die die Kunden gedacht sind (nur zur Erklärung in der Vorführung).
DEMO_COMPANY = "Zimmerei Musterholz (erfunden)"

# Die echte Datenbank: Dorthin werden Demo-Daten nie geladen.
REAL_DATABASE = DATA_DIR / "timbertalk.db"

# Die Kunden in fester Reihenfolge, damit jeder Ladevorgang dieselben Nummern ergibt.
# `archived: True` heißt: Der Kunde wird nach dem Anlegen archiviert.
DEMO_CUSTOMERS: list[dict] = [
    {
        "customer_type": "private",
        "first_name": "Erika",
        "last_name": "Mustermann",
        "street": "Musterweg 1",
        "zip": "00101",
        "city": "Musterstadt",
        "phone": "0000 100001",
        "email": "erika.mustermann@example.com",
        "note": "Dachstuhl Einfamilienhaus, Angebot angefragt.",
    },
    {
        "customer_type": "private",
        "first_name": "Max",
        "last_name": "Mustermann",
        "street": "Musterweg 3",
        "zip": "00101",
        "city": "Musterstadt",
        "phone": "0000 100002",
        "email": "max.mustermann@example.com",
        "note": "Nachbar von Erika Mustermann, gleicher Nachname (Suchfall).",
    },
    {
        "customer_type": "private",
        "first_name": "Jürgen",
        "last_name": "Übermuster",
        "street": "Große Straße 12",
        "zip": "00202",
        "city": "Übersee-Muster",
        "phone": "0000 200001",
        "email": "j.uebermuster@example.org",
        "note": "Carport aus Lärche. Umlaute und ß (Suchfall).",
    },
    {
        "customer_type": "private",
        "first_name": "Ana-Lena",
        "last_name": "Beispiel-Özdemir",
        "street": "Am Fiktivpark 5a",
        "zip": "00303",
        "city": "Beispielhausen",
        "phone": "0000 300001",
        "email": "ana-lena@example.net",
        "note": "Doppelname mit Bindestrich (Suchfall).",
    },
    {
        "customer_type": "private",
        "first_name": "Paul",
        "last_name": "Platzhalter",
        "street": "Alte Gasse 2",
        "zip": "00404",
        "city": "Fiktivingen",
        "phone": "0000 400001",
        "email": "paul.platzhalter@example.com",
        "note": "Auftrag 2025 abgeschlossen, Kunde archiviert.",
        "archived": True,
    },
    {
        "customer_type": "business",
        "company_name": "Beispiel Wohnbau GmbH",
        "street": "Industriestraße 40",
        "zip": "00303",
        "city": "Beispielhausen",
        "phone": "0000 300100",
        "email": "info@wohnbau.example.com",
        "note": "Bauträger, mehrere Reihenhäuser.",
    },
    {
        "customer_type": "business",
        "company_name": "Muster & Söhne Holzhandel KG",
        "street": "Hafenweg 7",
        "zip": "00101",
        "city": "Musterstadt",
        "phone": "0000 100200",
        "email": "kontakt@muster-soehne.example.org",
        "note": "Firmenname mit & (Sonderzeichen im Export).",
    },
    {
        "customer_type": "business",
        "company_name": "Gemeinde Fiktivingen (erfunden)",
        "street": "Rathausplatz 1",
        "zip": "00404",
        "city": "Fiktivingen",
        "phone": "0000 400100",
        "email": "bauamt@fiktivingen.example.net",
        "note": "Öffentlicher Auftraggeber: Spielplatz-Überdachung.",
    },
    {
        "customer_type": "business",
        "company_name": "Altbau Beispiel GbR",
        "street": "Lindenallee 9",
        "zip": "00505",
        "city": "Neu-Musterdorf",
        "phone": "0000 500100",
        "email": "altbau@example.com",
        "note": "Sanierung abgeschlossen, Kunde archiviert.",
        "archived": True,
    },
    {
        "customer_type": "business",
        "company_name": "=Formel Testbau GmbH (erfunden)",
        "street": "Prüfweg 0",
        "zip": "00606",
        "city": "Testhausen",
        "phone": "+0000 600100",
        "email": "pruefung@example.org",
        "note": 'Name beginnt mit "=" – zeigt den Schutz im CSV-Export.',
    },
]


class DemoRefused(RuntimeError):
    """Die Demo-Daten wurden nicht geladen, weil das Ziel ungeeignet ist."""


def load_demo_customers(session: Session) -> list[Customer]:
    """Legt alle Demo-Kunden an und gibt sie in der Reihenfolge von DEMO_CUSTOMERS zurück.

    Nur in eine Datenbank ohne Kunden – sonst DemoRefused. So landen Demo-Daten nie zwischen
    echten Kunden, und zweimal laden ergibt keine doppelten Einträge.
    """
    existing = session.exec(select(func.count()).select_from(Customer)).one()
    if existing:
        raise DemoRefused(
            f"Die Datenbank enthält schon {existing} Kunden. "
            "Demo-Daten nur in eine leere Datei laden."
        )
    created = []
    for entry in DEMO_CUSTOMERS:
        values = {key: value for key, value in entry.items() if key != "archived"}
        customer = service.create_customer(session, CustomerInput(**values))
        if entry.get("archived"):
            customer = service.archive_customer(session, customer.id)
        created.append(customer)
    return created


def demo_database_url(target: Path) -> str:
    """Prüft die Zieldatei und gibt ihre Datenbank-Adresse zurück. Die echte Datenbank: verboten."""
    path = target.resolve()
    if path == REAL_DATABASE.resolve():
        raise DemoRefused(
            f"{target} ist die echte Datenbank. Bitte eine eigene Datei wählen, z. B. data/demo.db."
        )
    if path.suffix != ".db":
        raise DemoRefused("Die Zieldatei muss auf .db enden (wird von Git ignoriert).")
    return f"sqlite:///{path.as_posix()}"


def main(argv: list[str] | None = None) -> int:
    """Befehl: uv run python -m timbertalk.features.customers.demo <datei.db>"""
    parser = argparse.ArgumentParser(description=f"Demo-Kunden der {DEMO_COMPANY} laden.")
    parser.add_argument("target", type=Path, help="Zieldatei, z. B. data/demo.db")
    args = parser.parse_args(argv)
    try:
        url = demo_database_url(args.target)
        args.target.parent.mkdir(parents=True, exist_ok=True)
        engine = make_engine(url)
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            customers = load_demo_customers(session)
            # Zählen, solange die Sitzung offen ist – danach sind die Objekte nicht mehr lesbar.
            total = len(customers)
            archived = sum(customer.archived for customer in customers)
        engine.dispose()
    except DemoRefused as error:
        print(f"Abgebrochen: {error}", file=sys.stderr)
        return 1
    print(f"{total} Demo-Kunden geladen ({archived} archiviert) in {args.target}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
