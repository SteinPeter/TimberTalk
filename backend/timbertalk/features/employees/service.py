# Die Logik des Features „Mitarbeitende“ (F14) als einfache Funktionen.
#
# Stundenkonto: Soll sind die vereinbarten Wochenstunden, gleich verteilt auf Montag bis Freitag.
# Feiertage (Bundesland des Betriebs, Feature holidays) und Abwesenheiten aus dem Kalender
# (Urlaub, krank, Berufsschule) zählen als erfüllt. Gerechnet wird vom 1. Januar (oder dem
# Eintritt) bis heute; gebucht minus Soll ergibt das Plus oder Minus.
#
# Urlaubskonto: Anspruch im Jahr plus Rest aus dem Vorjahr, minus genehmigter Urlaub aus dem
# Kalender, minus noch offene Anträge – alles in Arbeitstagen.
#
# Jede Funktion bekommt als ersten Parameter die Datenbank-Sitzung: session: Session.
# Fehler: ValueError – die Angabe passt nicht (422), LookupError – gibt es nicht (404).
# Daten anderer Features kommen nur über deren service.py: Personen (accounts), gebuchte Stunden
# (hours), Abwesenheiten und Urlaubsanträge (planning), Arbeitstage ohne Feiertage (holidays).

from datetime import date
from decimal import Decimal

from sqlmodel import Session

from timbertalk.features.accounts import service as accounts
from timbertalk.features.employees.models import (
    ContractIn,
    EmployeeContract,
    EmployeeSummary,
    HoursAccount,
    VacationAccount,
    VacationCarryover,
    VacationPreview,
)
from timbertalk.features.holidays import service as holidays
from timbertalk.features.hours import service as hours
from timbertalk.features.planning import service as planning

# Grenzen gegen Tippfehler (400 statt 40 Stunden).
MAX_WEEKLY_HOURS = Decimal("60")
MAX_VACATION_DAYS = 60
MAX_REQUEST_DAYS = 366  # wie im Kalender: ein Antrag umfasst höchstens ein Jahr


def _hours(minutes: int | Decimal) -> Decimal:
    return hours.to_hours(int(minutes))


def get_contract(session: Session, account_id: int) -> EmployeeContract:
    """Was mit der Person vereinbart ist – ohne Eintrag die Vorgaben."""
    accounts.get_account(session, account_id)  # LookupError, wenn es das Konto nicht gibt
    return session.get(EmployeeContract, account_id) or EmployeeContract(account_id=account_id)


def save_contract(session: Session, account_id: int, data: ContractIn) -> EmployeeSummary:
    """Speichert Wochenstunden, Urlaubsanspruch und Eintritt; gibt die Konten von heute zurück."""
    contract = get_contract(session, account_id)
    if not data.weekly_hours.is_finite() or not 0 <= data.weekly_hours <= MAX_WEEKLY_HOURS:
        raise ValueError("Die Wochenstunden müssen zwischen 0 und 60 liegen.")
    if not 0 <= data.vacation_days <= MAX_VACATION_DAYS:
        raise ValueError("Der Urlaubsanspruch muss zwischen 0 und 60 Tagen liegen.")
    contract.weekly_minutes = hours.to_minutes(data.weekly_hours)
    contract.vacation_days = data.vacation_days
    contract.start_date = data.start_date
    session.add(contract)
    session.commit()
    return summary(session, account_id, date.today().year)


def get_carryover(session: Session, account_id: int, year: int) -> int:
    stored = session.get(VacationCarryover, (account_id, year))
    return stored.days if stored else 0


def set_carryover(session: Session, account_id: int, year: int, days: int) -> EmployeeSummary:
    """Trägt den Resturlaub aus dem Vorjahr ein, der ins Jahr `year` übertragen wird."""
    accounts.get_account(session, account_id)
    if not 0 <= days <= MAX_VACATION_DAYS:
        raise ValueError("Der Resturlaub muss zwischen 0 und 60 Tagen liegen.")
    stored = session.get(VacationCarryover, (account_id, year)) or VacationCarryover(
        account_id=account_id, year=year
    )
    stored.days = days
    session.add(stored)
    session.commit()
    return summary(session, account_id, year)


def _hours_account(
    session: Session, contract: EmployeeContract, year: int, today: date
) -> HoursAccount:
    first = max(date(year, 1, 1), contract.start_date or date(year, 1, 1))
    until = min(today, date(year, 12, 31))
    if until < first:
        zero = Decimal("0.00")
        return HoursAccount(
            until=None,
            target_hours=zero,
            worked_hours=zero,
            balance_hours=zero,
            worked_month_hours=zero,
        )
    absent = planning.absence_days(session, contract.account_id, first, until)
    target_days = [day for day in holidays.workdays(session, first, until) if day not in absent]
    target = Decimal(len(target_days) * contract.weekly_minutes) / 5
    booked = hours.minutes_per_day(session, contract.account_id, first, until)
    worked = sum(booked.values())
    month = sum(
        m for day, m in booked.items() if (day.year, day.month) == (today.year, today.month)
    )
    return HoursAccount(
        until=until,
        target_hours=_hours(target),
        worked_hours=_hours(worked),
        balance_hours=_hours(worked) - _hours(target),
        worked_month_hours=_hours(month),
    )


