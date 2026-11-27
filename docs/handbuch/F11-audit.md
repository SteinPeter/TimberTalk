# F11 – Änderungsprotokoll (Handbuch-Kapitel)

> **Steckbrief:** `docs/features/F11-audit.md` · **Pate:** offen · **Stand:** 2026-11-26

## Dateien

| Datei | Wofür |
| --- | --- |
| `backend/timbertalk/features/audit/models.py` | Tabelle `AuditEvent`. |
| `backend/timbertalk/features/audit/service.py` | `record()`, `list_events()`, `list_areas()`, `describe_body()` (Angaben lesbar, ohne Passwörter), `describe_target()`. |
| `backend/timbertalk/features/audit/middleware.py` | `AuditMiddleware`: schreibt erfolgreiche Änderungen mit. |
| `backend/timbertalk/features/audit/api.py` | `GET /api/audit`, `GET /api/audit/areas`. |
| `backend/timbertalk/features/audit/test_audit.py` | Tests. |
| `frontend/features/settings/sections/audit.js` | Abschnitt „Änderungsprotokoll“. |

In gemeinsamen Dateien geändert:

| Datei | Änderung |
| --- | --- |
| `backend/timbertalk/main.py` | `app.add_middleware(AuditMiddleware)`. |
| `backend/timbertalk/features/accounts/permissions.py` | Recht `audit.view` (Voreinstellung: nur Admin). |
| `api.py` von `accounts`, `materials`, `planning` | `summary="…"` an jedem ändernden Endpunkt. |
| `frontend/features/settings/sections.js`, `frontend/style.css` | Abschnitt eingetragen; Klassen `audit-…`. |

## Endpunkte

| Methode und Adresse | Recht | Service-Funktion | Was sie tut |
| --- | --- | --- | --- |
| `GET /api/audit?area=` | `audit.view` | `list_events()` | Die letzten 300 Einträge, neueste zuerst, wahlweise ein Bereich. |
| `GET /api/audit/areas` | `audit.view` | `list_areas()` | Alle Bereiche im Protokoll. |

## Tabellen

| Tabelle | Spalten (wichtigste) | Verweist auf |
| --- | --- | --- |
| `audit_event` | `created_at`, `account_id`, `account_name` (Name zu dem Zeitpunkt), `area`, `action`, `target`, `details`, `method`, `path` | – |

## Wie die Middleware arbeitet

1. Jede Anfrage läuft durch `AuditMiddleware.__call__`. Ist es keine Änderung unter `/api` oder
   steht die Adresse in `SKIP_PATHS` (an-/abmelden, Mitteilungen gelesen), reicht sie die Anfrage
   einfach weiter.
2. Sonst ersetzt sie `receive` und `send` durch zwei kleine Funktionen: die eine merkt sich den
   Body, die andere den Statuscode der Antwort. Die Anfrage selbst läuft unverändert.
3. Nach der Antwort: Status unter 400 → `_write()` in einem eigenen Thread (die Datenbank arbeitet
   nicht asynchron). Die gefundene Route steht in `scope["route"]`: Bereich = `route.tags[0]`,
   Was = `route.summary`. Das Konto kommt aus dem Cookie (`accounts.service.account_for_token()`).
4. Die Datenbank-Sitzung holt `_write()` genauso wie die Endpunkte über `get_session` – inklusive
   `app.dependency_overrides`, damit die Tests ihre Test-Datenbank bekommen.
5. `describe_body()` ersetzt alle Felder mit „password“, „token“ oder „secret“ im Namen durch
   „•••“ und kürzt Werte über 80 Zeichen (z. B. ein Logo).

## Abhängigkeiten zu anderen Features

- F10 `accounts`: `deps.session_token()`, `service.account_for_token()`, `deps.require()`.

## Begriffe

| Begriff | Im Code |
| --- | --- |
| Änderungsprotokoll | `audit` |
| Eintrag | `AuditEvent` (`audit_event`) |
| Bereich | `area` (= erster Tag des Routers) |
| Middleware | `AuditMiddleware` |
