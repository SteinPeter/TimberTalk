# Tests für das Feature „Benutzerkonten und Rechte“ (F10).
# Fixtures aus backend/conftest.py: `session` für service.py, `anonymous_client` (nicht
# angemeldet), `client` (als Admin angemeldet) und `client_as("<rolle>")` für die Endpunkte.
# Jeder Test bekommt eine eigene, leere Datenbank.

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from timbertalk.features.accounts import security, service
from timbertalk.features.accounts.models import AccountSession


def _admin(session: Session):
    account, _ = service.create_account(session, "chef.admin", "Admin", "admin", None, "geheim123")
    return account


def _office_manager(session: Session, admin):
    """Ein Verwaltungs-Konto, dem der Admin das Recht „Konten verwalten“ gegeben hat."""
    service.set_role_permission(session, "office", "accounts.manage", True, admin)
    account, _ = service.create_account(session, "buero", "Büro", "office")
    return account


# --- Passwörter -------------------------------------------------------------------


def test_passwort_wird_nur_als_hash_gespeichert() -> None:
    stored = security.hash_password("zimmerei2026")
    assert "zimmerei2026" not in stored
    assert security.verify_password("zimmerei2026", stored)
    assert not security.verify_password("zimmerei2027", stored)
    # Zwei gleiche Passwörter ergeben verschiedene Hashes (eigenes Salz).
    assert stored != security.hash_password("zimmerei2026")


def test_neue_konten_bekommen_das_standardpasswort(session: Session) -> None:
    account, start = service.create_account(session, "max", "Max", "journeyman")
    assert start == service.DEFAULT_STANDARD_PASSWORD
    service.set_standard_password(session, " Zimmerei-2026 ")
    _, start2 = service.create_account(session, "tom", "Tom", "journeyman")
    assert start2 == "Zimmerei-2026"
    assert service.reset_password(session, account.id, None, _admin(session)) == "Zimmerei-2026"
    with pytest.raises(ValueError, match="mindestens"):
        service.set_standard_password(session, "kurz")
    # Als eigenes Passwort ist das Standardpasswort nicht erlaubt.
    with pytest.raises(ValueError, match="Standardpasswort"):
        service.change_own_password(session, account, "Zimmerei-2026", "Zimmerei-2026", "")


def test_foto_setzen_und_entfernen(session: Session) -> None:
    admin = _admin(session)
    max_, _ = service.create_account(session, "max", "Max", "journeyman")
    foto = "data:image/jpeg;base64,/9j/4AAQSkZJRg=="
    assert service.info(service.set_photo(session, max_.id, foto)).photo == foto
    assert service.set_photo(session, max_.id, None, admin).photo is None
    with pytest.raises(ValueError, match="JPEG"):
        service.set_photo(session, max_.id, "<svg onload=alert(1)>")
    with pytest.raises(ValueError, match="zu groß"):
        service.set_photo(session, max_.id, "data:image/png;base64," + "A" * 500_000)
    buero = _office_manager(session, admin)
    with pytest.raises(PermissionError):
        service.set_photo(session, admin.id, foto, buero)


# --- Konten anlegen ------------------------------------------------------------------


def test_konto_anlegen_mit_startpasswort_muss_beim_ersten_mal_wechseln(session: Session) -> None:
    account, start = service.create_account(
        session, " M.Berger ", "Max Berger", "journeyman", "017"
    )
    assert account.username == "m.berger"
    assert account.personnel_number == "017"
    assert account.must_change_password
    assert security.verify_password(start, account.password_hash)


@pytest.mark.parametrize(
    ("username", "role", "number", "text"),
    [
        ("", "journeyman", None, "Anmeldenamen"),
        ("max berger", "journeyman", None, "Leerzeichen"),
        ("max", "zauberer", None, "Rolle"),
        ("admin", "journeyman", None, "vergeben"),
        ("max", "journeyman", "001", "Personalnummer"),
        ("001", "journeyman", None, "vergeben"),  # Anmeldename = Personalnummer eines anderen
    ],
)
def test_konto_anlegen_prueft_die_angaben(
    session: Session, username: str, role: str, number: str | None, text: str
) -> None:
    service.create_account(session, "admin", "Admin", "admin", "001", "geheim123")
    with pytest.raises(ValueError, match=text):
        service.create_account(session, username, "Max", role, number)


