# Tests für das Feature „Feiertage“ (F15): Ostern, Feiertage je Bundesland, Postleitzahl →
# Bundesland, Bundesland aus der Firmenadresse oder von Hand, Endpunkte.
# Fixtures aus backend/conftest.py: `session` für service.py, `client`/`client_as` für api.py.

from collections.abc import Callable
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from timbertalk.features.holidays import rules, service
from timbertalk.features.materials import service as materials
from timbertalk.features.materials.models import CompanyIn

# --- Regeln ---------------------------------------------------------------------------


def test_ostern() -> None:
    assert rules.easter_sunday(2025) == date(2025, 4, 20)
    assert rules.easter_sunday(2026) == date(2026, 4, 5)
    assert rules.easter_sunday(2027) == date(2027, 3, 28)


@pytest.mark.parametrize(
    ("state", "count", "special"),
    [
        (None, 9, None),  # bundesweit
        ("BB", 12, (date(2026, 5, 24), "Pfingstsonntag")),
        ("BY", 12, (date(2026, 6, 4), "Fronleichnam")),  # ohne Mariä Himmelfahrt (nur Gemeinden)
        ("BE", 10, (date(2026, 3, 8), "Internationaler Frauentag")),
        ("SN", 11, (date(2026, 11, 18), "Buß- und Bettag")),
        ("TH", 11, (date(2026, 9, 20), "Weltkindertag")),
        ("HH", 10, (date(2026, 10, 31), "Reformationstag")),
        ("SL", 12, (date(2026, 8, 15), "Mariä Himmelfahrt")),
    ],
)
def test_feiertage_je_bundesland(state: str | None, count: int, special: tuple | None) -> None:
    free = rules.holidays(2026, state)
    assert len(free) == count
    assert free[date(2026, 4, 3)] == "Karfreitag"
    if special:
        assert free[special[0]] == special[1]


def test_reformationstag_im_norden_erst_ab_2018() -> None:
    assert date(2017, 10, 31) not in rules.holidays(2017, "NI")
    assert date(2018, 10, 31) in rules.holidays(2018, "NI")


def test_arbeitstage_ohne_wochenende_und_feiertage() -> None:
    # Weihnachtswoche 2026: 25. und 26. sind Feiertage (Fr, Sa), der 24. ist Arbeitstag.
    assert rules.workdays(date(2026, 12, 21), date(2026, 12, 27), "BB") == [
        date(2026, 12, 21),
        date(2026, 12, 22),
        date(2026, 12, 23),
        date(2026, 12, 24),
    ]


@pytest.mark.parametrize(
    ("postcode", "state"),
    [
        ("14467", "BB"),  # Potsdam
        ("10115", "BE"),  # Berlin-Mitte
        ("14195", "BE"),  # Berlin-Dahlem
        ("80331", "BY"),  # München
        ("20095", "HH"),  # Hamburg
        ("21073", "HH"),  # Hamburg-Harburg
        ("28195", "HB"),  # Bremen
        ("27568", "HB"),  # Bremerhaven
        ("01067", "SN"),  # Dresden
        ("99084", "TH"),  # Erfurt
        ("39104", "ST"),  # Magdeburg
        ("19053", "MV"),  # Schwerin
        ("24103", "SH"),  # Kiel
        ("30159", "NI"),  # Hannover
        ("50667", "NW"),  # Köln
        ("60311", "HE"),  # Frankfurt am Main
        ("55116", "RP"),  # Mainz
        ("66111", "SL"),  # Saarbrücken
        ("70173", "BW"),  # Stuttgart
        ("63739", "BY"),  # Aschaffenburg
        ("89231", "BY"),  # Neu-Ulm
    ],
)
def test_postleitzahl_ergibt_bundesland(postcode: str, state: str) -> None:
    assert rules.state_for_postcode(postcode) == state


def test_postleitzahl_aus_der_adresse() -> None:
    assert rules.postcode_in("Am Sägewerk 12\n14467 Potsdam") == "14467"
    assert rules.postcode_in("D-80331 München, Tel. 089 123456") == "80331"
    assert rules.postcode_in("Hauptstraße 1, Potsdam") is None


# --- Bundesland des Betriebs ------------------------------------------------------------


def test_bundesland_aus_firmenadresse_oder_von_hand(session: Session) -> None:
    assert service.current_state(session).source == "none"
    assert len(service.holidays_between(session, date(2026, 1, 1), date(2026, 12, 31))) == 9

    materials.save_company(session, CompanyIn(address="Marienplatz 1\n80331 München"))
    info = service.current_state(session)
    assert (info.state, info.name, info.source, info.postcode) == (
        "BY",
        "Bayern",
        "address",
        "80331",
    )
    names = [h.name for h in service.holidays_between(session, date(2026, 6, 1), date(2026, 6, 30))]
    assert names == ["Fronleichnam"]

    # Von Hand festgelegt gilt vor der Adresse; None stellt wieder auf „aus der Adresse“.
    assert service.set_state(session, "BB").source == "manual"
    assert service.current_state(session).detected == "BY"
    assert service.set_state(session, None).state == "BY"
    with pytest.raises(ValueError, match="gibt es nicht"):
        service.set_state(session, "XX")


def test_arbeitstage_folgen_dem_bundesland(session: Session) -> None:
    # Fronleichnam (4.6.2026) ist in Bayern frei, in Brandenburg nicht.
    week = (date(2026, 6, 1), date(2026, 6, 5))
    materials.save_company(session, CompanyIn(address="80331 München"))
    assert len(service.workdays(session, *week)) == 4
    materials.save_company(session, CompanyIn(address="14467 Potsdam"))
    assert len(service.workdays(session, *week)) == 5


def test_api_lesen_alle_festlegen_nur_mit_recht(
    client: TestClient, client_as: Callable[[str], TestClient]
) -> None:
    geselle = client_as("journeyman")
    week = geselle.get("/api/holidays?start=2026-12-21&end=2026-12-27")
    assert [h["name"] for h in week.json()] == ["1. Weihnachtstag", "2. Weihnachtstag"]
    assert len(geselle.get("/api/holidays/states").json()) == 16
    assert geselle.put("/api/holidays/state", json={"state": "BY"}).status_code == 403
    assert client.put("/api/holidays/state", json={"state": "BY"}).json()["name"] == "Bayern"
    assert client.get("/api/holidays?start=2026-01-01&end=2029-01-01").status_code == 422
