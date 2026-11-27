# Tabellen des Features „Mitarbeitende“ (F14) als SQLModel-Klassen, dazu Antworten und Eingaben.
# Die Tabellennamen beginnen mit `employees_`.
#
# Wie in F4 stehen Stunden als ganze Minuten (int) in der Datenbank, nach außen als Decimal.
# Urlaubstage sind ganze Tage (int).

from datetime import date
from decimal import Decimal

from sqlmodel import Field, SQLModel

DEFAULT_WEEKLY_MINUTES = 40 * 60  # 40 Stunden die Woche, Montag bis Freitag
DEFAULT_VACATION_DAYS = 30


class EmployeeContract(SQLModel, table=True):
    """Was mit einer Person vereinbart ist: Wochenstunden, Urlaubsanspruch, Eintritt.

    Fehlt die Zeile, gelten die Vorgaben oben (40 Stunden, 30 Tage, Eintritt unbekannt).
    """

    __tablename__ = "employees_contract"

    account_id: int = Field(primary_key=True)  # Konto aus F10
    weekly_minutes: int = DEFAULT_WEEKLY_MINUTES
    vacation_days: int = DEFAULT_VACATION_DAYS  # Urlaubstage im Jahr
    start_date: date | None = None  # Eintritt: davor zählen keine Soll-Stunden


class VacationCarryover(SQLModel, table=True):
    """Resturlaub aus dem Vorjahr, den der Chef für ein Jahr einträgt."""

    __tablename__ = "employees_carryover"

    account_id: int = Field(primary_key=True)
    year: int = Field(primary_key=True)  # das Jahr, in das der Urlaub übertragen wird
    days: int = 0


# --- Antworten und Eingaben (keine Tabellen) -------------------------------------


class ContractIn(SQLModel):
    """Eingabe: Wochenstunden, Urlaubstage im Jahr, Eintritt (freiwillig)."""

    weekly_hours: Decimal
    vacation_days: int
    start_date: date | None = None


class CarryoverIn(SQLModel):
    """Eingabe: Resturlaub aus dem Vorjahr in Tagen."""

    days: int


class HoursAccount(SQLModel):
    """Das Stundenkonto eines Jahres bis heute. Plus: mehr gearbeitet als vereinbart."""

    until: date | None  # gerechnet bis einschließlich; None: Jahr hat noch nicht begonnen
    target_hours: Decimal  # Soll bis heute (Urlaub, Krankheit, Schule zählen als erfüllt)
    worked_hours: Decimal  # gebucht bis heute
    balance_hours: Decimal  # gebucht minus Soll
    worked_month_hours: Decimal  # gebucht im laufenden Monat (im laufenden Jahr, sonst 0)


class VacationAccount(SQLModel):
    """Das Urlaubskonto eines Jahres in Arbeitstagen."""

    entitlement: int  # Anspruch im Jahr
    carryover: int  # Rest aus dem Vorjahr
    taken: int  # genehmigt und schon vorbei
    planned: int  # genehmigt, liegt noch vor uns
    requested: int  # beantragt, noch nicht entschieden
    remaining: int  # Anspruch + Rest Vorjahr − genehmigt − beantragt
    sick_days: int  # Krankheitstage bis heute


class VacationPreview(SQLModel):
    """Was ein Urlaubsantrag kosten würde – für die Live-Anzeige beim Beantragen."""

    year: int  # das Jahr des ersten Urlaubstags; dessen Urlaubskonto wird belastet
    workdays: int  # Arbeitstage im Zeitraum (Mo–Fr ohne Feiertage)
    other_year_days: int  # davon im Folgejahr – die zählen dort, nicht in `year`
    remaining_before: int  # übrig in `year` vor dem Antrag
    remaining_after: int  # übrig in `year`, wenn der Antrag genehmigt würde


class EmployeeSummary(SQLModel):
    """Stunden- und Urlaubskonto einer Person in einem Jahr, mit dem Vereinbarten."""

    account_id: int
    display_name: str
    year: int
    weekly_hours: Decimal
    vacation_days: int
    start_date: date | None
    holiday_region: str  # nach welchem Bundesland Feiertage zählen, z. B. „Brandenburg“
    hours: HoursAccount
    vacation: VacationAccount