def test_admin_konten_legt_nur_ein_admin_an(session: Session) -> None:
    buero = _office_manager(session, _admin(session))
    with pytest.raises(PermissionError):
        service.create_account(session, "neu", "Neu", "admin", acting=buero)


# --- Anmelden ------------------------------------------------------------------------


def test_anmelden_mit_name_oder_personalnummer(session: Session) -> None:
    service.create_account(session, "m.berger", "Max", "journeyman", "017", "geheim123")
    by_name, token = service.login(session, "M.Berger", "geheim123")
    by_number, _ = service.login(session, "017", "geheim123")
    assert by_name.id == by_number.id
    assert service.account_for_token(session, token).id == by_name.id
    assert by_name.last_login_at is not None


@pytest.mark.parametrize(("identifier", "password"), [("m.berger", "falsch!!"), ("gibts", "x")])
def test_falsche_anmeldung_verraet_nicht_was_falsch_war(
    session: Session, identifier: str, password: str
) -> None:
    service.create_account(session, "m.berger", "Max", "journeyman", None, "geheim123")
    with pytest.raises(service.LoginFailed, match="stimmen nicht"):
        service.login(session, identifier, password)


def test_gesperrtes_konto_kann_sich_nicht_anmelden_und_wird_abgemeldet(session: Session) -> None:
    admin = _admin(session)
    max_, _ = service.create_account(session, "max", "Max", "journeyman", None, "geheim123")
    _, token = service.login(session, "max", "geheim123")
    service.update_account(session, max_.id, "Max", "journeyman", None, False, admin)
    assert service.account_for_token(session, token) is None
    with pytest.raises(service.LoginFailed, match="gesperrt"):
        service.login(session, "max", "geheim123")


def test_abgelaufene_anmeldung_gilt_nicht_mehr(session: Session) -> None:
    service.create_account(session, "max", "Max", "journeyman", None, "geheim123")
    _, token = service.login(session, "max", "geheim123")
    stored = session.exec(select(AccountSession)).one()
    stored.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    session.add(stored)
    session.commit()
    assert service.account_for_token(session, token) is None


# --- Passwort ändern und zurücksetzen ---------------------------------------------------


def test_eigenes_passwort_aendern_beendet_andere_anmeldungen(session: Session) -> None:
    account, start = service.create_account(session, "max", "Max", "journeyman")
    _, handy = service.login(session, "max", start)
    _, buero = service.login(session, "max", start)
    service.change_own_password(session, account, start, "neues-passwort", keep_token=buero)
    assert not account.must_change_password
    assert service.account_for_token(session, buero) is not None
    assert service.account_for_token(session, handy) is None
    service.login(session, "max", "neues-passwort")


@pytest.mark.parametrize(
    ("old", "new", "text"),
    [
        ("falsch", "neues-passwort", "bisherige"),
        ("geheim123", "kurz", "mindestens"),
        ("geheim123", "max12345", "Anmeldename"),
        ("geheim123", "geheim123", "unterscheiden"),
    ],
)
def test_neues_passwort_wird_geprueft(session: Session, old: str, new: str, text: str) -> None:
    account, _ = service.create_account(session, "max12345", "Max", "journeyman", None, "geheim123")
    with pytest.raises(ValueError, match=text):
        service.change_own_password(session, account, old, new, keep_token="")


def test_admin_setzt_vergessenes_passwort_zurueck(session: Session) -> None:
    admin = _admin(session)
    max_, _ = service.create_account(session, "max", "Max", "journeyman", None, "geheim123")
    service.change_own_password(session, max_, "geheim123", "vergessen!", keep_token="")
    _, token = service.login(session, "max", "vergessen!")

    start = service.reset_password(session, max_.id, None, admin)

    assert service.account_for_token(session, token) is None  # überall abgemeldet
    account, _ = service.login(session, "max", start)
    assert account.must_change_password


def test_admin_konto_setzt_nur_ein_admin_zurueck(session: Session) -> None:
    admin = _admin(session)
    buero = _office_manager(session, admin)
    with pytest.raises(PermissionError):
        service.reset_password(session, admin.id, None, buero)


# --- Schutz vor dem Aussperren -------------------------------------------------------


