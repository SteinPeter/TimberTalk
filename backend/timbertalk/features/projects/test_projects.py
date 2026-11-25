# Prüft Projekte auf einer echten Testdatenbank; fehlende Nachbarservices werden markiert ersetzt.
from datetime import date
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from . import integration, service, tools
from .models import Project, ProjectStatus


@pytest.fixture
def customers(monkeypatch):
    # Ausschließlich Testdouble, kein produktiver Kundenersatz und keine fremde Tabelle.
    records = {4: SimpleNamespace(id=4, name="Berger"), 5: SimpleNamespace(id=5, name="Müller")}
    monkeypatch.setattr(
        integration.customers, "get_customer", lambda session, key: records.get(key), raising=False
    )
    monkeypatch.setattr(
        integration.customers,
        "list_customers",
        lambda session: list(records.values()),
        raising=False,
    )
    return records


@pytest.fixture
def project(session, customers):
    row = Project(id=12, name="Carport", customer_id=4, baustelle="Potsdam")
    session.add(row)
    session.commit()
    return row


def test_s03_existing_and_unknown(session, project):
    assert service.get_project(session, 12).customer_id == 4
    assert service.get_project(session, 999) is None
    assert service.get_customer(session, 4).name == "Berger"
    assert service.get_customer(session, 999) is None


def test_create_is_only_applied_after_confirmation(session, customers):
    args = {"kunde_id": 4, "name": "  Carport  ", "baustelle_ort": "Potsdam"}
    prepared = service.prepare_action(session, "projekt_anlegen", args)
    assert prepared["expected_version"] is None
    assert session.exec(select(Project)).all() == []
    result = service.apply_confirmed_action(session, "projekt_anlegen", args, expected_version=None)
    assert service.get_project(session, result["projekt_id"]).name == "Carport"
    # Der gemeinsame Bestätigungsservice muss die Transaktion abschließen.
    session.rollback()
    assert session.exec(select(Project)).all() == []


@pytest.mark.parametrize(
    "args,expected",
    [
        ({"name": "Carport"}, "rueckfrage"),
        ({"kunde_id": 4}, "rueckfrage"),
        ({"kunde_id": 999, "name": "Carport"}, "fehler"),
        ({"kunde_id": True, "name": "Carport"}, "fehler"),
        ({"kunde_id": "4", "name": "Carport"}, "fehler"),
        ({"kunde_id": 4, "name": "   "}, "fehler"),
        ({"kunde_id": 4, "name": "C", "dauer_tage": 0}, "fehler"),
        ({"kunde_id": 4, "name": "C", "start": "2026-02-30"}, "fehler"),
        ({"kunde_id": 4, "name": "C", "unexpected": 1}, "fehler"),
    ],
)
def test_invalid_create_never_writes(session, customers, args, expected):
    assert service.execute_project_tool(session, "projekt_anlegen", args)["status"] == expected
    assert session.exec(select(Project)).all() == []


def test_database_rejects_missing_customer(session):
    session.add(Project(name="Ohne Kunde"))
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


@pytest.mark.parametrize("status", list(ProjectStatus))
def test_all_five_statuses(session, project, status):
    service.apply_confirmed_action(
        session,
        "projekt_status_setzen",
        {"projekt_id": 12, "status": status.value},
        expected_version=1,
    )
    assert service.get_project(session, 12).status == status.value
    assert service.get_project(session, 12).version == 2


def test_change_and_stale_version(session, project):
    args = {"projekt_id": 12, "feldern": {"kunde_id": 5, "baustelle_ort": "Berlin"}}
    service.apply_confirmed_action(session, "projekt_aendern", args, expected_version=1)
    assert service.get_project(session, 12).customer_id == 5
    assert service.get_project(session, 12).baustelle == "Berlin"
    with pytest.raises(service.ProjectError, match="geändert"):
        service.apply_confirmed_action(session, "projekt_aendern", args, expected_version=1)


def test_customer_rechecked_at_confirmation(session, project, customers):
    args = {"projekt_id": 12, "status": "geplant"}
    service.prepare_action(session, "projekt_status_setzen", args)
    del customers[4]
    with pytest.raises(service.ProjectError) as error:
        service.apply_confirmed_action(session, "projekt_status_setzen", args, expected_version=1)
    assert error.value.code == "kunde_unbekannt"
    assert service.get_project(session, 12).status == "angefragt"


@pytest.mark.parametrize(
    "fields",
    [
        {},
        {"name": None},
        {"kunde_id": None},
        {"archived": True},
        {"version": 99},
        {"status": "geplant"},
    ],
)
def test_field_allowlist(session, project, fields):
    result = service.execute_project_tool(
        session, "projekt_aendern", {"projekt_id": 12, "feldern": fields}
    )
    assert result["status"] == "fehler"
    assert service.get_project(session, 12).version == 1


