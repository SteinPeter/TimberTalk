# Tests für das Feature „Projekte“ (F3): Service, Endpunkte, Schnittstelle S-03 und
# KI-Werkzeuge (S-09 / S-12). Fixtures `session` und `client` kommen aus backend/conftest.py;
# jeder Test bekommt eine eigene, leere Datenbank.

from datetime import date
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from timbertalk.features.customers import service as customers_service
from timbertalk.features.projects import service, tools
from timbertalk.features.projects.models import PROJECT_STATUSES

# --- Beispieldaten für S-09 / S-12 ----------------------------------------------


def seed_example_data(session: Session) -> None:
    """Legt den Beispielstand an, auf dem alle Werkzeug-Beispiele aus `tools.TOOLS` laufen."""
    service.create_project(
        session,
        customer_id=4,
        customer_name="Berger",
        name="Carport",
        baustelle="Potsdam",
        status="geplant",
        start_date=date(2026, 12, 1),
        duration_days=4,
    )


def _install_fake_customers(
    monkeypatch: pytest.MonkeyPatch,
    customers: dict[int, str],
) -> None:
    """Spielt ein fertiges Feature F2 (`customers/service.py`) für Tests der Kopplung nach."""

    def fake_get_customer(_session: Session, customer_id: int):
        name = customers.get(customer_id)
        return SimpleNamespace(id=customer_id, name=name) if name is not None else None

    def fake_list_customers(_session: Session):
        return [SimpleNamespace(id=cid, name=name) for cid, name in customers.items()]

    monkeypatch.setattr(customers_service, "get_customer", fake_get_customer, raising=False)
    monkeypatch.setattr(customers_service, "list_customers", fake_list_customers, raising=False)


# --- Service: Projekte anlegen, suchen, ändern, Status, archivieren -------------


def test_projekt_anlegen_und_enddatum_berechnen(session: Session) -> None:
    created = service.create_project(
        session,
        customer_id=4,
        customer_name="Holzbau Berger",
        name="Carport",
        baustelle="Potsdam",
        status="geplant",
        start_date=date(2026, 12, 1),
        duration_days=4,
        notes="Zufahrt über Gartenstraße",
    )

    assert created.id == 1
    assert created.customer_id == 4
    assert created.customer_name == "Holzbau Berger"
    assert created.name == "Carport"
    assert created.baustelle == "Potsdam"
    assert created.status == "geplant"
    assert created.start_date == date(2026, 12, 1)
    assert created.duration_days == 4
    assert created.end_date == date(2026, 12, 4)
    assert created.notes == "Zufahrt über Gartenstraße"
    assert created.archived is False


def test_projekt_ohne_kunde_wird_abgelehnt(session: Session) -> None:
    with pytest.raises(ValueError, match="Kunde"):
        service.create_project(session, customer_id=None, name="Dachstuhl")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="Kunde"):
        service.create_project(session, customer_id=0, name="Dachstuhl")
    with pytest.raises(ValueError, match="Kunde"):
        service.create_project(session, customer_id=-2, name="Dachstuhl")


def test_projekt_prueft_eingaben_zu_name_status_und_zeitraum(session: Session) -> None:
    with pytest.raises(ValueError, match="Projektname"):
        service.create_project(session, customer_id=1, name="   ")
    with pytest.raises(ValueError, match="Status"):
        service.create_project(session, customer_id=1, name="Carport", status="unbekannt")
    with pytest.raises(ValueError, match="Enddatum"):
        service.create_project(
            session,
            customer_id=1,
            name="Carport",
            start_date=date(2026, 12, 10),
            end_date=date(2026, 12, 5),
        )
    with pytest.raises(ValueError, match="Dauer"):
        service.create_project(session, customer_id=1, name="Carport", duration_days=0)


def test_alle_fuenf_status_setzbar_und_schreibweise_in_arbeit(session: Session) -> None:
    project = service.create_project(session, customer_id=2, name="Dachausbau")
    for status in PROJECT_STATUSES:
        updated = service.set_project_status(session, project.id, status)
        assert updated.status == status

    normalized = service.set_project_status(session, project.id, "in Arbeit")
    assert normalized.status == "in_arbeit"


