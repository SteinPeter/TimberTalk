# Tabelle und Eingaben des Features „Kunden“ als SQLModel-Klassen.
# `Customer` ist die Tabelle. `CustomerInput` und `CustomerUpdate` sind keine Tabellen, sondern
# beschreiben, was beim Anlegen bzw. Ändern hereinkommen darf; pydantic prüft Art und Länge.
# Geldbeträge gibt es hier nicht. Bankdaten (z. B. IBAN) werden bewusst nicht gespeichert.

from datetime import UTC, datetime
from typing import Literal

from sqlmodel import Field, SQLModel

# Erlaubte Kundenarten: Privatkunde oder Firma.
CustomerType = Literal["private", "business"]

# Höchstlängen der Textfelder, damit niemand beliebig lange Texte speichert.
SHORT_TEXT = 200
LONG_TEXT = 2000


def now_utc() -> datetime:
    """Der aktuelle Zeitpunkt in UTC – für created_at und updated_at."""
    return datetime.now(UTC)


class Customer(SQLModel, table=True):
    """Ein Kunde. Die Nummer `id` ist eine ganze Zahl, die die Datenbank vergibt."""

    id: int | None = Field(default=None, primary_key=True)
    customer_type: str = "private"  # "private" oder "business"
    # Anzeigename, bildet der Service: Firmenname bzw. „Vorname Nachname“.
    name: str = Field(index=True)
    company_name: str = ""
    first_name: str = ""
    last_name: str = ""
    street: str = ""
    zip: str = ""
    city: str = ""
    phone: str = ""
    email: str = ""
    note: str = ""
    # Kleingeschriebener Suchtext aus Name, PLZ, Ort, Telefon und E-Mail (bildet der Service).
    search_text: str = ""
    archived: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class CustomerInput(SQLModel):
    """Die Angaben zu einem neuen Kunden. Pflicht prüft der Service je nach Kundenart."""

    customer_type: CustomerType = "private"
    company_name: str = Field(default="", max_length=SHORT_TEXT)
    first_name: str = Field(default="", max_length=SHORT_TEXT)
    last_name: str = Field(default="", max_length=SHORT_TEXT)
    street: str = Field(default="", max_length=SHORT_TEXT)
    zip: str = Field(default="", max_length=20)
    city: str = Field(default="", max_length=SHORT_TEXT)
    phone: str = Field(default="", max_length=50)
    email: str = Field(default="", max_length=SHORT_TEXT)
    note: str = Field(default="", max_length=LONG_TEXT)


class CustomerRead(SQLModel):
    """Ein Kunde, wie die API ihn zurückgibt – ohne den internen Suchtext."""

    id: int
    customer_type: str
    name: str
    company_name: str
    first_name: str
    last_name: str
    street: str
    zip: str
    city: str
    phone: str
    email: str
    note: str
    archived: bool
    created_at: datetime
    updated_at: datetime


class CustomerUpdate(SQLModel):
    """Änderungen an einem Kunden. Nur die Felder, die mitgeschickt werden, ändern sich."""

    customer_type: CustomerType | None = None
    company_name: str | None = Field(default=None, max_length=SHORT_TEXT)
    first_name: str | None = Field(default=None, max_length=SHORT_TEXT)
    last_name: str | None = Field(default=None, max_length=SHORT_TEXT)
    street: str | None = Field(default=None, max_length=SHORT_TEXT)
    zip: str | None = Field(default=None, max_length=20)
    city: str | None = Field(default=None, max_length=SHORT_TEXT)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=SHORT_TEXT)
    note: str | None = Field(default=None, max_length=LONG_TEXT)