def test_archive_preserves_status_and_s03(session, project):
    service.apply_confirmed_action(
        session, "projekt_archivieren", {"projekt_id": 12}, expected_version=1
    )
    assert service.get_project(session, 12).status == "angefragt"
    assert service.list_projects(session)["treffer"] == []
    assert service.list_projects(session, archived=True)["treffer"][0]["projekt_id"] == 12
    assert service.list_customer_projects(session, 4, archived=True)[0]["archiviert"] is True
    with pytest.raises(service.ProjectError, match="Archivierte"):
        service.prepare_action(
            session, "projekt_status_setzen", {"projekt_id": 12, "status": "geplant"}
        )


def test_search_filters_and_ten_result_limit(session, project):
    for index in range(15):
        session.add(Project(name=f"Carport {index}", customer_id=4, baustelle="Berlin"))
    session.flush()
    result = service.list_projects(
        session, text="berger CARPORT", customer_id=4, status="angefragt"
    )
    assert len(result["treffer"]) == 10
    assert result["gesamt"] == 16
    assert result["weitere"] is True
    assert len(service.list_projects(session, offset=10)["treffer"]) == 6
    assert service.list_projects(session, text="%_")["treffer"] == []
    assert service.list_projects(session, customer_id=5)["treffer"] == []


def test_dates_include_start_day(session, project):
    project.start = date(2026, 11, 27)
    project.dauer_tage = 4
    assert service.project_data(session, project)["ende"] == "2026-11-30"
    result = service.execute_project_tool(
        session,
        "projekt_anlegen",
        {"kunde_id": 4, "name": "C", "start": "9999-12-31", "dauer_tage": 2},
    )
    assert result["status"] == "fehler"


@pytest.mark.parametrize("name", list(tools.EXAMPLES))
def test_every_registered_example(session, project, monkeypatch, name):
    # Prüft unseren Registrierungsadapter und jeden Handler; NICHT den fehlenden S-09-Katalog.
    registry = {}

    def werkzeug(**metadata):
        def register(handler):
            assert metadata["name"] not in registry
            assert metadata["modul"] == "A"
            assert metadata["schema_ein"]["type"] == "object"
            assert metadata["beschreibung"]
            registry[metadata["name"]] = (metadata, handler)
            return handler

        return register

    drafts = []

    def create_draft(db, tool_name, args, source, original_text):
        assert db is session
        drafts.append((tool_name, args, source))
        return {"entwurf_id": 7, "zusammenfassung": "Testentwurf"}

    monkeypatch.setattr(integration.drafts, "create_draft", create_draft, raising=False)
    tools.register_tools(werkzeug)
    assert set(registry) == set(service.INPUTS)
    definition, handler = registry[name]
    result = handler(session, definition["beispiel"])
    if name == "projekt_suchen":
        assert result == {
            "status": "ok",
            "daten": {
                "treffer": [
                    {
                        "projekt_id": 12,
                        "name": "Carport",
                        "kunde_id": 4,
                        "kunde": "Berger",
                        "baustelle_ort": "Potsdam",
                        "status": "angefragt",
                        "start": None,
                        "ende": None,
                        "dauer_tage": None,
                        "archiviert": False,
                        "version": 1,
                    }
                ],
                "gesamt": 1,
                "weitere": False,
            },
        }
        assert drafts == []
    else:
        assert result == {"status": "ok", "entwurf_id": 7, "zusammenfassung": "Testentwurf"}
        assert drafts[0][0] == name
    assert service.get_project(session, 12).version == 1
    assert len(session.exec(select(Project)).all()) == 1


def test_missing_dependency_fails_closed(session, customers, monkeypatch):
    monkeypatch.delattr(integration.drafts, "create_draft", raising=False)
    result = service.execute_project_tool(session, "projekt_anlegen", {"kunde_id": 4, "name": "C"})
    assert result["fehler"]["code"] == "nicht_verfuegbar"
    assert session.exec(select(Project)).all() == []


def test_api_search_and_customer_projects(client, project):
    assert client.get("/api/projects?text=Berger").json()["daten"]["treffer"][0]["projekt_id"] == 12
    assert client.get("/api/projects/customer/4").json()["daten"][0]["name"] == "Carport"
    assert client.get("/api/projects/customers").json()["daten"][0]["id"] == 4
    assert client.get("/api/projects?offset=-1").status_code == 422
    assert client.get("/api/projects?status=falsch").status_code == 422


def test_ui_dispatches_through_shared_catalog(client, monkeypatch):
    calls = []

    def call_tool(session, name, args, source, original_text):
        calls.append((name, args, source))
        return {"status": "ok", "entwurf_id": 7}

    monkeypatch.setattr(integration.drafts, "call_tool", call_tool, raising=False)
    response = client.post(
        "/api/projects/tools",
        json={"name": "projekt_anlegen", "args": {"kunde_id": 4, "name": "C"}, "quelle": "ui"},
    )
    assert response.json() == {"status": "ok", "entwurf_id": 7}
    assert calls == [("projekt_anlegen", {"kunde_id": 4, "name": "C"}, "ui")]


def test_ui_cannot_bypass_missing_catalog(client, monkeypatch):
    monkeypatch.delattr(integration.drafts, "call_tool", raising=False)
    response = client.post(
        "/api/projects/tools", json={"name": "projekt_archivieren", "args": {"projekt_id": 12}}
    )
    assert response.json()["fehler"]["code"] == "nicht_verfuegbar"