def _vacation_account(
    session: Session, contract: EmployeeContract, year: int, today: date
) -> VacationAccount:
    first, last = date(year, 1, 1), date(year, 12, 31)
    year_workdays = set(holidays.workdays(session, first, last))
    absent = planning.absence_days(session, contract.account_id, first, last)
    vacation = [d for d, kind in absent.items() if kind == "vacation" and d in year_workdays]
    sick = [d for d, kind in absent.items() if kind == "sick" and d in year_workdays and d <= today]
    requested = 0
    for request in planning.list_requests(session, contract.account_id, may_approve=False):
        if request.status == "pending":
            days = holidays.workdays(
                session, max(request.start_date, first), min(request.end_date, last)
            )
            requested += len(days)
    taken = sum(1 for day in vacation if day <= today)
    carryover = get_carryover(session, contract.account_id, year)
    return VacationAccount(
        entitlement=contract.vacation_days,
        carryover=carryover,
        taken=taken,
        planned=len(vacation) - taken,
        requested=requested,
        remaining=contract.vacation_days + carryover - len(vacation) - requested,
        sick_days=len(sick),
    )


def summary(
    session: Session, account_id: int, year: int, today: date | None = None
) -> EmployeeSummary:
    """Stunden- und Urlaubskonto einer Person im Jahr `year` (today: zum Testen)."""
    today = today or date.today()
    contract = get_contract(session, account_id)
    account = accounts.get_account(session, account_id)
    return EmployeeSummary(
        account_id=account_id,
        display_name=account.display_name,
        year=year,
        weekly_hours=_hours(contract.weekly_minutes),
        vacation_days=contract.vacation_days,
        start_date=contract.start_date,
        holiday_region=holidays.current_state(session).name,
        hours=_hours_account(session, contract, year, today),
        vacation=_vacation_account(session, contract, year, today),
    )


def may_see_all(view_all: bool, manage: bool) -> bool:
    """Darf die Konten aller sehen? Mit „employees.view_all“ oder „employees.manage“ – pflegen
    schließt sehen ein, damit ein Häkchen bei „pflegen“ genügt."""
    return view_all or manage


def vacation_preview(
    session: Session, account_id: int, start: date, end: date, today: date | None = None
) -> VacationPreview:
    """Wie viele Arbeitstage ein Urlaub von start bis end kostet und was danach übrig bleibt.

    Gerechnet wie im Urlaubskonto: Montag bis Freitag ohne Feiertage. Tage im nächsten Jahr
    zählen dort und werden gesondert genannt.
    """
    if end < start:
        raise ValueError("Der letzte Urlaubstag liegt vor dem ersten.")
    if (end - start).days > MAX_REQUEST_DAYS:
        raise ValueError("Ein Antrag darf höchstens ein Jahr umfassen.")
    today = today or date.today()
    days = holidays.workdays(session, start, end)
    in_year = sum(1 for day in days if day.year == start.year)
    contract = get_contract(session, account_id)
    remaining = _vacation_account(session, contract, start.year, today).remaining
    return VacationPreview(
        year=start.year,
        workdays=len(days),
        other_year_days=len(days) - in_year,
        remaining_before=remaining,
        remaining_after=remaining - in_year,
    )


def visible_summary(
    session: Session,
    viewer_id: int,
    view_all: bool,
    manage: bool,
    account_id: int,
    year: int,
) -> EmployeeSummary:
    """Die Konten einer Person – fremde nur mit Recht (siehe may_see_all), sonst LookupError."""
    if account_id != viewer_id and not may_see_all(view_all, manage):
        raise LookupError(f"Das Konto {account_id} gibt es nicht.")
    return summary(session, account_id, year)


def overview(
    session: Session,
    year: int,
    view_all: bool,
    manage: bool,
    today: date | None = None,
) -> list[EmployeeSummary]:
    """Stunden- und Urlaubskonten aller aktiven Personen, nach Namen sortiert (Reiter „Personal“).

    Ohne Recht (siehe may_see_all): PermissionError. Admin-Konten fehlen schon in
    accounts.list_people() – auf dem Konto für die Technik arbeitet niemand.
    """
    if not may_see_all(view_all, manage):
        raise PermissionError("Dafür fehlt Ihnen das Recht, den Reiter „Personal“ zu sehen.")
    return [summary(session, person.id, year, today) for person in accounts.list_people(session)]
