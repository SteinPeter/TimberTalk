# F10 – Benutzerkonten und Rechte (Handbuch-Kapitel)

> **Steckbrief:** `docs/features/F10-accounts.md` · **Pate:** offen · **Stand:** 2026-11-26

## Dateien

| Datei | Wofür |
| --- | --- |
| `backend/timbertalk/features/accounts/permissions.py` | Rollen (`ROLES`), Rechte (`PERMISSIONS`) und die Voreinstellung (`DEFAULTS`). Ein neues Recht kommt hier dazu. |
| `backend/timbertalk/features/accounts/security.py` | Passwort-Hash mit `scrypt`, Startpasswörter, Sitzungsschlüssel und deren Hash. |
| `backend/timbertalk/features/accounts/models.py` | Die drei Tabellen und die Antwort- und Eingabeklassen. |
| `backend/timbertalk/features/accounts/service.py` | Die Logik: Konten, Anmelden, Passwörter, Rechte, erstes Admin-Konto. |
| `backend/timbertalk/features/accounts/deps.py` | Bausteine für alle Endpunkte: `require_login`, `current_account`, `require()`, `can()`. |
| `backend/timbertalk/features/accounts/api.py` | Die Endpunkte unter `/api/accounts`, setzt und löscht das Cookie. |
| `backend/timbertalk/features/accounts/test_accounts.py` | Tests für Passwörter, Konten, Anmeldung, Rechte und Endpunkte. |
| `frontend/shared/session.js` | `loadAccount()`, `currentAccount()`, `can()`, `logout()`. |
| `frontend/shared/login.js` | Anmeldeseite, „eigenes Passwort festlegen“ und das Formular `passwordForm()`. |
| `frontend/shared/dom.js` | Helfer für Formulare und Tabellen: `el()`, `field()`, `messageBox()`, `formatDateTime()`. |
| `frontend/features/settings/sections/accounts-own.js` | Abschnitt „Mein Konto“: Name, Anmeldename, Personalnummer, Passwort ändern. Für alle. Die Rolle steht nur in „Benutzerkonten“. |
| `frontend/features/settings/sections/accounts-manage.js` | Abschnitt „Benutzerkonten“: Liste, anlegen, bearbeiten, sperren, Passwort zurücksetzen. |
| `frontend/features/settings/sections/accounts-roles.js` | Abschnitt „Rollen und Rechte“: Tabelle mit Häkchen. |

In gemeinsamen Dateien geändert (Grundgerüst, siehe auch `docs/handbuch.md`):

| Datei | Änderung |
| --- | --- |
| `backend/timbertalk/main.py` | `require_login` an jedem Feature-Router; beim Start `ensure_initial_admin()`. |
| `backend/conftest.py` | Neue Fixtures `anonymous_client` und `client_as(role)`; `client` ist als Admin angemeldet. |
| `frontend/app.js` | Prüft beim Start die Anmeldung, zeigt sonst Anmeldung oder „Passwort festlegen“; Name (ohne Rolle) und „Abmelden“ in der Leiste; Reiter mit `permission` nur mit Recht. |
| `frontend/shared/api.js` | `sendJson()` dazu; bei 401 wird die Seite neu geladen (zurück zur Anmeldung); Fehlertext aus `detail`. |
| `frontend/shared/sections.js` | Abschnitte mit `permission` erscheinen nur mit diesem Recht. |
| `frontend/features/settings/sections.js` und `settings.js` | Drei Abschnitte eingetragen; Hinweistext ergänzt. |
| `frontend/style.css` | `.account` in der Leiste, gemeinsame Klassen `form-…`, `button…`, `table…`, `login-card` und `accounts-…`. |
| Feature F5 `materials/` | Rechte an den Endpunkten (siehe unten), `show_prices` in `list_materials()` und `list_bookings()`, neue Funktion `booking_info()`; im Frontend `permission` an den Einstellungs-Abschnitten und ausgeblendete Preise im Buchungs-Abschnitt. |

## Endpunkte