def test_letzter_admin_bleibt_admin(session: Session) -> None:
    admin = _admin(session)
    other, _ = service.create_account(session, "zweit", "Zweiter", "admin")
    service.update_account(session, other.id, "Zweiter", "admin", None, False, admin)
    with pytest.raises(ValueError, match="eigene"):
        service.update_account(session, admin.id, "Admin", "master", None, True, admin)
    with pytest.raises(ValueError, match="mindestens ein aktives Admin"):
        service.update_account(session, admin.id, "Admin", "master", None, True, other)


def test_eigenes_konto_kann_man_nicht_sperren(session: Session) -> None:
    admin = _admin(session)
    with pytest.raises(ValueError, match="eigene"):
        service.update_account(session, admin.id, "Admin", "admin", None, False, admin)


def test_erstes_konto_beim_allerersten_start(session: Session) -> None:
    assert service.ensure_initial_admin(session)
    assert not service.ensure_initial_admin(session)  # nur einmal
    account, _ = service.login(session, "admin", "admin")
    assert account.role == "admin" and account.must_change_password


# --- Rechte --------------------------------------------------------------------------


def test_voreinstellung_geselle_sieht_keine_preise(session: Session) -> None:
    geselle, _ = service.create_account(session, "max", "Max", "journeyman")
    assert service.has_permission(session, geselle, "bookings.create")
    assert not service.has_permission(session, geselle, "finance.view")


def test_rechte_einer_rolle_aendern(session: Session) -> None:
    admin = _admin(session)
    geselle, _ = service.create_account(session, "max", "Max", "journeyman")
    service.set_role_permission(session, "journeyman", "finance.view", True, admin)
    assert service.has_permission(session, geselle, "finance.view")
    service.set_role_permission(session, "journeyman", "bookings.create", False, admin)
    assert not service.has_permission(session, geselle, "bookings.create")


def test_admin_behaelt_kontenverwaltung_urlaub_entscheidet_der_chef(session: Session) -> None:
    admin = _admin(session)
    chef, _ = service.create_account(session, "chef", "Chef", "owner")
    assert not service.has_permission(session, admin, "calendar.approve_absence")
    assert service.has_permission(session, chef, "calendar.approve_absence")
    with pytest.raises(ValueError, match="behält immer"):
        service.set_role_permission(session, "admin", "accounts.manage", False, chef)
    # Andere Häkchen des Admins lassen sich ändern.
    service.set_role_permission(session, "admin", "audit.view", False, chef)
    assert not service.has_permission(session, admin, "audit.view")
    admin_row = next(r for r in service.role_matrix(session).roles if r.role == "admin")
    assert admin_row.locked == ["accounts.manage"]


def test_rechte_je_konto_als_ausnahme_zur_rolle(session: Session) -> None:
    chef, _ = service.create_account(session, "chef", "Chef", "owner")
    max_, _ = service.create_account(session, "max", "Max", "journeyman")
    tom, _ = service.create_account(session, "tom", "Tom", "journeyman")
    # Max (Vorarbeiter) darf Preise sehen, obwohl Gesellen das nicht dürfen – Tom nicht.
    rights = service.set_account_permission(session, max_.id, "finance.view", True, chef)
    entry = next(r for r in rights if r.permission == "finance.view")
    assert (entry.from_role, entry.allowed, entry.overridden) == (False, True, True)
    assert service.has_permission(session, max_, "finance.view")
    assert not service.has_permission(session, tom, "finance.view")
    # Und umgekehrt: Max darf keinen Urlaub beantragen, obwohl die Rolle es darf.
    service.set_account_permission(session, max_.id, "calendar.request_absence", False, chef)
    assert not service.has_permission(session, max_, "calendar.request_absence")
    # None = wieder wie die Rolle.
    service.set_account_permission(session, max_.id, "finance.view", None, chef)
    assert not service.has_permission(session, max_, "finance.view")
    with pytest.raises(ValueError, match="selbst nehmen"):
        service.set_account_permission(session, chef.id, "accounts.manage", False, chef)


def test_eigene_rolle_verliert_nicht_die_kontenverwaltung(session: Session) -> None:
    buero = _office_manager(session, _admin(session))
    with pytest.raises(ValueError, match="eigenen Rolle"):
        service.set_role_permission(session, "office", "accounts.manage", False, buero)


# --- Endpunkte -----------------------------------------------------------------------


