# Tests für das Feature „Material, Fahrten und Preise“.
# Fixtures aus backend/conftest.py: `session` für service.py, `client` für api.py.
# Jeder Test bekommt eine eigene, leere Datenbank.

from collections.abc import Callable
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from timbertalk.features.materials import service, tools
from timbertalk.features.materials.models import CompanyIn

DAY = date(2026, 12, 3)


@pytest.fixture
def holz(session: Session):
    """Ein Material mit zwei Preisen: 450 Euro ab 2026-01-01 und 480 Euro ab 2026-12-01."""
    material = service.create_material(session, "Konstruktionsvollholz C24", "Bauholz", "m³")
    service.add_price(session, material.id, Decimal("450.00"), date(2026, 1, 1))
    service.add_price(session, material.id, Decimal("480.00"), date(2026, 12, 1))
    return material


def set_travel_rate(session: Session, rate: str = "0.50") -> None:
    service.save_company(session, CompanyIn(travel_rate_per_km=Decimal(rate)))


# --- Materialstamm und Preise ------------------------------------------------------


def test_preis_gilt_ab_seinem_datum(session: Session, holz) -> None:
    assert service.current_price(session, holz.id, date(2025, 12, 31)) is None
    assert service.current_price(session, holz.id, date(2026, 11, 30)).unit_price == Decimal(
        "450.00"
    )
    assert service.current_price(session, holz.id, date(2026, 12, 1)).unit_price == Decimal(
        "480.00"
    )


def test_preis_am_selben_tag_zweimal_wird_abgelehnt(session: Session, holz) -> None:
    with pytest.raises(ValueError, match="schon einen Preis"):
        service.add_price(session, holz.id, Decimal("1"), date(2026, 12, 1))


def test_preis_fuer_unbekanntes_material_wird_abgelehnt(session: Session) -> None:
    with pytest.raises(LookupError):
        service.add_price(session, 99, Decimal("1"), DAY)


def test_materialliste_nennt_den_preis_von_heute_und_filtert_die_kategorie(
    session: Session, holz
) -> None:
    service.create_material(session, "Holzschrauben 5x80", "Kleinteile", "Stk")
    alle = service.list_materials(session, on_date=DAY)
    assert [m.name for m in alle] == ["Holzschrauben 5x80", "Konstruktionsvollholz C24"]
    assert alle[0].preis is None  # noch kein Preis eingetragen

    bauholz = service.list_materials(session, "Bauholz", on_date=DAY)
    assert len(bauholz) == 1
    assert bauholz[0].preis == Decimal("480.00")
    assert bauholz[0].gueltig_ab == date(2026, 12, 1)
    assert bauholz[0].einheit == "m³"
    assert service.list_materials(session, "Gibt es nicht") == []


def test_suche_findet_ohne_gross_und_klein_und_hoechstens_zehn(session: Session) -> None:
    for number in range(12):
        service.create_material(session, f"Latte {number}", "Holz", "m")
    assert len(service.search_materials(session, "LATTE")) == 10
    assert service.search_materials(session, "holz")  # auch über die Kategorie
    with pytest.raises(ValueError):
        service.search_materials(session, "  ")


def test_material_braucht_name_und_einheit(session: Session) -> None:
    with pytest.raises(ValueError):
        service.create_material(session, " ", "", "m")
    with pytest.raises(ValueError):
        service.create_material(session, "Latte", "", "")


# --- Stammdaten der Abrechnung -----------------------------------------------------


def test_stammdaten_werden_gespeichert_und_wieder_gelesen(session: Session) -> None:
    assert service.get_company(session).company_name == ""  # noch nichts hinterlegt
    service.save_company(
        session,
        CompanyIn(
            company_name=" Zimmerei Berger ",
            address="Dorfstraße 1\n14467 Potsdam",
            logo="data:image/png;base64,AAAA",
            bank_name="Sparkasse",
            iban="de89 3704 0044 0532 0130 00",
            bic="cobadeffxxx",
            travel_rate_per_km=Decimal("0.55"),
            vat_rate=Decimal("19"),
        ),
    )
    company = service.get_company(session)
    assert company.company_name == "Zimmerei Berger"
    assert company.iban == "DE89370400440532013000"
    assert company.bic == "COBADEFFXXX"
    assert company.travel_rate_per_km == Decimal("0.55")
    assert company.logo == "data:image/png;base64,AAAA"


