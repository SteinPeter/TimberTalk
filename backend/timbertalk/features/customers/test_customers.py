# Tests für das Feature „Kunden“: service.py, api.py, den Demo-Datensatz (demo.py) und die
# S-11-Vorbereitung (tools.py).
# Fixtures aus backend/conftest.py: `session` für service.py, `client` für api.py.
# Jeder Test bekommt eine eigene, leere Datenbank. Alle Namen, Adressen, Telefonnummern und
# E-Mail-Adressen sind erfunden (E-Mail nur unter example.com/.org/.net).

import csv
import io
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlmodel import Session, SQLModel

from timbertalk.db import IN_MEMORY_URL, make_engine
from timbertalk.features.audit import service as audit
from timbertalk.features.customers import demo, service, tools
from timbertalk.features.customers.models import CustomerInput, CustomerUpdate
from timbertalk.main import FRONTEND_DIR

# --- Erfundene Testdaten --------------------------------------------------------------


def privat(**changes) -> CustomerInput:
    """Ein erfundener Privatkunde; einzelne Felder lassen sich überschreiben."""
    values = {
        "customer_type": "private",
        "first_name": "Erika",
        "last_name": "Mustermann",
        "street": "Musterweg 1",
        "zip": "12345",
        "city": "Musterstadt",
        "phone": "0000 111111",
        "email": "erika@example.com",
    }
    return CustomerInput(**(values | changes))


def firma(**changes) -> CustomerInput:
    """Eine erfundene Firma; einzelne Felder lassen sich überschreiben."""
    values = {
        "customer_type": "business",
        "company_name": "Beispiel Holzbau GmbH",
        "street": "Am Beispielhof 7",
        "zip": "54321",
        "city": "Beispielhausen",
        "phone": "0000 222222",
        "email": "info@example.com",
    }
    return CustomerInput(**(values | changes))


def names(customers) -> list[str]:
    return [customer.name for customer in customers]


# --- Anlegen und Prüfen ---------------------------------------------------------------


def test_privatkunde_anlegen(session: Session) -> None:
    customer = service.create_customer(session, privat())

    assert isinstance(customer.id, int)
    assert customer.name == "Erika Mustermann"
    assert customer.customer_type == "private"
    assert customer.archived is False
    assert service.get_customer(session, customer.id).city == "Musterstadt"


def test_firmenkunde_anlegen(session: Session) -> None:
    customer = service.create_customer(session, firma())

    assert customer.name == "Beispiel Holzbau GmbH"
    assert customer.customer_type == "business"


def test_privatkunde_ohne_nachname_wird_abgelehnt(session: Session) -> None:
    with pytest.raises(service.CustomerError) as error:
        service.create_customer(session, privat(last_name=""))
    assert error.value.code == "ungueltig"
    assert service.list_customers(session, include_archived=True) == []


def test_firma_ohne_firmenname_wird_abgelehnt(session: Session) -> None:
    with pytest.raises(service.CustomerError):
        service.create_customer(session, firma(company_name="   "))


def test_leerzeichen_werden_entfernt(session: Session) -> None:
    customer = service.create_customer(session, privat(first_name="  Erika ", city=" Musterstadt"))
    assert customer.name == "Erika Mustermann"
    assert customer.city == "Musterstadt"


def test_pruefen_speichert_nichts(session: Session) -> None:
    cleaned = service.check_customer_input(privat(last_name=" Mustermann "))
    assert cleaned.last_name == "Mustermann"
    assert service.list_customers(session, include_archived=True) == []


def test_unbekannte_kundenart_und_zu_langer_text_werden_abgelehnt() -> None:
    with pytest.raises(ValidationError):
        CustomerInput(customer_type="verein", last_name="Mustermann")
    with pytest.raises(ValidationError):
        CustomerInput(last_name="x" * 201)


# --- Lesen für andere Features (Erwartung von F3) -------------------------------------


def test_get_customer_liefert_id_und_name(session: Session) -> None:
    created = service.create_customer(session, firma())
    customer = service.get_customer(session, created.id)
    assert customer.id == created.id
    assert customer.name == "Beispiel Holzbau GmbH"