def test_api_ohne_anmeldung_gibt_es_nur_health_und_login(anonymous_client: TestClient) -> None:
    assert anonymous_client.get("/api/health").status_code == 200
    assert anonymous_client.get("/api/accounts/me").status_code == 401
    assert anonymous_client.get("/api/materials/items").status_code == 401
    falsch = anonymous_client.post("/api/accounts/login", json={"identifier": "x", "password": "y"})
    assert falsch.status_code == 401
    assert "stimmen nicht" in falsch.json()["detail"]


def test_api_erste_anmeldung_erst_passwort_dann_alles_andere(
    client: TestClient, anonymous_client: TestClient
) -> None:
    created = client.post(
        "/api/accounts",
        json={"username": "max", "display_name": "Max", "role": "journeyman"},
    )
    assert created.status_code == 201
    start = created.json()["start_password"]
    assert "password_hash" not in created.json()["account"]

    login = anonymous_client.post(
        "/api/accounts/login", json={"identifier": "max", "password": start}
    )
    assert login.status_code == 200
    assert login.json()["must_change_password"]
    assert "httponly" in login.headers["set-cookie"].lower()

    # Vor dem eigenen Passwort geht nur das Nötigste.
    assert anonymous_client.get("/api/materials/items").status_code == 403
    assert anonymous_client.get("/api/accounts/me").status_code == 200

    changed = anonymous_client.post(
        "/api/accounts/me/password",
        json={"old_password": start, "new_password": "mein-passwort"},
    )
    assert changed.status_code == 200
    assert not changed.json()["must_change_password"]
    assert anonymous_client.get("/api/materials/items").status_code == 200

    assert anonymous_client.post("/api/accounts/logout").status_code == 204
    assert anonymous_client.get("/api/accounts/me").status_code == 401


def test_api_me_nennt_rolle_und_rechte(client_as: Callable[[str], TestClient]) -> None:
    me = client_as("journeyman").get("/api/accounts/me").json()
    assert me["role_label"] == "Geselle"
    assert me["permissions"] == [
        "bookings.create",
        "calendar.request_absence",
        "calendar.view_all",
        "hours.book_own",
    ]


def test_api_kontenverwaltung_nur_mit_recht(client_as: Callable[[str], TestClient]) -> None:
    geselle = client_as("journeyman")
    response = geselle.get("/api/accounts")
    assert response.status_code == 403
    assert "Konten verwalten" in response.json()["detail"]
    assert geselle.get("/api/accounts/roles").status_code == 403

    assert client_as("admin").get("/api/accounts").status_code == 200
    # Ohne Häkchen darf auch die Verwaltung keine Konten verwalten.
    assert client_as("office").get("/api/accounts").status_code == 403


def test_api_konto_aendern_und_zuruecksetzen(client: TestClient) -> None:
    account_id = client.post(
        "/api/accounts",
        json={
            "username": "max",
            "display_name": "Max",
            "role": "journeyman",
            "personnel_number": "017",
            "start_password": "anfang-123",
        },
    ).json()["account"]["id"]

    changed = client.put(
        f"/api/accounts/{account_id}",
        json={"display_name": "Max Berger", "role": "master", "personnel_number": "017"},
    )
    assert changed.json()["role_label"] == "Meister"

    reset = client.post(f"/api/accounts/{account_id}/reset-password", json={})
    assert reset.status_code == 200
    assert reset.json()["start_password"] == "timbertalk-start"

    assert client.put("/api/accounts/999", json=changed.json()).status_code == 404


def test_api_rollen_und_rechte(client: TestClient, client_as: Callable[[str], TestClient]) -> None:
    geselle = client_as("journeyman")
    assert geselle.get("/api/materials/projects/1/costs").status_code == 403

    matrix = client.put(
        "/api/accounts/roles/journeyman/permissions/finance.view", json={"allowed": True}
    )
    assert matrix.status_code == 200
    assert geselle.get("/api/materials/projects/1/costs").status_code == 200

    falsch = client.put("/api/accounts/roles/journeyman/permissions/zaubern", json={"allowed": 1})
    assert falsch.status_code == 422


def test_rollen_in_der_reihenfolge_der_anzeige(session: Session) -> None:
    assert [row.label for row in service.role_matrix(session).roles] == [
        "Admin",
        "Chef",
        "Meister",
        "Verwaltung",
        "Geselle",
        "Azubi",
    ]
    with pytest.raises(ValueError, match="Rolle"):
        service.create_account(session, "x", "X", "zauberer")


