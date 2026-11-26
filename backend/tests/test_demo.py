# Tests für den Beispielbetrieb (timbertalk/demo.py): Er legt alles an, was man zum Ausprobieren
# braucht, und ein zweiter Aufruf ändert nichts.

from datetime import date, timedelta

import pytest
from sqlmodel import Session

from timbertalk import demo
from timbertalk.features.accounts import service as accounts
from timbertalk.features.hours import service as hours
from timbertalk.features.materials import service as materials
from timbertalk.features.planning import service as planning


@pytest.mark.parametrize(
    "today",
    [date(2026, 11, 26), date(2026, 11, 30), date(2027, 1, 1)],  # Do, Montag, Neujahr (Freitag)
    ids=["donnerstag", "montag", "neujahr"],
)
def test_beispielbetrieb_hat_alles_zum_ausprobieren(session: Session, today: date) -> None:
    assert demo.seed(session, today)

    roles = {a.role for a in accounts.list_accounts(session)}
    assert roles == {"admin", "owner", "master", "office", "journeyman", "apprentice"}
    assert materials.get_company(session).company_name.startswith("Zimmerei")
    assert len(materials.list_materials(session, on_date=today)) == len(demo.MATERIALS)
    assert all(m.preis is not None for m in materials.list_materials(session, on_date=today))
    assert len(materials.list_hourly_rates(session)) == len(demo.HOURLY_RATES)
    assert len(planning.vehicles_with_rate(session)) == 2

    monday = today - timedelta(days=today.weekday())
    chef = next(a for a in accounts.list_accounts(session) if a.role == "owner")
    week = planning.list_entries(session, monday, monday + timedelta(days=6), chef.id, True)
    assert len(week) >= 5
    pending = [r for r in planning.list_requests(session, chef.id, True) if r.status == "pending"]
    assert len(pending) == 1  # steht beim Chef auf dem Dashboard
    assert materials.project_costs(session, demo.CARPORT).total_net > 0
    booked = hours.list_hours(
        session, monday - timedelta(days=7), monday + timedelta(days=6), chef.id, True
    )
    assert booked

    # Demo-Modus an, automatisch als Chef.
    assert accounts.demo_settings(session).enabled
    assert accounts.demo_settings(session).account_id == chef.id


def test_zweiter_aufruf_aendert_nichts(session: Session) -> None:
    assert demo.seed(session, date(2026, 11, 26))
    count = len(accounts.list_accounts(session))
    assert not demo.seed(session, date(2026, 11, 26))
    assert len(accounts.list_accounts(session)) == count
    assert len(materials.list_materials(session)) == len(demo.MATERIALS)


def test_bestehende_datenbank_mit_admin_bekommt_den_beispielbetrieb_dazu(session: Session) -> None:
    accounts.ensure_initial_admin(session)  # wie eine schon benutzte Datenbank
    assert demo.seed(session, date(2026, 11, 26))
    admins = [a for a in accounts.list_accounts(session) if a.role == "admin"]
    assert len(admins) == 1  # der vorhandene Admin bleibt, kein zweiter