def test_projekt_suchen_aendern_und_archivieren(session: Session) -> None:
    p1 = service.create_project(
        session,
        customer_id=4,
        customer_name="Berger",
        name="Carport",
        baustelle="Potsdam",
        status="geplant",
    )
    p2 = service.create_project(
        session,
        customer_id=7,
        customer_name="Müller",
        name="Gaube",
        baustelle="Werder",
        status="in_arbeit",
    )

    # Suche über mehrere Wörter aus Kundenname und Projektname
    hits = service.list_projects(session, text="Berger Carport")
    assert [p.id for p in hits] == [p1.id]

    # Filtern nach Status und Kunde
    assert [p.id for p in service.list_projects(session, status="in_arbeit")] == [p2.id]
    assert [p.id for p in service.list_projects(session, customer_id=4)] == [p1.id]

    # Ändern
    edited = service.update_project(
        session,
        p1.id,
        {"baustelle": "Werder (Havel)", "notes": "Holz bestellt"},
    )
    assert edited.baustelle == "Werder (Havel)"
    assert edited.notes == "Holz bestellt"

    # Archivieren: verschwindet aus der normalen Liste, bleibt aber mit Filter sichtbar
    archived = service.archive_project(session, p1.id)
    assert archived.archived is True
    assert [p.id for p in service.list_projects(session)] == [p2.id]
    assert {p.id for p in service.list_projects(session, include_archived=True)} == {p1.id, p2.id}

    # Wiederherstellen
    restored = service.archive_project(session, p1.id, archived=False)
    assert restored.archived is False
    assert {p.id for p in service.list_projects(session)} == {p1.id, p2.id}


# --- Schnittstelle S-03 & Kopplung an F2 (Kunden) -------------------------------


def test_s03_get_project_und_get_customer_ohne_f2(session: Session) -> None:
    seed_example_data(session)

    project = service.get_project(session, 1)
    assert project is not None
    assert project.id == 1
    assert project.name == "Carport"
    assert project.customer_id == 4
    assert project.baustelle == "Potsdam"
    assert project.status == "geplant"
    assert service.get_project(session, 999) is None
    assert service.get_project(session, 0) is None

    customer = service.get_customer(session, 4)
    assert customer is not None
    assert customer.id == 4
    assert customer.name == "Berger"
    assert service.get_customer(session, 999) is None