@pytest.mark.parametrize(
    "fields",
    [
        {"travel_rate_per_km": Decimal("-1")},
        {"vat_rate": Decimal("101")},
        {"logo": "kein-bild"},
        {"logo": "data:image/png;base64," + "A" * service.MAX_LOGO_LENGTH},
    ],
)
def test_ungueltige_stammdaten_werden_abgelehnt(session: Session, fields: dict) -> None:
    with pytest.raises(ValueError):
        service.save_company(session, CompanyIn(**fields))


def test_stundensatz_anlegen_aendern_und_loeschen(session: Session) -> None:
    geselle = service.save_hourly_rate(session, "Geselle", Decimal("55"))
    service.save_hourly_rate(session, "Meister", Decimal("70"))
    service.save_hourly_rate(session, "Geselle", Decimal("58.50"))  # gleicher Name: ändern
    rates = service.list_hourly_rates(session)
    assert [(r.name, r.rate) for r in rates] == [
        ("Geselle", Decimal("58.50")),
        ("Meister", Decimal("70")),
    ]
    service.delete_hourly_rate(session, geselle.id)
    assert [r.name for r in service.list_hourly_rates(session)] == ["Meister"]
    with pytest.raises(LookupError):
        service.delete_hourly_rate(session, geselle.id)


# --- Buchen und Kosten -------------------------------------------------------------


def test_material_buchen_haelt_den_preis_vom_buchungstag_fest(session: Session, holz) -> None:
    booking = service.book_material(session, 12, holz.id, Decimal("2.5"), date(2026, 11, 30))
    assert booking.unit_price == Decimal("450.00")  # der Preis vom 30.11., nicht der neuere
    service.add_price(session, holz.id, Decimal("999"), date(2027, 1, 1))
    costs = service.project_costs(session, 12)
    assert costs.material == Decimal("1125.00")


def test_material_ohne_preis_am_tag_wird_abgelehnt(session: Session, holz) -> None:
    with pytest.raises(ValueError, match="keinen Preis"):
        service.book_material(session, 12, holz.id, Decimal("1"), date(2025, 1, 1))


@pytest.mark.parametrize("quantity", ["0", "-1"])
def test_menge_muss_positiv_sein(session: Session, holz, quantity: str) -> None:
    with pytest.raises(ValueError, match="Menge"):
        service.book_material(session, 12, holz.id, Decimal(quantity), DAY)


HUGE_NUMBERS = ["Infinity", "-Infinity", "NaN", "1e1000", "1000000.01"]


@pytest.mark.parametrize("value", HUGE_NUMBERS)
def test_unendliche_und_riesige_zahlen_werden_ueberall_abgelehnt(
    session: Session, holz, value: str
) -> None:
    number = Decimal(value)
    with pytest.raises(ValueError, match="Zahl zwischen 0 und"):
        service.book_material(session, 12, holz.id, number, DAY)
    with pytest.raises(ValueError, match="Zahl zwischen 0 und"):
        service.add_price(session, holz.id, number, date(2027, 1, 1))
    with pytest.raises(ValueError, match="Zahl zwischen 0 und"):
        service.save_hourly_rate(session, "Geselle", number)
    with pytest.raises(ValueError):
        service.save_company(session, CompanyIn(travel_rate_per_km=number))
    with pytest.raises(ValueError):
        service.save_company(session, CompanyIn(vat_rate=number))
    set_travel_rate(session)
    with pytest.raises(ValueError, match="Zahl zwischen 0 und"):
        service.book_travel(session, 12, number, DAY)
    # Es wurde nichts gespeichert, die Kosten des Projekts lassen sich weiter berechnen.
    assert service.list_bookings(session, 12) == []
    assert service.project_costs(session, 12).total_net == Decimal("0")