# --- Sperre nach Fehlversuchen und Azubi -----------------------------------------------


def test_nach_fuenf_falschen_passwoertern_kurz_gesperrt(session: Session) -> None:
    admin = _admin(session)
    max_, _ = service.create_account(session, "max", "Max", "journeyman", None, "geheim123")
    for _ in range(service.MAX_FAILED_LOGINS - 1):
        with pytest.raises(service.LoginFailed, match="stimmen nicht"):
            service.login(session, "max", "falsch!!")
    with pytest.raises(service.LoginFailed, match="Zu viele"):
        service.login(session, "max", "falsch!!")
    # Auch mit dem richtigen Passwort geht es jetzt nicht.
    with pytest.raises(service.LoginFailed, match="gesperrt"):
        service.login(session, "max", "geheim123")
    assert service.info(max_).locked_until is not None

    # Der Admin setzt das Passwort zurück – damit ist die Sperre aufgehoben.
    start = service.reset_password(session, max_.id, None, admin)
    service.login(session, "max", start)


def test_sperre_endet_von_selbst_und_erfolg_setzt_den_zaehler_zurueck(session: Session) -> None:
    max_, _ = service.create_account(session, "max", "Max", "journeyman", None, "geheim123")
    max_.locked_until = datetime.now(UTC) - timedelta(seconds=1)  # Sperre gerade abgelaufen
    max_.failed_logins = 3
    session.add(max_)
    session.commit()
    account, _ = service.login(session, "max", "geheim123")
    assert account.failed_logins == 0 and account.locked_until is None


def test_azubi_bucht_und_sieht_keine_preise(session: Session) -> None:
    azubi, _ = service.create_account(session, "lena", "Lena", "apprentice")
    assert service.info(azubi).role_label == "Azubi"
    assert service.has_permission(session, azubi, "bookings.create")
    assert not service.has_permission(session, azubi, "finance.view")


def test_personenliste_fuer_andere_features_ohne_gesperrte_und_admin(session: Session) -> None:
    admin = _admin(session)
    service.create_account(session, "max", "Max Berger", "journeyman")
    weg, _ = service.create_account(session, "weg", "Alt Geselle", "journeyman")
    service.update_account(session, weg.id, "Alt Geselle", "journeyman", None, False, admin)
    people = service.list_people(session)
    # Das Admin-Konto ist nur zum Verwalten da: keine Person im Kalender oder unter „Personal“.
    assert [p.display_name for p in people] == ["Max Berger"]
    assert "role" not in people[0].model_dump_json()  # die Rolle sieht nur der Admin


def test_api_standardpasswort_und_foto(
    client: TestClient, client_as: Callable[[str], TestClient]
) -> None:
    assert client.get("/api/accounts/standard-password").json() == {
        "start_password": "timbertalk-start"
    }
    changed = client.put(
        "/api/accounts/standard-password", json={"start_password": "Zimmerei-2026"}
    )
    assert changed.status_code == 200
    assert client_as("journeyman").get("/api/accounts/standard-password").status_code == 403

    geselle = client_as("journeyman")
    foto = "data:image/png;base64,iVBORw0KGgo="
    assert geselle.put("/api/accounts/me/photo", json={"photo": foto}).json()["photo"] == foto
    assert geselle.get("/api/accounts/me").json()["photo"] == foto
    # Im Änderungsprotokoll steht das Standardpasswort nicht.
    event = client.get("/api/audit").json()
    assert not any("Zimmerei-2026" in e["details"] for e in event)


def test_api_rechte_je_konto(client_as: Callable[[str], TestClient]) -> None:
    chef = client_as("owner")
    geselle = client_as("journeyman")
    geselle_id = geselle.get("/api/accounts/me").json()["id"]
    assert geselle.get("/api/materials/projects/1/costs").status_code == 403
    changed = chef.put(
        f"/api/accounts/{geselle_id}/permissions/finance.view", json={"allowed": True}
    )
    assert changed.status_code == 200
    assert geselle.get("/api/materials/projects/1/costs").status_code == 200
    assert "finance.view" in geselle.get("/api/accounts/me").json()["permissions"]
    assert geselle.get(f"/api/accounts/{geselle_id}/permissions").status_code == 403