def test_get_customer_mit_unbekannter_nummer_liefert_none(session: Session) -> None:
    assert service.get_customer(session, 999) is None


def test_get_customer_liefert_auch_archivierte(session: Session) -> None:
    created = service.create_customer(session, privat())
    service.archive_customer(session, created.id)
    assert service.get_customer(session, created.id).archived is True


def test_list_customers_ohne_suche_alphabetisch(session: Session) -> None:
    service.create_customer(session, privat(first_name="Zora", last_name="Beispiel"))
    service.create_customer(session, firma())
    service.create_customer(session, privat(first_name="anna", last_name="Muster"))

    assert names(service.list_customers(session)) == [
        "anna Muster",
        "Beispiel Holzbau GmbH",
        "Zora Beispiel",
    ]


# --- Suchen ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query",
    ["Mustermann", "erika", "12345", "musterstadt", "0000 111111", "erika@example.com"],
)
def test_suche_findet_nach_name_plz_ort_telefon_und_email(session: Session, query: str) -> None:
    service.create_customer(session, privat())
    service.create_customer(session, firma())
    assert names(service.list_customers(session, query=query)) == ["Erika Mustermann"]


def test_suche_ohne_ruecksicht_auf_gross_und_kleinschreibung_bei_umlauten(
    session: Session,
) -> None:
    service.create_customer(session, privat(last_name="Müller", city="Übersee-Muster"))
    assert names(service.list_customers(session, query="MÜLLER")) == ["Erika Müller"]
    assert names(service.list_customers(session, query="übersee")) == ["Erika Müller"]


def test_suche_mit_mehreren_woertern(session: Session) -> None:
    service.create_customer(session, privat())
    service.create_customer(session, privat(first_name="Max", city="Beispielhausen"))
    result = service.list_customers(session, query="mustermann beispielhausen")
    assert names(result) == ["Max Mustermann"]


def test_prozentzeichen_ist_kein_platzhalter(session: Session) -> None:
    service.create_customer(session, privat())
    assert service.list_customers(session, query="%") == []
    assert service.list_customers(session, query="_") == []


def test_suche_ohne_treffer(session: Session) -> None:
    service.create_customer(session, privat())
    assert service.list_customers(session, query="Nirgendwo") == []


# --- Bearbeiten -----------------------------------------------------------------------


def test_kunde_bearbeiten(session: Session) -> None:
    created = service.create_customer(session, privat())
    before = created.updated_at

    changed = service.update_customer(
        session, created.id, CustomerUpdate(street="Neuer Weg 2", city="Beispielhausen")
    )

    assert changed.street == "Neuer Weg 2"
    assert changed.city == "Beispielhausen"
    assert changed.last_name == "Mustermann"  # nicht mitgeschickt, also unverändert
    assert changed.updated_at >= before
    assert names(service.list_customers(session, query="beispielhausen")) == ["Erika Mustermann"]


def test_namensaenderung_aendert_anzeigenamen(session: Session) -> None:
    created = service.create_customer(session, privat())
    changed = service.update_customer(session, created.id, CustomerUpdate(last_name="Beispiel"))
    assert changed.name == "Erika Beispiel"


def test_wechsel_zur_firma_ohne_firmenname_wird_abgelehnt(session: Session) -> None:
    created = service.create_customer(session, privat())
    with pytest.raises(service.CustomerError):
        service.update_customer(session, created.id, CustomerUpdate(customer_type="business"))
    session.expire_all()
    assert service.get_customer(session, created.id).customer_type == "private"


def test_pflichtfeld_leeren_wird_abgelehnt(session: Session) -> None:
    created = service.create_customer(session, privat())
    with pytest.raises(service.CustomerError):
        service.update_customer(session, created.id, CustomerUpdate(last_name=""))


def test_unbekannten_kunden_bearbeiten(session: Session) -> None:
    with pytest.raises(service.CustomerError) as error:
        service.update_customer(session, 999, CustomerUpdate(city="Musterstadt"))
    assert error.value.code == "nicht_gefunden"