def test_die_obergrenze_selbst_ist_erlaubt(session: Session) -> None:
    set_travel_rate(session)
    service.book_travel(session, 12, service.MAX_AMOUNT, DAY)
    assert service.project_costs(session, 12).travel == Decimal("500000.00")


def test_fahrt_braucht_den_satz_aus_den_stammdaten(session: Session) -> None:
    with pytest.raises(ValueError, match="Einstellungen"):
        service.book_travel(session, 12, Decimal("40"), DAY)


def test_fahrt_rechnet_km_mal_satz(session: Session) -> None:
    set_travel_rate(session, "0.55")
    booking = service.book_travel(session, 12, Decimal("40"), DAY)
    assert booking.unit == "km"
    assert service.project_costs(session, 12).travel == Decimal("22.00")


def test_geld_bleibt_decimal_und_summiert_ohne_rundungsfehler(session: Session) -> None:
    # Mit float wäre 0.1 + 0.2 nicht 0.3. Hier müssen die Summen auf den Cent stimmen.
    material = service.create_material(session, "Nägel", "Kleinteile", "Stk")
    service.add_price(session, material.id, Decimal("0.10"), date(2026, 1, 1))
    for _ in range(3):
        service.book_material(session, 1, material.id, Decimal("2"), DAY)
    costs = service.project_costs(session, 1)
    assert costs.material == Decimal("0.60")
    assert isinstance(costs.material, Decimal)


def test_kosten_zaehlen_je_projekt_und_nur_bestaetigtes(session: Session, holz) -> None:
    set_travel_rate(session)
    service.book_material(session, 12, holz.id, Decimal("2"), DAY)  # 960.00
    service.book_travel(session, 12, Decimal("40"), DAY)  # 20.00
    service.book_material(session, 13, holz.id, Decimal("1"), DAY)  # anderes Projekt
    service.book_travel_draft(session, 12, Decimal("100"), DAY)  # Entwurf: zählt noch nicht

    costs = service.project_costs(session, 12)
    assert (costs.material, costs.travel, costs.total_net) == (
        Decimal("960.00"),
        Decimal("20.00"),
        Decimal("980.00"),
    )
    assert service.project_costs(session, 99).total_net == Decimal("0.00")


def test_buchungsliste_zeigt_beschreibung_betrag_und_status(session: Session, holz) -> None:
    set_travel_rate(session)
    service.book_material(session, 12, holz.id, Decimal("2"), DAY)
    service.book_travel_draft(session, 12, Decimal("40"), DAY)
    liste = service.list_bookings(session, 12)
    assert [(b.description, b.amount, b.status) for b in liste] == [
        ("Konstruktionsvollholz C24", Decimal("960.00"), "confirmed"),
        ("Fahrt", Decimal("20.00"), "draft"),
    ]
    assert service.list_bookings(session, 99) == []


# --- Entwurf (S-05) ----------------------------------------------------------------


def test_material_als_entwurf_buchen_und_bestaetigen(session: Session, holz) -> None:
    positions = [
        {"material_id": holz.id, "menge": Decimal("2"), "einheit": "m³", "design_id": 7},
        {"material_id": holz.id, "menge": Decimal("1"), "einheit": "m³"},
    ]
    draft_id = service.book_material_draft(session, 12, positions, DAY)

    assert service.project_costs(session, 12).material == Decimal("0.00")  # noch Entwurf
    assert {b.status for b in service.list_bookings(session, 12)} == {"draft"}

    service.confirm_draft(session, draft_id)
    assert service.project_costs(session, 12).material == Decimal("1440.00")
    with pytest.raises(LookupError):
        service.confirm_draft(session, 99)