| Methode und Adresse | Recht | Service-Funktion | Was sie tut |
| --- | --- | --- | --- |
| `POST /api/accounts/login` | ohne Anmeldung | `login()` | Anmelden mit `identifier` (Name oder Personalnummer) und `password`; setzt das Cookie. |
| `POST /api/accounts/logout` | angemeldet | `logout()` | Beendet die Anmeldung auf diesem Gerät, löscht das Cookie. |
| `GET /api/accounts/me` | angemeldet | `me()` | Eigenes Konto mit Liste der Rechte. |
| `POST /api/accounts/me/password` | angemeldet | `change_own_password()` | Eigenes Passwort ändern; andere Geräte werden abgemeldet. |
| `GET /api/accounts` | `accounts.manage` | `list_accounts()` | Alle Konten. |
| `POST /api/accounts` | `accounts.manage` | `create_account()` | Konto anlegen; Antwort enthält das Startpasswort (einmalig). |
| `PUT /api/accounts/{id}` | `accounts.manage` | `update_account()` | Name, Rolle, Personalnummer, gesperrt. |
| `POST /api/accounts/{id}/reset-password` | `accounts.manage` | `reset_password()` | Neues Startpasswort, alle Anmeldungen enden. |
| `GET /api/accounts/roles` | `accounts.manage` | `role_matrix()` | Alle Rollen mit ihren Rechten. |
| `PUT /api/accounts/roles/{role}/permissions/{permission}` | `accounts.manage` | `set_role_permission()` | Ein Häkchen setzen oder entfernen. |

Fehler aus dem Service werden in `_run()` zu Antworten mit deutschem Text: `LoginFailed` → 401,
`PermissionError` → 403, `LookupError` → 404, `ValueError` → 422.

Rechte an den Endpunkten von F5 (`materials/api.py`):

| Endpunkt | Recht |
| --- | --- |
| `GET /items`, `GET /bookings` | angemeldet; ohne `finance.view` bleiben `preis`, `unit_price` und `amount` leer (`null`) |
| `POST /items` | `materials.edit` |
| `GET /items/{id}/prices`, `GET /company`, `GET /hourly-rates`, `GET /projects/{id}/costs` | `finance.view` |
| `POST /items/{id}/prices`, `PUT /company`, `PUT`/`DELETE /hourly-rates` | `finance.edit` |
| `POST /bookings/material`, `POST /bookings/travel` | `bookings.create`; die Antwort ist jetzt eine `BookingInfo` (ohne Preis, wenn man ihn nicht sehen darf) |

## Tabellen

| Tabelle | Spalten (wichtigste) | Verweist auf |
| --- | --- | --- |
| `accounts_account` | `username` (eindeutig, klein), `personnel_number` (eindeutig, freiwillig), `display_name`, `role`, `password_hash`, `must_change_password`, `active`, `last_login_at` | – |
| `accounts_session` | `token_hash` (eindeutig), `account_id`, `created_at`, `expires_at` | `accounts_account` |
| `accounts_role_permission` | `role`, `permission` (zusammen der Schlüssel), `allowed` | – |

In `accounts_role_permission` stehen nur **geänderte** Häkchen. Fehlt eine Zeile, gilt `DEFAULTS`
aus `permissions.py`. So bekommt ein neues Recht seine Voreinstellung, ohne dass jemand die
Tabelle anfasst.

## Wie Anmeldung und Prüfung funktionieren

1. **Passwort:** `security.hash_password()` speichert `scrypt$n$r$p$salz$hash`. Das Passwort selbst
   steht nirgends. `verify_password()` rechnet mit demselben Salz nach und vergleicht mit
   `hmac.compare_digest` (immer gleich lange, verrät nichts über Teil-Treffer). Gibt es den
   Anmeldenamen nicht, rechnet `login()` trotzdem einmal – sonst könnte man an der Antwortzeit
   erkennen, welche Namen es gibt.
