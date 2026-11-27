# Tabelle des Features „Feiertage“ (F15), dazu Antworten und Eingaben.
# Der Tabellenname beginnt mit `holidays_`.

from datetime import date

from sqlmodel import Field, SQLModel


class HolidaySetting(SQLModel, table=True):
    """Ein von Hand festgelegtes Bundesland. Fehlt die Zeile: aus der Firmenadresse."""

    __tablename__ = "holidays_setting"

    id: int = Field(default=1, primary_key=True)  # es gibt nur eine Zeile
    state: str  # Kürzel aus rules.STATES, z. B. „BB“


class StateInfo(SQLModel):
    """Nach welchem Bundesland die Feiertage gerechnet werden – und woher das kommt."""

    state: str | None  # Kürzel; None: unbekannt, dann nur die bundesweiten Feiertage
    name: str  # z. B. „Brandenburg“ oder „bundesweit“
    source: str  # „address“ (aus der Postleitzahl), „manual“ (festgelegt) oder „none“
    postcode: str | None  # die Postleitzahl aus der Firmenadresse, falls eine dasteht
    detected: str | None  # was die Postleitzahl ergibt – auch wenn von Hand anders festgelegt


class StateIn(SQLModel):
    """Eingabe: Bundesland festlegen (Kürzel) oder None für „aus der Firmenadresse“."""

    state: str | None


class Holiday(SQLModel):
    """Ein Feiertag für die Anzeige, z. B. im Kalender."""

    day: date
    name: str


class StateOption(SQLModel):
    """Ein Bundesland für die Auswahl in den Einstellungen."""

    state: str
    name: str