# --- Archivieren und Wiederherstellen -------------------------------------------------


def test_archivierter_kunde_verschwindet_aus_der_liste(session: Session) -> None:
    created = service.create_customer(session, privat())
    service.create_customer(session, firma())

    archived = service.archive_customer(session, created.id)

    assert archived.archived is True
    assert archived.city == "Musterstadt"  # Daten bleiben erhalten
    assert names(service.list_customers(session)) == ["Beispiel Holzbau GmbH"]
    assert "Erika Mustermann" in names(service.list_customers(session, include_archived=True))


def test_kunde_wiederherstellen(session: Session) -> None:
    created = service.create_customer(session, privat())
    service.archive_customer(session, created.id)

    restored = service.restore_customer(session, created.id)

    assert restored.archived is False
    assert names(service.list_customers(session)) == ["Erika Mustermann"]


def test_unbekannten_kunden_archivieren(session: Session) -> None:
    with pytest.raises(service.CustomerError):
        service.archive_customer(session, 999)
    with pytest.raises(service.CustomerError):
        service.restore_customer(session, 999)


# --- Löschen (vorläufige Regel D3: nur archivierte) -----------------------------------


def test_aktiven_kunden_loeschen_wird_abgelehnt(session: Session) -> None:
    created = service.create_customer(session, privat())
    with pytest.raises(service.CustomerError) as error:
        service.delete_customer(session, created.id)
    assert error.value.code == "nicht_archiviert"
    assert service.get_customer(session, created.id) is not None


def test_archivierten_kunden_loeschen(session: Session) -> None:
    created = service.create_customer(session, privat())
    service.archive_customer(session, created.id)

    service.delete_customer(session, created.id)

    assert service.get_customer(session, created.id) is None


def test_unbekannten_kunden_loeschen(session: Session) -> None:
    with pytest.raises(service.CustomerError) as error:
        service.delete_customer(session, 999)
    assert error.value.code == "nicht_gefunden"


# --- Exportieren ----------------------------------------------------------------------


def read_csv(data: bytes) -> list[list[str]]:
    return list(csv.reader(io.StringIO(data.decode("utf-8-sig")), delimiter=";"))


def test_export_als_csv_fuer_excel(session: Session) -> None:
    service.create_customer(session, privat(last_name="Müller"))
    service.create_customer(session, firma())

    data = service.export_customers_csv(session)
    rows = read_csv(data)

    assert data.startswith(b"\xef\xbb\xbf")  # BOM: Excel erkennt UTF-8 und zeigt Umlaute
    assert rows[0][:3] == ["Kundennummer", "Art", "Name"]
    assert [row[2] for row in rows[1:]] == ["Beispiel Holzbau GmbH", "Erika Müller"]
    assert rows[1][1] == "Firma"
    assert rows[2][-1] == "nein"


def test_export_ohne_und_mit_archivierten(session: Session) -> None:
    created = service.create_customer(session, privat())
    service.archive_customer(session, created.id)

    assert len(read_csv(service.export_customers_csv(session))) == 1  # nur Überschrift
    rows = read_csv(service.export_customers_csv(session, include_archived=True))
    assert rows[1][-1] == "ja"


def test_export_entschaerft_formeln(session: Session) -> None:
    service.create_customer(session, firma(company_name="=1+1", phone="+00 000"))
    row = read_csv(service.export_customers_csv(session))[1]
    assert row[2] == "'=1+1"
    assert row[9] == "'+00 000"


def test_export_ohne_kunden(session: Session) -> None:
    rows = read_csv(service.export_customers_csv(session))
    assert rows == [list(service.EXPORT_COLUMNS.keys())]


# === Endpunkte (api.py) mit dem `client` aus conftest.py ===============================

PRIVAT_JSON = {
    "customer_type": "private",
    "first_name": "Erika",
    "last_name": "Mustermann",
    "street": "Musterweg 1",
    "zip": "12345",
    "city": "Musterstadt",
    "phone": "0000 111111",
    "email": "erika@example.com",
}
FIRMA_JSON = {
    "customer_type": "business",
    "company_name": "Beispiel Holzbau GmbH",
    "zip": "54321",
    "city": "Beispielhausen",
}