def test_entwuerfe_bekommen_fortlaufende_nummern(session: Session, holz) -> None:
    position = [{"material_id": holz.id, "menge": "1", "einheit": "m³"}]
    first = service.book_material_draft(session, 12, position, DAY)
    second = service.book_material_draft(session, 12, position, DAY)
    assert (first, second) == (1, 2)


def test_entwurf_bucht_alles_oder_nichts(session: Session, holz) -> None:
    positions = [
        {"material_id": holz.id, "menge": "1", "einheit": "m³"},
        {"material_id": 99, "menge": "1", "einheit": "m³"},  # gibt es nicht
    ]
    with pytest.raises(LookupError):
        service.book_material_draft(session, 12, positions, DAY)
    assert service.list_bookings(session, 12) == []


@pytest.mark.parametrize(
    "position",
    [
        {"menge": "1", "einheit": "m³"},  # ohne material_id
        {"material_id": 1, "menge": "viel", "einheit": "m³"},  # keine Zahl
        {"material_id": 1, "menge": "1", "einheit": "Stk"},  # falsche Einheit
    ],
)
def test_entwurf_mit_unpassender_position_wird_abgelehnt(
    session: Session, holz, position: dict
) -> None:
    with pytest.raises(ValueError):
        service.book_material_draft(session, 12, [position], DAY)
    assert service.list_bookings(session, 12) == []


def test_entwurf_ohne_positionen_wird_abgelehnt(session: Session) -> None:
    with pytest.raises(ValueError):
        service.book_material_draft(session, 12, [])


# --- Endpunkte ---------------------------------------------------------------------


def test_api_material_anlegen_preis_eintragen_und_listen(client: TestClient) -> None:
    created = client.post(
        "/api/materials/items", json={"name": "Brett", "category": "Bauholz", "unit": "m"}
    )
    assert created.status_code == 201
    material_id = created.json()["id"]

    price = client.post(
        f"/api/materials/items/{material_id}/prices",
        json={"unit_price": "12.50", "valid_from": "2026-01-01"},
    )
    assert price.status_code == 201

    items = client.get("/api/materials/items", params={"category": "Bauholz"}).json()
    assert items == [
        {
            "id": material_id,
            "name": "Brett",
            "kategorie": "Bauholz",
            "einheit": "m",
            "preis": "12.50",
            "gueltig_ab": "2026-01-01",
        }
    ]
    prices = client.get(f"/api/materials/items/{material_id}/prices").json()
    assert [p["unit_price"] for p in prices] == ["12.50"]


def test_api_fehler_kommen_mit_deutschem_text(client: TestClient) -> None:
    unbekannt = client.post(
        "/api/materials/items/99/prices", json={"unit_price": "1", "valid_from": "2026-01-01"}
    )
    assert unbekannt.status_code == 404
    assert "Material 99" in unbekannt.json()["detail"]

    leer = client.post("/api/materials/items", json={"name": " ", "unit": "m"})
    assert leer.status_code == 422
    assert "Name" in leer.json()["detail"]


def test_api_stammdaten_und_stundensaetze(client: TestClient) -> None:
    assert client.get("/api/materials/company").json()["company_name"] == ""
    saved = client.put(
        "/api/materials/company",
        json={"company_name": "Zimmerei Berger", "travel_rate_per_km": "0.55", "vat_rate": "19"},
    )
    assert saved.status_code == 200
    assert client.get("/api/materials/company").json()["travel_rate_per_km"] == "0.55"
    assert client.put("/api/materials/company", json={"vat_rate": "500"}).status_code == 422

    rate = client.put("/api/materials/hourly-rates", json={"name": "Geselle", "rate": "55"})
    assert rate.status_code == 200
    assert [r["name"] for r in client.get("/api/materials/hourly-rates").json()] == ["Geselle"]
    assert client.delete(f"/api/materials/hourly-rates/{rate.json()['id']}").status_code == 204
    assert client.get("/api/materials/hourly-rates").json() == []


