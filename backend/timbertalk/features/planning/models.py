# Tabellen des Features „Planung: Kalender je Mitarbeiter“ (F8) als SQLModel-Klassen, dazu die
# Antwort- und Eingabeklassen der API. Alle Tabellennamen beginnen mit `planning_`.
#
# Ein Termin (Einsatz auf der Baustelle, Urlaub, Berufsschule …) läuft von einem Tag bis zu einem
# Tag, wahlweise mit Uhrzeit, und gehört einer oder mehreren Personen. Personen sind Konten aus
# F10 (accounts); hier steht nur ihre Nummer.

from datetime import date, datetime, time

from sqlmodel import Field, SQLModel

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
    created_by: int | None = None  # Nummer des Kontos, das den Termin eingetragen hat
    created_at: datetime


class CalendarAssignment(SQLModel, table=True):
    """Wer zu einem Termin eingeplant ist: eine Zeile je Person und Termin."""

    __tablename__ = "planning_assignment"

    entry_id: int = Field(foreign_key="planning_entry.id", primary_key=True)
    account_id: int = Field(primary_key=True, index=True)  # Konto aus F10


# --- Antworten und Eingaben (keine Tabellen) -------------------------------------


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
    people: list[PersonRef]


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
    people: list[int]  # Nummern der Konten
