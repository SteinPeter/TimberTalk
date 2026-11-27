# Tabelle des Features „Stunden buchen“ (F4) als SQLModel-Klasse, dazu Antwort- und
# Eingabeklassen. Der Tabellenname beginnt mit `hours_`.
#
# Gespeichert werden ganze Minuten (int): So gibt es keine Rundungsfehler, und 7,5 Stunden sind
# genau 450 Minuten. Nach außen (API) sind es Stunden als Decimal, z. B. „7.50“.

from datetime import date, datetime
from decimal import Decimal

from sqlmodel import Field, SQLModel


class HoursEntry(SQLModel, table=True):
    """Gebuchte Arbeitszeit einer Person an einem Tag, wahlweise auf ein Projekt."""

    __tablename__ = "hours_entry"

    id: int | None = Field(default=None, primary_key=True)
    account_id: int = Field(index=True)  # wer gearbeitet hat (Konto aus F10)
    work_date: date = Field(index=True)
    minutes: int  # Arbeitszeit in Minuten, ohne Pausen
    project_id: int | None = Field(default=None, index=True)  # Projektnummer (F3), freiwillig
    title: str = ""  # wofür, z. B. „Carport Berger“ – aus dem Kalender oder von Hand
    note: str = ""
    calendar_entry_id: int | None = None  # aus welchem Kalendertermin (F8) vorgeschlagen
    created_by: int | None = None  # wer gebucht hat (bei „für andere buchen“ nicht die Person)
    created_at: datetime


class HoursIn(SQLModel):
    """Eingabe: Stunden buchen. Ohne account_id für sich selbst."""

    work_date: date
    hours: Decimal  # z. B. „7.5“
    project_id: int | None = None
    title: str = ""
    note: str = ""
    calendar_entry_id: int | None = None
    account_id: int | None = None  # nur mit dem Recht „hours.manage“ für jemand anderen


class DayIn(SQLModel):
    """Eingabe: mehrere Vorschläge eines Tages auf einmal bestätigen."""

    items: list[HoursIn]


class HoursInfo(SQLModel):
    """Gebuchte Stunden für die Anzeige."""

    id: int
    account_id: int
    person: str
    work_date: date
    hours: Decimal
    project_id: int | None
    title: str
    note: str


class Suggestion(SQLModel):
    """Ein Vorschlag aus dem Kalender für einen Tag."""

    calendar_entry_id: int
    title: str
    project_id: int | None
    hours: Decimal  # Vorschlag: Arbeitszeit laut Kalender minus Pause, sonst 8
    time: str  # z. B. „07:00–16:00“ oder „ganzer Tag“
    booked: bool  # schon gebucht?