def test_api_buchen_und_gesamtkosten(client: TestClient) -> None:
    material_id = client.post("/api/materials/items", json={"name": "Brett", "unit": "m"}).json()[
        "id"
    ]
    client.post(
        f"/api/materials/items/{material_id}/prices",
        json={"unit_price": "12.50", "valid_from": "2026-01-01"},
    )
    client.put("/api/materials/company", json={"travel_rate_per_km": "0.50"})

    material = client.post(
        "/api/materials/bookings/material",
        json={
            "project_id": 12,
            "material_id": material_id,
            "quantity": "4",
            "booking_date": "2026-12-03",
        },
    )
    travel = client.post(
        "/api/materials/bookings/travel",
        json={"project_id": 12, "km": "40", "booking_date": "2026-12-03"},
    )
    assert (material.status_code, travel.status_code) == (201, 201)

    liste = client.get("/api/materials/bookings", params={"project_id": 12}).json()
    assert [(b["description"], b["amount"]) for b in liste] == [
        ("Brett", "50.00"),
        ("Fahrt", "20.00"),
    ]
    assert client.get("/api/materials/projects/12/costs").json() == {
        "hours": "0.00",
        "material": "50.00",
        "travel": "20.00",
        "total_net": "70.00",
    }


@pytest.mark.parametrize("km", ["Infinity", "1e1000"])
def test_api_riesige_strecke_wird_abgelehnt_und_das_projekt_bleibt_benutzbar(
    client: TestClient, km: str
) -> None:
    client.put("/api/materials/company", json={"travel_rate_per_km": "0.50"})
    response = client.post(
        "/api/materials/bookings/travel",
        json={"project_id": 12, "km": km, "booking_date": "2026-12-03"},
    )
    assert response.status_code == 422
    assert client.get("/api/materials/bookings", params={"project_id": 12}).status_code == 200
    assert client.get("/api/materials/projects/12/costs").status_code == 200


def test_api_buchung_ohne_preis_wird_abgelehnt(client: TestClient) -> None:
    material_id = client.post("/api/materials/items", json={"name": "Brett", "unit": "m"}).json()[
        "id"
    ]
    response = client.post(
        "/api/materials/bookings/material",
        json={
            "project_id": 12,
            "material_id": material_id,
            "quantity": "1",
            "booking_date": "2026-12-03",
        },
    )
    assert response.status_code == 422
    assert "keinen Preis" in response.json()["detail"]


# --- Werkzeuge (S-09, S-14) --------------------------------------------------------


def seed_example_data(session: Session) -> None:
    """Die Daten, auf die sich die Beispiele der Werkzeuge beziehen."""
    material = service.create_material(session, "Konstruktionsvollholz C24", "Bauholz", "m³")
    service.add_price(session, material.id, Decimal("450.00"), date(2026, 1, 1))
    set_travel_rate(session, "0.50")
    service.book_material(session, 12, material.id, Decimal("2"), date(2026, 12, 1))  # 900.00
    service.book_travel(session, 12, Decimal("10"), date(2026, 12, 1))  # 5.00


def contains(expected, actual) -> bool:
    """Stimmt `actual` mit `expected` überein? Bei Dicts reicht es, wenn alle erwarteten Felder
    stimmen; bei Listen wird Element für Element verglichen."""
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(
            key in actual and contains(value, actual[key]) for key, value in expected.items()
        )
    if isinstance(expected, list):
        return (
            isinstance(actual, list)
            and len(actual) >= len(expected)
            and all(contains(e, a) for e, a in zip(expected, actual, strict=False))
        )
    return expected == actual


def test_die_vier_werkzeuge_aus_s14_sind_registriert() -> None:
    assert set(tools.TOOLS) == {
        "material_suchen",
        "material_buchen",
        "fahrt_buchen",
        "projekt_kosten",
    }