2. **Sitzungsschlüssel:** Nach der Anmeldung erzeugt `security.new_session_token()` 32 Byte Zufall.
   Der Browser bekommt ihn als Cookie `timbertalk_session` (`HttpOnly`: JavaScript kommt nicht
   heran; `SameSite=Strict`: fremde Seiten können ihn nicht mitschicken). In `accounts_session`
   steht nur sein SHA-256-Hash und das Ablaufdatum (30 Tage). Für spätere Apps geht auch der Kopf
   `Authorization: Bearer <Schlüssel>`.
3. **Jede Anfrage:** `main.py` hängt `Depends(require_login)` an jeden Feature-Router.
   `require_login` liest den Schlüssel, sucht mit `account_for_token()` das Konto (abgelaufen oder
   gesperrt → 401) und lässt bei `must_change_password` nur die drei Adressen in
   `PASSWORD_CHANGE_PATHS` zu (sonst 403). `/api/accounts/login` steht in `PUBLIC_PATHS` und geht
   ohne Anmeldung. `/api/health` hängt direkt an der App und ist ebenfalls frei.
4. **Rechte:** `require("finance.edit")` holt das Konto über `current_account` und fragt
   `has_permission()`. Das nimmt `DEFAULTS[rolle]` und legt die geänderten Häkchen darüber. Der
   Admin hat immer alle Rechte. Ein Tippfehler im Namen eines Rechts fällt schon beim Start auf
   (`RuntimeError`), nicht erst bei der ersten Anfrage.
5. **Schutz vor dem Aussperren:** Es bleibt immer ein aktives Admin-Konto. Man kann das eigene
   Konto nicht sperren, die eigene Rolle nicht ändern und der eigenen Rolle nicht
   `accounts.manage` nehmen. Admin-Konten bearbeitet nur ein Admin.
6. **Erster Start:** `lifespan()` in `main.py` ruft `ensure_initial_admin()`. Gibt es noch kein
   Konto, entsteht `admin` / `admin` mit `must_change_password=True`. Das steht auch in der Konsole.

## Weg einer typischen Anfrage

Ein Geselle öffnet „Buchungen“ und wählt Projekt 12:

1. `materials.js` fragt `can("finance.view")` aus `shared/session.js` → `false`. Spalten Preis und
   Betrag und der Kasten „Gesamtkosten“ werden gar nicht erst gebaut.
2. `getJson("/api/materials/bookings?project_id=12")`; der Browser schickt das Cookie mit.
3. `require_login` (aus `main.py`) prüft die Anmeldung. Im Endpunkt liefert `can("finance.view")`
   den Wert `False` als Parameter `show_prices`.
4. `service.list_bookings(session, 12, show_prices=False)` gibt die Buchungen ohne Preis und
   Betrag zurück.
5. Fragt der Geselle trotzdem `/api/materials/projects/12/costs`, antwortet `require("finance.view")`
   mit 403 und „Dafür fehlt Ihnen das Recht …“.

## Für andere Features: Rechte benutzen

```python
from timbertalk.features.accounts.deps import can, current_account, require
from timbertalk.features.accounts.models import Account

@router.post("/invoices")
def create_invoice(..., account: Account = Depends(require("finance.edit"))): ...
```

Ein neues Recht: eine Zeile in `PERMISSIONS` und das Recht in `DEFAULTS` bei den Rollen, die es von
Anfang an haben sollen. In der Oberfläche erscheint es dann von selbst in „Rollen und Rechte“.

## Abhängigkeiten zu anderen Features

Keine. Umgekehrt benutzt F5 (`materials`) `require()` und `can()` aus `deps.py`. Das ist die
Ausnahme von der Regel „nur über `service.py`“ und so im Programmaufbau (Kapitel 10) vorgesehen.

## Begriffe

| Begriff | Im Code |
| --- | --- |
| Konto | `Account` |
| Rolle (Admin, Chef, Meister, Verwaltung, Geselle) | `role`: `admin`, `owner`, `master`, `office`, `journeyman` |
| Recht | `permission`, z. B. `finance.view` |
| Anmeldung auf einem Gerät | `AccountSession` |
| Sitzungsschlüssel | `token` (im Cookie), `token_hash` (in der Datenbank) |
| Startpasswort | `start_password`; danach `must_change_password` |
| Personalnummer | `personnel_number` |