def anlegen(client: TestClient, data: dict) -> dict:
    response = client.post("/api/customers", json=data)
    assert response.status_code == 201, response.text
    return response.json()


def test_router_ist_ohne_eintrag_in_main_eingebunden(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/customers" in paths
    assert "/api/customers/{customer_id}" in paths
    assert "/api/customers/export.csv" in paths


def test_api_kunde_anlegen(client: TestClient) -> None:
    customer = anlegen(client, PRIVAT_JSON)

    assert isinstance(customer["id"], int)
    assert customer["name"] == "Erika Mustermann"
    assert customer["archived"] is False
    assert "search_text" not in customer  # interner Suchtext bleibt intern


def test_api_anlegen_ohne_pflichtfeld_gibt_422_mit_meldung(client: TestClient) -> None:
    response = client.post("/api/customers", json=PRIVAT_JSON | {"last_name": ""})
    assert response.status_code == 422
    assert "Nachname" in response.json()["detail"]  # deutsche Meldung als Text für api.js


def test_api_nur_mit_anmeldung(anonymous_client: TestClient) -> None:
    # main.py verlangt für jeden Router eine Anmeldung (F10) – auch für Export und Schreiben.
    assert anonymous_client.get("/api/customers").status_code == 401
    assert anonymous_client.get("/api/customers/export.csv").status_code == 401
    assert anonymous_client.post("/api/customers", json=PRIVAT_JSON).status_code == 401
    assert anonymous_client.delete("/api/customers/1").status_code == 401


def test_api_jede_aenderung_hat_einen_namen_fuers_protokoll() -> None:
    # CLAUDE.md (F11): Jeder ändernde Endpunkt bekommt summary="…".
    from timbertalk.features.customers.api import router

    for route in router.routes:
        if route.methods & {"POST", "PUT", "PATCH", "DELETE"}:
            assert route.summary, route.path


def test_api_aenderungen_stehen_im_protokoll(client: TestClient, session: Session) -> None:
    created = anlegen(client, PRIVAT_JSON)
    client.post(f"/api/customers/{created['id']}/archive")
    client.delete("/api/customers/999")  # abgelehnt (404) → kein Eintrag

    actions = [event.action for event in audit.list_events(session, area="Kunden")]
    assert actions == ["Kunde archivieren", "Kunde anlegen"]


def test_api_anlegen_mit_falscher_kundenart_gibt_422(client: TestClient) -> None:
    response = client.post("/api/customers", json=PRIVAT_JSON | {"customer_type": "verein"})
    assert response.status_code == 422


def test_api_liste_und_suche(client: TestClient) -> None:
    anlegen(client, PRIVAT_JSON)
    anlegen(client, FIRMA_JSON)

    alle = client.get("/api/customers").json()
    assert [c["name"] for c in alle] == ["Beispiel Holzbau GmbH", "Erika Mustermann"]

    treffer = client.get("/api/customers", params={"q": "musterstadt"}).json()
    assert [c["name"] for c in treffer] == ["Erika Mustermann"]


def test_api_kunde_anzeigen(client: TestClient) -> None:
    created = anlegen(client, FIRMA_JSON)
    response = client.get(f"/api/customers/{created['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Beispiel Holzbau GmbH"


def test_api_unbekannter_kunde_gibt_404(client: TestClient) -> None:
    response = client.get("/api/customers/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Kunde 999 gibt es nicht."
    assert client.patch("/api/customers/999", json={"city": "X"}).status_code == 404
    assert client.post("/api/customers/999/archive").status_code == 404
    assert client.post("/api/customers/999/restore").status_code == 404
    assert client.delete("/api/customers/999").status_code == 404


def test_api_kunde_bearbeiten(client: TestClient) -> None:
    created = anlegen(client, PRIVAT_JSON)

    response = client.patch(f"/api/customers/{created['id']}", json={"city": "Beispielhausen"})

    assert response.status_code == 200
    assert response.json()["city"] == "Beispielhausen"
    assert response.json()["last_name"] == "Mustermann"
    assert client.get(f"/api/customers/{created['id']}").json()["city"] == "Beispielhausen"


def test_api_bearbeiten_ohne_pflichtfeld_gibt_422(client: TestClient) -> None:
    created = anlegen(client, PRIVAT_JSON)
    response = client.patch(f"/api/customers/{created['id']}", json={"customer_type": "business"})
    assert response.status_code == 422
    assert client.get(f"/api/customers/{created['id']}").json()["customer_type"] == "private"


def test_api_archivieren_und_wiederherstellen(client: TestClient) -> None:
    created = anlegen(client, PRIVAT_JSON)

    archived = client.post(f"/api/customers/{created['id']}/archive")
    assert archived.status_code == 200
    assert archived.json()["archived"] is True
    assert client.get("/api/customers").json() == []
    assert len(client.get("/api/customers", params={"include_archived": True}).json()) == 1

    restored = client.post(f"/api/customers/{created['id']}/restore")
    assert restored.json()["archived"] is False
    assert len(client.get("/api/customers").json()) == 1


def test_api_loeschen_nur_archivierte(client: TestClient) -> None:
    created = anlegen(client, PRIVAT_JSON)
    url = f"/api/customers/{created['id']}"

    abgelehnt = client.delete(url)
    assert abgelehnt.status_code == 409
    assert "archiviert" in abgelehnt.json()["detail"]
    assert client.get(url).status_code == 200

    client.post(f"{url}/archive")
    assert client.delete(url).status_code == 204
    assert client.get(url).status_code == 404


def test_api_export_als_datei(client: TestClient) -> None:
    anlegen(client, PRIVAT_JSON | {"last_name": "Müller"})

    response = client.get("/api/customers/export.csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert 'filename="kunden.csv"' in response.headers["content-disposition"]
    rows = read_csv(response.content)
    assert rows[0][0] == "Kundennummer"
    assert rows[1][2] == "Erika Müller"


def test_api_export_mit_archivierten(client: TestClient) -> None:
    created = anlegen(client, PRIVAT_JSON)
    client.post(f"/api/customers/{created['id']}/archive")

    ohne = read_csv(client.get("/api/customers/export.csv").content)
    mit = read_csv(
        client.get("/api/customers/export.csv", params={"include_archived": True}).content
    )
    assert len(ohne) == 1
    assert len(mit) == 2


# === Demo-Datensatz (LD-09, demo.py) =================================================


def test_demo_daten_laden(session: Session) -> None:
    customers = demo.load_demo_customers(session)

    assert len(customers) == len(demo.DEMO_CUSTOMERS) == 10
    assert sum(c.customer_type == "private" for c in customers) == 5
    assert sum(c.customer_type == "business" for c in customers) == 5
    assert [c.name for c in customers if c.archived] == ["Paul Platzhalter", "Altbau Beispiel GbR"]
    assert len({c.city for c in customers}) >= 5


def test_demo_daten_sind_reproduzierbar(session: Session) -> None:
    first = [(c.id, c.name, c.archived) for c in demo.load_demo_customers(session)]

    other = make_engine(IN_MEMORY_URL)
    SQLModel.metadata.create_all(other)
    with Session(other) as second_session:
        second = [(c.id, c.name, c.archived) for c in demo.load_demo_customers(second_session)]
    other.dispose()

    assert first == second


def test_demo_daten_nur_in_leere_datenbank(session: Session) -> None:
    service.create_customer(session, privat())
    with pytest.raises(demo.DemoRefused):
        demo.load_demo_customers(session)
    assert len(service.list_customers(session, include_archived=True)) == 1


def test_demo_daten_sind_eindeutig_erfunden() -> None:
    for entry in demo.DEMO_CUSTOMERS:
        assert entry["zip"].startswith("00"), entry  # PLZ mit 00 gibt es nicht
        assert entry["phone"].lstrip("+").startswith("0000"), entry
        domain = entry["email"].rsplit("@", 1)[1]
        assert ".".join(domain.split(".")[-2:]) in ("example.com", "example.org", "example.net")
        assert "iban" not in {key.lower() for key in entry}


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("mustermann", ["Erika Mustermann", "Max Mustermann"]),
        ("ÜBERSEE", ["Jürgen Übermuster"]),
        ("özdemir", ["Ana-Lena Beispiel-Özdemir"]),
        ("00101", ["Erika Mustermann", "Max Mustermann", "Muster & Söhne Holzhandel KG"]),
        ("beispielhausen wohnbau", ["Beispiel Wohnbau GmbH"]),
        ("platzhalter", []),  # archiviert, ohne Schalter nicht sichtbar
    ],
)
def test_demo_suchfaelle(session: Session, query: str, expected: list[str]) -> None:
    demo.load_demo_customers(session)
    assert names(service.list_customers(session, query=query)) == expected


def test_demo_archivierte_mit_schalter_sichtbar(session: Session) -> None:
    demo.load_demo_customers(session)
    result = service.list_customers(session, query="platzhalter", include_archived=True)
    assert names(result) == ["Paul Platzhalter"]


def test_demo_nie_in_die_echte_datenbank() -> None:
    with pytest.raises(demo.DemoRefused):
        demo.demo_database_url(demo.REAL_DATABASE)
    with pytest.raises(demo.DemoRefused):
        demo.demo_database_url(Path("demo.txt"))


def test_demo_befehl_laedt_eine_eigene_datei(tmp_path: Path, capsys) -> None:
    target = tmp_path / "demo.db"

    assert demo.main([str(target)]) == 0
    assert "10 Demo-Kunden geladen (2 archiviert)" in capsys.readouterr().out
    assert target.exists()

    # Ein zweiter Lauf in dieselbe Datei bricht ab, statt Kunden doppelt anzulegen.
    assert demo.main([str(target)]) == 1
    assert "Abgebrochen" in capsys.readouterr().err


# === Export und Datenschutz (LN-05) ===================================================


def test_export_enthaelt_alle_vorgesehenen_felder(session: Session) -> None:
    service.create_customer(session, privat(note="Rückruf erbeten"))
    header, row = read_csv(service.export_customers_csv(session))

    assert header == list(service.EXPORT_COLUMNS)
    exported = dict(zip(header, row, strict=True))
    assert exported["Vorname"] == "Erika"
    assert exported["Nachname"] == "Mustermann"
    assert exported["Straße"] == "Musterweg 1"
    assert exported["PLZ"] == "12345"
    assert exported["Ort"] == "Musterstadt"
    assert exported["Telefon"] == "0000 111111"
    assert exported["E-Mail"] == "erika@example.com"
    assert exported["Notiz"] == "Rückruf erbeten"
    assert exported["Art"] == "Privat"
    assert exported["Archiviert"] == "nein"


def test_export_enthaelt_keine_internen_felder(session: Session) -> None:
    service.create_customer(session, privat())
    text = service.export_customers_csv(session).decode("utf-8-sig")
    assert "search_text" not in text
    assert "erika mustermann 12345" not in text  # Inhalt des internen Suchtexts


def test_export_sonderzeichen_bleiben_erhalten(session: Session) -> None:
    note = 'Preis 1.200 €; "Eilauftrag"\nzweite Zeile – Größe ½ ✓'
    service.create_customer(session, firma(company_name="Muster & Söhne; Holz KG", note=note))

    row = read_csv(service.export_customers_csv(session))[1]

    assert row[2] == "Muster & Söhne; Holz KG"  # Semikolon im Wert bricht die Spalten nicht
    assert row[11] == note  # Anführungszeichen, Zeilenumbruch, €, ½ unverändert


def test_export_ist_utf8_mit_bom(session: Session) -> None:
    service.create_customer(session, privat(last_name="Größe", city="Übersee"))
    data = service.export_customers_csv(session)

    assert data[:3] == b"\xef\xbb\xbf"
    assert data.count(b"\xef\xbb\xbf") == 1
    assert "Größe" in data[3:].decode("utf-8")  # ohne BOM ist es gültiges UTF-8
    assert b"\r\n" in data  # Zeilenende wie von Excel erwartet


@pytest.mark.parametrize("start", ["=", "+", "-", "@"])
def test_export_entschaerft_formeln_in_jedem_feld(session: Session, start: str) -> None:
    service.create_customer(
        session,
        privat(
            first_name=f"{start}A",
            last_name=f"{start}B",
            street=f"{start}SUM(1)",
            city=f"{start}C",
            note=f'{start}HYPERLINK("x")',
        ),
    )
    row = read_csv(service.export_customers_csv(session))[1]
    for value in row:
        assert not value.startswith(service._FORMULA_START), row


def test_export_formel_nach_leerzeichen_wird_auch_entschaerft(session: Session) -> None:
    service.create_customer(session, firma(company_name="  =1+1"))
    assert read_csv(service.export_customers_csv(session))[1][2] == "'=1+1"


def test_export_gleichheitszeichen_mitten_im_text_bleibt(session: Session) -> None:
    service.create_customer(session, firma(note="Maß a=b"))
    assert read_csv(service.export_customers_csv(session))[1][11] == "Maß a=b"


def test_geloeschter_kunde_ist_auch_im_export_weg(session: Session) -> None:
    created = service.create_customer(session, privat())
    service.archive_customer(session, created.id)
    service.delete_customer(session, created.id)

    rows = read_csv(service.export_customers_csv(session, include_archived=True))
    assert rows == [list(service.EXPORT_COLUMNS)]


def test_demo_export_mit_allen_kunden(session: Session) -> None:
    demo.load_demo_customers(session)
    rows = read_csv(service.export_customers_csv(session, include_archived=True))

    assert len(rows) == 11
    assert [rows[1][2], rows[1][9]] == ["'=Formel Testbau GmbH (erfunden)", "'+0000 600100"]
    assert sum(row[-1] == "ja" for row in rows[1:]) == 2


# === S-11-Vorbereitung (tools.py) =====================================================


def test_s11_felder_werden_uebersetzt() -> None:
    changes = tools.changes_from_s11({"strasse": "Neuer Weg 2", "plz": "00999", "ort": "X"})
    assert changes.model_dump(exclude_unset=True) == {
        "street": "Neuer Weg 2",
        "zip": "00999",
        "city": "X",
    }


@pytest.mark.parametrize(
    ("fields", "code"),
    [
        ({}, "ungueltig"),
        ({"farbe": "rot"}, "ungueltig"),
        ({"name": "Neu"}, "offen"),  # D9: Name über Werkzeug noch nicht festgelegt
    ],
)
def test_s11_felder_werden_geprueft(fields: dict, code: str) -> None:
    with pytest.raises(service.CustomerError) as error:
        tools.changes_from_s11(fields)
    assert error.value.code == code


def test_s11_zu_langer_wert_wird_abgewiesen() -> None:
    with pytest.raises(ValidationError):
        tools.changes_from_s11({"ort": "x" * 201})


def test_s11_kunde_suchen(session: Session) -> None:
    demo.load_demo_customers(session)
    assert names(tools.search_customers(session, "Mustermann")) == [
        "Erika Mustermann",
        "Max Mustermann",
    ]
    assert tools.search_customers(session, "Platzhalter") == []  # archiviert


def test_s11_kunde_aendern_vorschau_speichert_nichts(session: Session) -> None:
    created = service.create_customer(session, privat())

    preview = tools.preview_customer_change(session, created.id, {"ort": "Beispielhausen"})

    assert preview.city == "Beispielhausen"
    session.expire_all()
    assert service.get_customer(session, created.id).city == "Musterstadt"


def test_s11_kunde_aendern_vorschau_unbekannter_kunde(session: Session) -> None:
    with pytest.raises(service.CustomerError) as error:
        tools.preview_customer_change(session, 999, {"ort": "X"})
    assert error.value.code == "nicht_gefunden"


def test_s11_kunde_archivieren_vorschau_speichert_nichts(session: Session) -> None:
    created = service.create_customer(session, privat())

    preview = tools.preview_customer_archive(session, created.id)

    assert preview.id == created.id
    assert service.get_customer(session, created.id).archived is False
    with pytest.raises(service.CustomerError):
        tools.preview_customer_archive(session, 999)


def test_check_customer_update_speichert_nichts(session: Session) -> None:
    created = service.create_customer(session, privat())
    preview = service.check_customer_update(session, created.id, CustomerUpdate(city="Neu"))
    assert preview.city == "Neu"
    session.expire_all()
    assert service.get_customer(session, created.id).city == "Musterstadt"


# === Regeln für den Reiter (frontend/features/customers/customers.js) ===================
# Ohne Node.js im Projekt prüfen diese Tests den Quelltext des Reiters gegen CLAUDE.md und
# gegen die Regeln im Backend. Das Verhalten im Browser wird zusätzlich von Hand geprüft.

CUSTOMERS_JS = FRONTEND_DIR / "features" / "customers" / "customers.js"
SHARED_API_JS = FRONTEND_DIR / "shared" / "api.js"


def reiter_code() -> str:
    return CUSTOMERS_JS.read_text(encoding="utf-8")


def test_reiter_fragt_die_api_nur_ueber_shared_api_js() -> None:
    code = reiter_code()
    assert 'import { getJson, sendJson } from "../../shared/api.js";' in code
    assert "fetch(" not in code
    assert "XMLHttpRequest" not in code
    # Lesen: genau ein Aufruf (die Liste). Schreiben: genau einer, in sendChange().
    assert code.count("await getJson(") == 1
    assert code.count("await sendJson(") == 1
    send = code[code.index("async function sendChange(") :]
    assert "await sendJson(" in send[: send.index("\n}\n")]


def test_reiter_setzt_innerhtml_nur_mit_festem_text() -> None:
    code = reiter_code()
    templates = re.findall(r"innerHTML = `(.*?)`", code, re.S)
    assert len(templates) == code.count("innerHTML") == 1
    assert "${" not in templates[0]  # keine Daten im HTML, die kommen mit textContent


def test_schreiben_nur_an_wenn_shared_api_js_sendjson_hat() -> None:
    # Schreiben braucht sendJson(method, path, body) aus shared/api.js. Fehlt es, liefe ein
    # „Speichern“ ins Leere – dann muss WRITE_ENABLED aus sein.
    api = SHARED_API_JS.read_text(encoding="utf-8")
    hat_sendjson = re.search(r"export async function sendJson\(method, path, body\)", api)
    if not hat_sendjson:
        assert "const WRITE_ENABLED = false;" in reiter_code()


def test_reiter_prueft_antworten_bevor_er_erfolg_meldet() -> None:
    code = reiter_code()
    send = code[code.index("async function sendChange(") :]
    send = send[: send.index("\n}\n")]
    assert "if (!WRITE_ENABLED)" in send
    assert "confirmsChange(action" in send
    # Erfolgsmeldungen („gespeichert“, „archiviert“ …) stehen nur in Aufrufen nach sendChange().
    assert code.count("done(") == code.count("await sendChange(") + 1  # +1: Aufruf in openAction


def test_reiter_hoechstlaengen_wie_im_backend() -> None:
    fields = re.findall(r'\{ key: "(\w+)".*?max: (\d+)', reiter_code())
    assert {key for key, _ in fields} == set(CustomerInput.model_fields) - {"customer_type"}
    for key, maximum in fields:
        metadata = CustomerInput.model_fields[key].metadata
        limits = [m.max_length for m in metadata if getattr(m, "max_length", None) is not None]
        assert limits == [int(maximum)], key


def test_reiter_pflichtfelder_wie_im_backend() -> None:
    code = reiter_code()
    assert re.search(r'key: "company_name".*?required: \["business"\]', code)
    assert re.search(r'key: "last_name".*?required: \["private"\]', code)
    assert len(re.findall(r"required: \[", code)) == 2


def test_reiter_nutzt_noch_keine_eigenen_css_klassen() -> None:
    # Eigene Klassen customers-* kommen erst mit der Freigabe für style.css (Lösung A).
    code = reiter_code()
    assert 'class="customers-' not in code
    assert 'className = "customers-' not in code