@pytest.mark.parametrize("name", sorted(tools.TOOLS))
def test_werkzeug_ist_nach_s09_beschrieben(name: str) -> None:
    tool = tools.TOOLS[name]
    assert tool.art in {tools.ART_LESEN, tools.ART_ENTWURF}
    assert tool.modul == "A"
    assert tool.beschreibung.endswith(".")
    assert tool.schema_ein["type"] == "object"
    assert set(tool.schema_ein["required"]) <= set(tool.schema_ein["properties"])
    assert tool.schema_aus["type"] == "object"
    assert set(tool.beispiel) == {"args", "ergebnis"}
    # Das Beispiel enthält alle Pflichtangaben des Schemas.
    assert set(tool.schema_ein["required"]) <= set(tool.beispiel["args"])


@pytest.mark.parametrize("name", sorted(tools.TOOLS))
def test_werkzeug_liefert_mit_seinem_beispiel_das_dokumentierte_ergebnis(
    session: Session, name: str
) -> None:
    seed_example_data(session)
    tool = tools.TOOLS[name]
    result = tools.call_tool(session, name, tool.beispiel["args"])
    assert contains(tool.beispiel["ergebnis"], result), result


def test_gebuchter_entwurf_aus_dem_werkzeug_zaehlt_erst_nach_der_bestaetigung(
    session: Session,
) -> None:
    seed_example_data(session)
    args = tools.TOOLS["fahrt_buchen"].beispiel["args"]
    result = tools.call_tool(session, "fahrt_buchen", args)
    before = tools.call_tool(session, "projekt_kosten", {"projekt_id": 12})
    service.confirm_draft(session, result["entwurf_id"])
    after = tools.call_tool(session, "projekt_kosten", {"projekt_id": 12})
    assert before["daten"]["fahrten"] == "5.00"
    assert after["daten"]["fahrten"] == "25.00"  # 5.00 + 40 km * 0.50


def test_werkzeug_fragt_nach_statt_zu_raten(session: Session) -> None:
    seed_example_data(session)
    fehlt = tools.call_tool(session, "fahrt_buchen", {"projekt_id": 12, "datum": "2026-12-03"})
    assert fehlt["status"] == "rueckfrage"
    assert fehlt["rueckfrage"]["feld"] == "km"

    unbekannt = tools.call_tool(
        session,
        "material_buchen",
        {
            "projekt_id": 12,
            "datum": "2026-12-03",
            "positionen": [{"material_id": 99, "menge": "1", "einheit": "m³"}],
        },
    )
    assert unbekannt["status"] == "rueckfrage"
    assert unbekannt["rueckfrage"]["optionen"][0]["name"] == "Konstruktionsvollholz C24"
    assert service.list_bookings(session, 12)[-1].status == "confirmed"  # nichts dazugebucht


def test_werkzeug_meldet_fehler_mit_code(session: Session) -> None:
    seed_example_data(session)
    assert tools.call_tool(session, "gibt_es_nicht", {})["fehler"]["code"] == "unbekannt"
    kein_datum = tools.call_tool(
        session, "fahrt_buchen", {"projekt_id": 12, "datum": "morgen", "km": "40"}
    )
    assert kein_datum["status"] == "fehler"
    assert kein_datum["fehler"]["code"] == "ungueltig"
    assert "JJJJ-MM-TT" in kein_datum["fehler"]["meldung"]


