# Die Logik des Features „Feiertage“ (F15) als einfache Funktionen.
#
# Das Bundesland kommt aus der Postleitzahl in der Firmenadresse (Feature materials, F5); ist es
# unter Einstellungen → Feiertage von Hand festgelegt, gilt das. Ohne beides gelten nur die
# bundesweiten Feiertage. Andere Features fragen hier nach Feiertagen und Arbeitstagen.
#
# Jede Funktion bekommt als ersten Parameter die Datenbank-Sitzung: session: Session.
# Fehler: ValueError – die Angabe passt nicht (422).

from datetime import date

from sqlmodel import Session

from timbertalk.features.holidays import rules
from timbertalk.features.holidays.models import Holiday, HolidaySetting, StateInfo, StateOption
from timbertalk.features.materials import service as materials

NATIONWIDE = "bundesweit"


def current_state(session: Session) -> StateInfo:
    """Nach welchem Bundesland gerechnet wird, und woher das kommt."""
    postcode = rules.postcode_in(materials.get_company(session).address)
    detected = rules.state_for_postcode(postcode) if postcode else None
    manual = session.get(HolidaySetting, 1)
    if manual is not None:
        state, source = manual.state, "manual"
    elif detected is not None:
        state, source = detected, "address"
    else:
        state, source = None, "none"
    return StateInfo(
        state=state,
        name=rules.STATES.get(state, NATIONWIDE),
        source=source,
        postcode=postcode,
        detected=detected,
    )


def set_state(session: Session, state: str | None) -> StateInfo:
    """Legt das Bundesland fest. None: wieder aus der Postleitzahl der Firmenadresse."""
    manual = session.get(HolidaySetting, 1)
    if state is None:
        if manual is not None:
            session.delete(manual)
            session.commit()
        return current_state(session)
    if state not in rules.STATES:
        raise ValueError(f"Das Bundesland „{state}“ gibt es nicht.")
    manual = manual or HolidaySetting(state=state)
    manual.state = state
    session.add(manual)
    session.commit()
    return current_state(session)


def list_states() -> list[StateOption]:
    """Alle Bundesländer für die Auswahl, alphabetisch."""
    return [StateOption(state=code, name=name) for code, name in rules.STATES.items()]


def holidays_between(session: Session, start: date, end: date) -> list[Holiday]:
    """Die Feiertage von start bis end im Bundesland des Betriebs, nach Datum."""
    if end < start:
        raise ValueError("Das Ende des Zeitraums liegt vor dem Anfang.")
    if end.year - start.year > 1:
        raise ValueError("Bitte höchstens zwei Kalenderjahre auf einmal abfragen.")
    state = current_state(session).state
    found = []
    for year in range(start.year, end.year + 1):
        for day, name in rules.holidays(year, state).items():
            if start <= day <= end:
                found.append(Holiday(day=day, name=name))
    return sorted(found, key=lambda holiday: holiday.day)


def workdays(session: Session, start: date, end: date) -> list[date]:
    """Arbeitstage von start bis end: Montag bis Freitag ohne Feiertage des Betriebs."""
    return rules.workdays(start, end, current_state(session).state)