def test_s03_und_kundenpruefung_mit_f2_service(
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_customers(monkeypatch, {4: "Familie Berger", 9: "Zimmerei Schulz"})

    assert service.get_customer(session, 4) == service.CustomerInfo(id=4, name="Familie Berger")
    assert service.get_customer(session, 999) is None

    # Unbekannter Kunde wird beim Anlegen abgelehnt
    with pytest.raises(LookupError, match="Kunde 999"):
        service.create_project(session, customer_id=999, name="Terrasse")

    # Bekannter Kunde bekommt automatisch seinen Namen aus F2
    created = service.create_project(session, customer_id=4, name="Terrasse", baustelle="Berlin")
    assert created.customer_name == "Familie Berger"

    # Kunden-Projekt-Liste zeigt alle F2-Kunden samt ihrer Projekte
    grouped = service.list_customer_projects(session)
    by_id = {entry.customer.id: entry for entry in grouped}
    assert set(by_id) == {4, 9}
    assert [p.id for p in by_id[4].projects] == [created.id]
    assert by_id[9].projects == []
    assert [p.id for p in service.list_projects_for_customer(session, 4)] == [created.id]


# --- Endpunkte (/api/projects) --------------------------------------------------


def test_api_projekt_lebenszyklus(client: TestClient) -> None:
    # Ohne Kunde abgelehnt (422)
    missing_customer = client.post("/api/projects", json={"name": "Carport"})
    assert missing_customer.status_code == 422

    # Anlegen
    created_resp = client.post(
        "/api/projects",
        json={
            "customer_id": 4,
            "customer_name": "Berger",
            "name": "Carport",
            "baustelle": "Potsdam",
            "status": "angefragt",
            "start_date": "2026-12-01",
            "duration_days": 4,
        },
    )
    assert created_resp.status_code == 201
    created = created_resp.json()
    project_id = created["id"]
    assert created["end_date"] == "2026-12-04"

    # Einzelabruf & 404
    assert client.get(f"/api/projects/{project_id}").status_code == 200
    assert client.get("/api/projects/999").status_code == 404

    # Ändern & Status setzen
    patched = client.patch(f"/api/projects/{project_id}", json={"baustelle": "Werder"})
    assert patched.status_code == 200
    assert patched.json()["baustelle"] == "Werder"

    status_resp = client.patch(
        f"/api/projects/{project_id}/status",
        json={"status": "in_arbeit"},
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "in_arbeit"

    # Suche & Kunden-Projekt-Ansicht
    search = client.get("/api/projects", params={"text": "Berger Carport", "status": "in_arbeit"})
    assert search.status_code == 200
    assert [item["id"] for item in search.json()] == [project_id]

    customers_resp = client.get("/api/projects/customers")
    assert customers_resp.status_code == 200
    assert customers_resp.json()["customers"] == [{"id": 4, "name": "Berger"}]

    by_customer = client.get("/api/projects/by-customer")
    assert by_customer.status_code == 200
    assert len(by_customer.json()) == 1
    assert by_customer.json()[0]["projects"][0]["id"] == project_id

    # Archivieren & wieder einblenden
    archived = client.post(f"/api/projects/{project_id}/archive", json={"archived": True})
    assert archived.status_code == 200
    assert archived.json()["archived"] is True
    assert client.get("/api/projects").json() == []
    assert len(client.get("/api/projects", params={"include_archived": True}).json()) == 1


# --- Werkzeuge nach S-09 und S-12 -----------------------------------------------


def test_werkzeug_katalog_ist_vollstaendig() -> None:
    expected = {
        "projekt_suchen",
        "projekt_anlegen",
        "projekt_aendern",
        "projekt_status_setzen",
        "projekt_archivieren",
    }
    assert set(tools.TOOLS) == expected
    for tool in tools.TOOLS.values():
        assert tool.beschreibung
        assert tool.art in (tools.KIND_READ, tools.KIND_DRAFT)
        assert tool.modul == "A"
        assert "args" in tool.beispiel and "ergebnis" in tool.beispiel


@pytest.mark.parametrize("tool_name", sorted(tools.TOOLS))
def test_jedes_werkzeug_liefert_sein_dokumentiertes_beispiel(
    session: Session,
    tool_name: str,
) -> None:
    seed_example_data(session)
    tool = tools.TOOLS[tool_name]
    result = tools.call_tool(session, tool.name, tool.beispiel["args"])
    assert result == tool.beispiel["ergebnis"]


def test_werkzeuge_entwurf_bestaetigen_und_verwerfen(session: Session) -> None:
    # 1. projekt_anlegen legt erst einen Entwurf an – noch kein echtes Projekt in der Liste
    res_create = tools.call_tool(
        session,
        "projekt_anlegen",
        {"kunde_id": 5, "name": "Dachstuhl", "baustelle_ort": "Spandau", "start": "2026-12-10"},
    )
    assert res_create["status"] == "ok"
    assert service.list_projects(session) == []

    # Erst nach confirm_draft existiert das Projekt
    created = service.confirm_draft(session, res_create["entwurf_id"])
    assert created.name == "Dachstuhl"
    assert created.baustelle == "Spandau"
    assert created.start_date == date(2026, 12, 10)

    # 2. projekt_aendern und projekt_status_setzen als Entwurf + Bestätigung
    res_edit = tools.call_tool(
        session,
        "projekt_aendern",
        {"projekt_id": created.id, "felder": {"baustelle_ort": "Falkensee", "dauer_tage": 5}},
    )
    assert res_edit["status"] == "ok"
    assert service.get_project(session, created.id).baustelle == "Spandau"  # type: ignore[union-attr]
    updated = service.confirm_draft(session, res_edit["entwurf_id"])
    assert updated.baustelle == "Falkensee"
    assert updated.end_date == date(2026, 12, 14)

    res_status = tools.call_tool(
        session,
        "projekt_status_setzen",
        {"projekt_id": created.id, "status": "abgeschlossen"},
    )
    confirmed_status = service.confirm_draft(session, res_status["entwurf_id"])
    assert confirmed_status.status == "abgeschlossen"

    # 3. projekt_archivieren verwerfen → Projekt bleibt aktiv
    res_arch = tools.call_tool(session, "projekt_archivieren", {"projekt_id": created.id})
    service.reject_draft(session, res_arch["entwurf_id"])
    assert service.get_project(session, created.id).archived is False  # type: ignore[union-attr]


def test_werkzeuge_rueckfragen_fehler_und_trefferlimit(
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Unbekanntes Werkzeug
    unknown = tools.call_tool(session, "gibt_es_nicht", {})
    assert unknown["status"] == "fehler"
    assert unknown["fehler"]["code"] == "unbekannt"

    # Fehlende Pflichtangabe → Rückfrage statt Raten
    missing = tools.call_tool(session, "projekt_anlegen", {"name": "Carport"})
    assert missing["status"] == "rueckfrage"
    assert missing["rueckfrage"]["feld"] == "kunde_id"

    # Leeres felder-Dict → Rückfrage
    seed_example_data(session)
    empty_fields = tools.call_tool(session, "projekt_aendern", {"projekt_id": 1, "felder": {}})
    assert empty_fields["status"] == "rueckfrage"
    assert empty_fields["rueckfrage"]["feld"] == "felder"

    # Unbekannter Kunde (wenn F2 aktiv) → fehler
    _install_fake_customers(monkeypatch, {4: "Berger"})
    bad_customer = tools.call_tool(
        session,
        "projekt_anlegen",
        {"kunde_id": 999, "name": "Schuppen"},
    )
    assert bad_customer["status"] == "fehler"
    assert bad_customer["fehler"]["code"] == "ungueltig"

    # Ungültiges Datum oder falscher Typ stürzen nicht ab
    bad_date = tools.call_tool(
        session,
        "projekt_anlegen",
        {"kunde_id": 4, "name": "Schuppen", "start": "kein-datum"},
    )
    assert bad_date["status"] == "fehler"

    bad_arg = tools.call_tool(session, "projekt_suchen", {"unbekannt": 1})
    assert bad_arg["status"] == "fehler"

    # Suche liefert höchstens 10 Treffer (S-09)
    for index in range(12):
        service.create_project(session, customer_id=4, name=f"Auftrag {index}")
    hits = tools.call_tool(session, "projekt_suchen", {"kunde_id": 4})
    assert hits["status"] == "ok"
    assert len(hits["daten"]["treffer"]) == service.MAX_SEARCH_RESULTS


@pytest.mark.parametrize("tool_name", sorted(tools.TOOLS))
def test_jedes_beispiel_passt_zu_den_schemata(session: Session, tool_name: str) -> None:
    seed_example_data(session)
    tool = tools.TOOLS[tool_name]
    assert tools.schema_violation(tool.beispiel["args"], tool.schema_ein) is None
    result = tools.call_tool(session, tool.name, tool.beispiel["args"])
    # schema_aus beschreibt nach S-09 nur „daten“, also die Antwort lesender Werkzeuge.
    if "daten" in result:
        assert tools.schema_violation(result["daten"], tool.schema_aus) is None


@pytest.mark.parametrize(
    ("tool_name", "args", "field"),
    [
        ("projekt_suchen", {"text": 5}, "text"),
        ("projekt_suchen", {"status": 5}, "status"),
        ("projekt_suchen", {"status": "fertig"}, "status"),
        ("projekt_suchen", {"archivierte_anzeigen": "false"}, "archivierte_anzeigen"),
        ("projekt_suchen", {"unbekannt": 1}, "unbekannt"),
        ("projekt_anlegen", {"kunde_id": "4", "name": "Carport"}, "kunde_id"),
        ("projekt_anlegen", {"kunde_id": 4, "name": "C", "dauer_tage": True}, "dauer_tage"),
        ("projekt_aendern", {"projekt_id": 1, "felder": "Werder"}, "felder"),
        ("projekt_aendern", {"projekt_id": 1, "felder": {"farbe": "rot"}}, "felder.farbe"),
        ("projekt_aendern", {"projekt_id": 1, "felder": {"start": 5}}, "felder.start"),
    ],
)
def test_werkzeug_nennt_bei_schemaverstoss_das_feld(
    session: Session,
    tool_name: str,
    args: dict,
    field: str,
) -> None:
    seed_example_data(session)
    result = tools.call_tool(session, tool_name, args)
    assert result["status"] == "fehler"
    assert result["fehler"]["code"] == "ungueltig"
    assert f"„{field}“" in result["fehler"]["meldung"]


def test_werkzeug_freiwillige_angabe_null_und_datumsformat(session: Session) -> None:
    seed_example_data(session)
    hits = tools.call_tool(session, "projekt_suchen", {"text": None, "kunde_id": None})
    assert hits["status"] == "ok"
    assert len(hits["daten"]["treffer"]) == 1

    for value in ("20261201", "2026-W49-1", "2026-13-01"):
        result = tools.call_tool(
            session,
            "projekt_anlegen",
            {"kunde_id": 4, "name": "Schuppen", "start": value},
        )
        assert result["status"] == "fehler"


# --- Zeitraum, Grenzwerte und Entwürfe ------------------------------------------


def _carport(session: Session):
    """Ein Projekt vom 01.12. bis 04.12. (4 Tage)."""
    seed_example_data(session)
    return service.get_project(session, 1)


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        # So schickt es die Oberfläche: alle Felder, nur eines wirklich geändert.
        (
            {"duration_days": 10, "end_date": date(2026, 12, 4)},
            (date(2026, 12, 1), 10, date(2026, 12, 10)),
        ),
        (
            {"start_date": date(2026, 12, 20), "end_date": date(2026, 12, 4)},
            (date(2026, 12, 20), 4, date(2026, 12, 23)),
        ),
        ({"end_date": date(2026, 12, 10)}, (date(2026, 12, 1), 10, date(2026, 12, 10))),
        ({"end_date": None}, (date(2026, 12, 1), 4, date(2026, 12, 4))),
        ({"duration_days": None}, (date(2026, 12, 1), None, date(2026, 12, 4))),
    ],
)
def test_zeitraum_bleibt_beim_aendern_stimmig(
    session: Session,
    fields: dict,
    expected: tuple,
) -> None:
    project = _carport(session)
    updated = service.update_project(session, project.id, fields)
    assert (updated.start_date, updated.duration_days, updated.end_date) == expected


def test_widerspruechlicher_oder_zu_spaeter_zeitraum_wird_abgelehnt(session: Session) -> None:
    with pytest.raises(ValueError, match="passen nicht zusammen"):
        service.create_project(
            session,
            customer_id=1,
            name="Carport",
            start_date=date(2026, 12, 1),
            duration_days=4,
            end_date=date(2026, 12, 20),
        )
    with pytest.raises(ValueError, match="zu weit"):
        service.create_project(
            session,
            customer_id=1,
            name="Carport",
            start_date=date(9999, 12, 30),
            duration_days=10,
        )


def test_riesige_nummern_sind_unbekannt_statt_absturz(
    session: Session,
    client: TestClient,
) -> None:
    huge = 10**30
    assert service.get_project(session, huge) is None
    assert service.get_customer(session, huge) is None
    with pytest.raises(ValueError, match="Kunde"):
        service.create_project(session, customer_id=huge, name="Carport")
    assert client.get(f"/api/projects/{huge}").status_code == 404
    assert client.get("/api/projects", params={"customer_id": huge}).status_code == 422
    assert client.patch(f"/api/projects/{huge}", json={"name": "x"}).status_code == 422


def test_abgelehnte_aenderung_hinterlaesst_nichts(session: Session) -> None:
    project = _carport(session)
    with pytest.raises(ValueError, match="Enddatum"):
        service.update_project(
            session,
            project.id,
            {"name": "Neuer Name", "end_date": date(2026, 1, 1)},
        )
    session.commit()  # eine spätere Speicherung darf nichts Halbes mitnehmen
    session.expire_all()
    assert service.get_project(session, project.id).name == "Carport"  # type: ignore[union-attr]


def test_entwurf_rechnet_erst_beim_bestaetigen(session: Session) -> None:
    project = _carport(session)
    draft_id = service.update_project_draft(session, project.id, {"duration_days": 20})
    service.update_project(session, project.id, {"start_date": date(2027, 3, 1)})

    confirmed = service.confirm_draft(session, draft_id)
    assert confirmed.start_date == date(2027, 3, 1)
    assert confirmed.end_date == date(2027, 3, 20)


def test_entwurf_nur_einmal_und_bei_fehler_weiter_offen(session: Session) -> None:
    project = _carport(session)
    draft_id = service.update_project_draft(
        session,
        project.id,
        {"end_date": date(2026, 12, 10)},
    )
    service.update_project(session, project.id, {"start_date": date(2027, 3, 1)})
    # Das verlangte Ende liegt inzwischen vor dem Beginn: Fehler, der Entwurf bleibt offen.
    with pytest.raises(ValueError, match="Enddatum"):
        service.confirm_draft(session, draft_id)
    service.reject_draft(session, draft_id)
    with pytest.raises(ValueError, match="bereits abgeschlossen"):
        service.confirm_draft(session, draft_id)

    create_id = service.create_project_draft(session, customer_id=4, name="Gaube")
    service.confirm_draft(session, create_id)
    with pytest.raises(ValueError, match="bereits abgeschlossen"):
        service.confirm_draft(session, create_id)
    assert len(service.list_projects(session)) == 2


def test_entwurf_nur_mit_kundenname(session: Session) -> None:
    project = _carport(session)
    draft_id = service.update_project_draft(session, project.id, {"customer_name": "Familie B."})
    assert service.confirm_draft(session, draft_id).customer_name == "Familie B."


def test_projekt_eines_entfernten_kunden_bleibt_aenderbar(
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _carport(session)
    _install_fake_customers(monkeypatch, {9: "Zimmerei Schulz"})  # Kunde 4 fehlt jetzt
    updated = service.update_project(
        session,
        project.id,
        {"customer_id": 4, "baustelle": "Werder"},
    )
    assert updated.baustelle == "Werder"
    assert updated.customer_name == "Berger"