# --- Demo-Modus und Anmeldedaten für die Entwicklung -----------------------------------


def test_demo_login_nur_wenn_der_demo_modus_an_ist(session: Session) -> None:
    max_, _ = service.create_account(session, "max", "Max", "journeyman")
    with pytest.raises(PermissionError, match="aus"):
        service.demo_login(session, max_.id)
    service.set_demo_mode(session, True, max_.id)
    account, token = service.demo_login(session, None)  # das voreingestellte Konto
    assert account.id == max_.id
    assert service.account_for_token(session, token).id == max_.id
    # Im Demo-Modus muss Max nicht erst ein eigenes Passwort festlegen.
    assert not service.me(session, account).must_change_password
    service.set_demo_mode(session, False, None)
    assert service.me(session, account).must_change_password


def test_anmeldedaten_fuer_die_entwicklung(session: Session) -> None:
    service.ensure_initial_admin(session)
    info = service.login_info(session, show_hint=True)
    assert info.hint.initial_admin and info.hint.standard_password == "timbertalk-start"
    assert info.demo_people == []  # Demo-Modus aus: keine Konten zum Anklicken
    assert service.login_info(session, show_hint=False).hint is None
    admin, _ = service.login(session, "admin", "admin")
    service.change_own_password(session, admin, "admin", "eigenes-passwort", "")
    assert not service.login_info(session, show_hint=True).hint.initial_admin


def test_api_demo_modus(client: TestClient, anonymous_client: TestClient) -> None:
    assert anonymous_client.post("/api/accounts/demo-login", json={}).status_code == 403
    max_id = client.post(
        "/api/accounts",
        json={"username": "max", "display_name": "Max Berger", "role": "journeyman"},
    ).json()["account"]["id"]
    saved = client.put("/api/accounts/demo-mode", json={"enabled": True, "account_id": max_id})
    assert saved.json() == {"enabled": True, "account_id": max_id}

    info = anonymous_client.get("/api/accounts/login-info").json()
    assert info["demo_mode"] and info["demo_account_id"] == max_id
    assert "Max Berger" in [p["display_name"] for p in info["demo_people"]]

    me = anonymous_client.post("/api/accounts/demo-login", json={})
    assert me.status_code == 200 and me.json()["display_name"] == "Max Berger"
    assert anonymous_client.get("/api/materials/items").status_code == 200  # ohne Passwortwechsel
    assert (
        anonymous_client.put("/api/accounts/demo-mode", json={"enabled": False}).status_code == 403
    )


def test_notfall_befehl_setzt_vergessenes_admin_passwort_zurueck(
    session: Session, engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    from timbertalk.features.accounts import cli

    admin = _admin(session)
    service.change_own_password(session, admin, "geheim123", "vergessen-123", "")
    for _ in range(service.MAX_FAILED_LOGINS):  # ausgesperrt
        with pytest.raises(service.LoginFailed):
            service.login(session, "chef.admin", "falsch!!")
    monkeypatch.setattr(cli, "get_engine", lambda: engine)
    assert cli.reset("chef.admin") == "chef.admin"
    session.expire_all()
    account, _ = service.login(session, "chef.admin", service.DEFAULT_STANDARD_PASSWORD)
    assert account.must_change_password
    with pytest.raises(LookupError):
        cli.reset("gibt-es-nicht")


def test_jedes_recht_steht_in_genau_einem_funktionsbereich() -> None:
    from timbertalk.features.accounts.permissions import AREAS, PERMISSIONS

    listed = [key for _, keys in AREAS for key in keys]
    assert sorted(listed) == sorted(PERMISSIONS), "Jedes Recht braucht genau einen Bereich in AREAS"


def test_rollen_und_rechte_nach_bereichen(session: Session) -> None:
    matrix = service.role_matrix(session)
    areas = list(dict.fromkeys(p.area for p in matrix.permissions))
    assert areas[:2] == ["Kalender", "Zeitkonto, Urlaub und Personal"]
    zeitkonto = [p.permission for p in matrix.permissions if p.area == areas[1]]
    assert zeitkonto == [
        "calendar.request_absence",
        "calendar.approve_absence",
        "employees.view_all",
        "employees.manage",
    ]
