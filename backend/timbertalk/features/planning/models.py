# Tabellen des Features „Planung: Kalender je Mitarbeiter“ (F8) als SQLModel-Klassen, dazu die
# Antwort- und Eingabeklassen der API. Alle Tabellennamen beginnen mit `planning_`.
#
# Ein Termin (Einsatz auf der Baustelle, Urlaub, Berufsschule …) läuft von einem Tag bis zu einem
# Tag, wahlweise mit Uhrzeit, und gehört einer oder mehreren Personen. Personen sind Konten aus
# F10 (accounts); hier steht nur ihre Nummer.

from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import Column, String
from sqlalchemy.types import TypeDecorator
from sqlmodel import Field, SQLModel


class DecimalText(TypeDecorator):
    """Speichert ein Decimal als Text und liest es als Decimal – SQLite kennt kein Decimal."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else str(Decimal(value))

    def process_result_value(self, value, dialect):
        return None if value is None else Decimal(value)


# Art eines Termins: Schlüssel im Code → Name auf dem Bildschirm. Abwesenheiten (Urlaub, krank,
# Schule) zählen bei der Prüfung auf Überschneidungen besonders.
KINDS: dict[str, str] = {
    "job": "Baustelle",
    "workshop": "Werkstatt",
    "appointment": "Termin",
    "vacation": "Urlaub",
    "sick": "Krank",
    "school": "Berufsschule",
}
ABSENCE_KINDS = {"vacation", "sick", "school"}

# Arten von Fahrzeugen und Maschinen, die man mit einplanen kann (Kran, Transporter …).
RESOURCE_CATEGORIES: dict[str, str] = {
    "vehicle": "Fahrzeug",
    "machine": "Maschine",
}

# --- Tabellen -------------------------------------------------------------------


class CalendarEntry(SQLModel, table=True):
    """Ein Termin im Kalender, vom ersten bis zum letzten Tag (beide eingeschlossen)."""

    __tablename__ = "planning_entry"

    id: int | None = Field(default=None, primary_key=True)
    title: str  # z. B. „Carport Berger, Potsdam“
    kind: str  # Schlüssel aus KINDS
    start_date: date = Field(index=True)
    end_date: date = Field(index=True)
    start_time: time | None = None  # ohne Uhrzeit: ganzer Tag
    end_time: time | None = None
    location: str = ""
    note: str = ""
    project_id: int | None = (
        None  # Projektnummer, freiwillig – damit die Stunden aufs Projekt gehen
    )
    created_by: int | None = None  # Nummer des Kontos, das den Termin eingetragen hat
    created_at: datetime


class CalendarAssignment(SQLModel, table=True):
    """Wer zu einem Termin eingeplant ist: eine Zeile je Person und Termin."""

    __tablename__ = "planning_assignment"

    entry_id: int = Field(foreign_key="planning_entry.id", primary_key=True)
    account_id: int = Field(primary_key=True, index=True)  # Konto aus F10


class Resource(SQLModel, table=True):
    """Ein Fahrzeug oder eine Maschine, die man wie eine Person einplanen kann."""

    __tablename__ = "planning_resource"

    id: int | None = Field(default=None, primary_key=True)
    name: str  # z. B. „Transporter B-TT 123“ oder „Autokran“
    category: str  # Schlüssel aus RESOURCE_CATEGORIES
    active: bool = True  # False: ausgemustert, erscheint nicht mehr auf der Plantafel
    # Nur bei Fahrzeugen: Euro netto je km für Fahrtbuchungen (F5). None: noch nicht eingetragen.
    rate_per_km: Decimal | None = Field(default=None, sa_column=Column(DecimalText, nullable=True))


class ResourceAssignment(SQLModel, table=True):
    """Welches Fahrzeug, welche Maschine zu einem Termin gebraucht wird."""

    __tablename__ = "planning_resource_assignment"

    entry_id: int = Field(foreign_key="planning_entry.id", primary_key=True)
    resource_id: int = Field(foreign_key="planning_resource.id", primary_key=True, index=True)


# Stand eines Urlaubsantrags: Schlüssel im Code → Name auf dem Bildschirm.
REQUEST_STATUS: dict[str, str] = {
    "pending": "Offen",
    "approved": "Genehmigt",
    "rejected": "Abgelehnt",
}


class AbsenceRequest(SQLModel, table=True):
    """Ein Urlaubsantrag. Genehmigt wird daraus ein Termin „Urlaub“ im Kalender."""

    __tablename__ = "planning_absence_request"

    id: int | None = Field(default=None, primary_key=True)
    account_id: int = Field(index=True)  # wer Urlaub möchte
    start_date: date
    end_date: date
    note: str = ""
    status: str = "pending"  # Schlüssel aus REQUEST_STATUS
    created_at: datetime
    decided_by: int | None = None
    decided_at: datetime | None = None
    decision_note: str = ""  # z. B. der Grund für eine Ablehnung
    entry_id: int | None = None  # der Termin im Kalender, sobald genehmigt


class IcalToken(SQLModel, table=True):
    """Der geheime Schlüssel für das Kalender-Abo einer Person. Gespeichert ist nur sein Hash."""

    __tablename__ = "planning_ical_token"

    account_id: int = Field(primary_key=True)
    token_hash: str = Field(unique=True, index=True)
    created_at: datetime


# --- Antworten und Eingaben (keine Tabellen) -------------------------------------


class ResourceInfo(SQLModel):
    """Ein Fahrzeug oder eine Maschine für die Anzeige."""

    id: int
    name: str
    category: str
    category_label: str
    active: bool
    rate_per_km: Decimal | None  # None: nicht eingetragen – oder man darf Preise nicht sehen


class RateIn(SQLModel):
    """Eingabe: Kilometersatz eines Fahrzeugs in Euro netto (leer = keiner)."""

    rate_per_km: Decimal | None


class ResourceIn(SQLModel):
    """Eingabe: ein neues oder geändertes Fahrzeug, eine Maschine."""

    name: str
    category: str = "vehicle"
    active: bool = True


class PersonRef(SQLModel):
    """Eine eingeplante Person mit Namen."""

    id: int
    display_name: str


class EntryInfo(SQLModel):
    """Ein Termin, wie die Oberfläche ihn zeigt – mit Namen der Personen."""

    id: int
    title: str
    kind: str
    kind_label: str
    start_date: date
    end_date: date
    start_time: time | None
    end_time: time | None
    location: str
    note: str
    project_id: int | None
    people: list[PersonRef]
    resources: list[PersonRef]  # Fahrzeuge und Maschinen: Nummer und Name


class SavedEntry(SQLModel):
    """Antwort nach dem Speichern: der Termin und Hinweise auf Überschneidungen."""

    entry: EntryInfo
    warnings: list[str]


class KindInfo(SQLModel):
    """Eine Art von Termin, für die Auswahl im Formular."""

    kind: str
    label: str
    absence: bool


class EntryIn(SQLModel):
    """Eingabe: ein neuer oder geänderter Termin."""

    title: str
    kind: str = "job"
    start_date: date
    end_date: date | None = None  # ohne: ein Tag
    start_time: time | None = None
    end_time: time | None = None
    location: str = ""
    note: str = ""
    project_id: int | None = None
    people: list[int] = []  # Nummern der Konten
    resources: list[int] = []  # Nummern der Fahrzeuge und Maschinen


# --- Urlaubsanträge und Kalender-Abo: Antworten und Eingaben -------------------------


class RequestInfo(SQLModel):
    """Ein Urlaubsantrag für die Anzeige – bei offenen Anträgen mit Hinweisen auf Termine."""

    id: int
    person: PersonRef
    start_date: date
    end_date: date
    days: int  # Kalendertage, Wochenenden eingeschlossen
    note: str
    status: str
    status_label: str
    decision_note: str
    conflicts: list[str]  # nur bei offenen Anträgen: was in der Zeit schon eingeplant ist


class RequestIn(SQLModel):
    """Eingabe: Urlaub von bis, mit Notiz."""

    start_date: date
    end_date: date
    note: str = ""


class DecisionIn(SQLModel):
    """Eingabe: Genehmigen oder Ablehnen, wahlweise mit Grund."""

    note: str = ""


class Decision(SQLModel):
    """Antwort nach dem Entscheiden: der Antrag und beim Genehmigen Hinweise aus dem Kalender."""

    request: RequestInfo
    warnings: list[str]


class IcalLink(SQLModel):
    """Antwort zum Kalender-Abo: ob es einen Link gibt, und direkt nach dem Erzeugen die Adresse."""

    active: bool
    path: str | None = None  # nur direkt nach dem Erzeugen, danach nie wieder