@pytest.mark.parametrize(
    ("name", "args"),
    [
        ("fahrt_buchen", {"projekt_id": 12, "datum": "2026-12-03", "km": "NaN"}),
        ("fahrt_buchen", {"projekt_id": 12, "datum": "2026-12-03", "km": "Infinity"}),
        ("fahrt_buchen", {"projekt_id": 12, "datum": "2026-12-03", "km": "1e1000"}),
        ("fahrt_buchen", {"projekt_id": "12", "datum": "2026-12-03", "km": "40"}),
        ("fahrt_buchen", {"projekt_id": 12, "datum": "2026-12-03", "km": "40", "notiz": "x"}),
        ("material_buchen", {"projekt_id": 12, "datum": "2026-12-03", "positionen": ["x"]}),
        ("projekt_kosten", {"projekt_id": "zwölf"}),
    ],
)
def test_werkzeug_antwortet_auf_falsche_eingaben_statt_abzustuerzen(
    session: Session, name: str, args: dict
) -> None:
    seed_example_data(session)
    result = tools.call_tool(session, name, args)
    assert result["status"] == "fehler", result
    assert result["fehler"]["code"] == "ungueltig"
    # Nichts Halbes ist liegen geblieben: Buchungsliste und Kosten funktionieren weiter.
    service.list_bookings(session, 12)
    assert tools.call_tool(session, "projekt_kosten", {"projekt_id": 12})["status"] == "ok"


def test_doppelter_werkzeugname_bricht_ab() -> None:
    with pytest.raises(RuntimeError, match="schon registriert"):
        tools.werkzeug(
            name="material_suchen",
            beschreibung="x.",
            art=tools.ART_LESEN,
            schema_ein={},
            schema_aus={},
            beispiel={},
        )(lambda session: None)


# --- Rechte (F10) ------------------------------------------------------------------


def _material_mit_preis(client: TestClient) -> int:
    material_id = client.post("/api/materials/items", json={"name": "Brett", "unit": "m"}).json()[
        "id"
    ]
    client.post(
        f"/api/materials/items/{material_id}/prices",
        json={"unit_price": "12.50", "valid_from": "2026-01-01"},
    )
    return material_id


def test_geselle_bucht_material_sieht_aber_keine_preise(
    client: TestClient, client_as: Callable[[str], TestClient]
) -> None:
    material_id = _material_mit_preis(client)
    geselle = client_as("journeyman")

    items = geselle.get("/api/materials/items").json()
    assert items[0]["name"] == "Brett"
    assert items[0]["preis"] is None

    gebucht = geselle.post(
        "/api/materials/bookings/material",
        json={
            "project_id": 12,
            "material_id": material_id,
            "quantity": "4",
            "booking_date": "2026-12-03",
        },
    )
    assert gebucht.status_code == 201
    assert gebucht.json()["unit_price"] is None
    assert gebucht.json()["amount"] is None

    liste = geselle.get("/api/materials/bookings", params={"project_id": 12}).json()
    assert [(b["description"], b["quantity"], b["amount"]) for b in liste] == [("Brett", "4", None)]
    # Der Chef sieht dieselbe Buchung mit Betrag.
    assert (
        client.get("/api/materials/bookings", params={"project_id": 12}).json()[0]["amount"]
        == "50.00"
    )


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/materials/projects/12/costs"),
        ("GET", "/api/materials/company"),
        ("GET", "/api/materials/hourly-rates"),
        ("GET", "/api/materials/items/1/prices"),
        ("POST", "/api/materials/items/1/prices"),
        ("PUT", "/api/materials/company"),
        ("POST", "/api/materials/items"),
    ],
)
def test_geselle_kommt_nicht_an_geld_und_stammdaten(
    client_as: Callable[[str], TestClient], method: str, path: str
) -> None:
    response = client_as("journeyman").request(method, path, json={})
    assert response.status_code == 403


def test_verwaltung_aendert_preise_meister_sieht_sie_nur(
    client: TestClient, client_as: Callable[[str], TestClient]
) -> None:
    material_id = _material_mit_preis(client)
    preis = {"unit_price": "13.00", "valid_from": "2026-02-01"}
    meister = client_as("master")
    verwaltung = client_as("office")

    assert meister.get("/api/materials/projects/12/costs").status_code == 200
    assert meister.post(f"/api/materials/items/{material_id}/prices", json=preis).status_code == 403
    assert (
        verwaltung.post(f"/api/materials/items/{material_id}/prices", json=preis).status_code == 201
    )
