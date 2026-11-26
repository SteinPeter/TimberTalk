# F12 – Dashboard mit Widgets (Handbuch-Kapitel)

> **Steckbrief:** `docs/features/F12-dashboard.md` · **Pate:** offen · **Stand:** 2026-11-26

## Dateien

| Datei | Wofür |
| --- | --- |
| `backend/timbertalk/features/dashboard/models.py` | Tabelle `DashboardLayout`, Antworten `WidgetInfo`, `LayoutInfo`. |
| `backend/timbertalk/features/dashboard/service.py` | `available_widgets()` sucht die Widget-Dateien; `get_layout()`, `save_layout()`. |
| `backend/timbertalk/features/dashboard/api.py` | Endpunkte unter `/api/dashboard`. |
| `backend/timbertalk/features/dashboard/test_dashboard.py` | Tests, auch: jedes Widget hat `title` und `render`. |
| `frontend/features/start/start.js` | Das Dashboard: lädt die Widgets, zeigt sie als Karten, „Anpassen“. Bauplan eines Widgets steht oben in der Datei. |
| `frontend/features/start/widgets/status.js` | Widget „Systemstatus“ (vorher der Inhalt von `start.js`). |
| `frontend/features/planning/widgets/absence-requests.js` | Widget „Offene Urlaubsanträge“ (Recht `calendar.approve_absence`). |
| `frontend/features/planning/widgets/my-week.js` | Widget „Meine nächsten Termine“. |
| `frontend/features/bookings/widgets/hours-today.js` | Widget „Stunden heute“ (Recht `hours.book_own`). |

Geändert: `backend/tests/test_health.py` (der Text „TimberTalk läuft“ steht jetzt im Widget),
`audit/middleware.py` (`/api/dashboard/layout` wird nicht protokolliert), `frontend/style.css`
(Klassen `dashboard-…`).

## Endpunkte

| Methode und Adresse | Recht | Service-Funktion | Was sie tut |
| --- | --- | --- | --- |
| `GET /api/dashboard/widgets` | angemeldet | `available_widgets()` | Alle Widgets: `id` („planning/my-week“) und `path` der Datei. |
| `GET /api/dashboard/layout` | angemeldet | `get_layout()` | Die eigene Auswahl – `null`: noch nichts gewählt. |
| `PUT /api/dashboard/layout` | angemeldet | `save_layout()` | Auswahl und Reihenfolge speichern; `null` = Voreinstellung. |

## Tabellen

| Tabelle | Spalten | Verweist auf |
| --- | --- | --- |
| `dashboard_layout` | `account_id` (Schlüssel), `widgets` (JSON-Liste der Widget-Namen) | Konto aus F10 (ohne Fremdschlüssel) |

## Wie das Dashboard entsteht

1. `start.js` fragt `GET /api/dashboard/widgets`. Das Backend sucht mit
   `FEATURES_DIR.glob("*/widgets/*.js")` – ein neues Widget ist also nur eine neue Datei.
2. `start.js` lädt jede Datei mit `import()`. Widgets mit `permission`, das man nicht hat, fallen
   weg (`can()`); der Rest wird nach `order` sortiert.
3. Ohne eigene Auswahl zeigt es die Widgets mit `defaultOn`; sonst die gespeicherte Liste.
4. Je Widget eine Karte mit `title`; `render(container)` füllt sie. Ein Fehler in einem Widget
   zeigt nur in dieser Karte eine Meldung.
5. „Anpassen“ zeigt alle erlaubten Widgets mit Häkchen und ↑/↓ und speichert mit
   `PUT /api/dashboard/layout`.
6. Antwortet das Backend nicht, zeigt das Dashboard nur den Systemstatus.

## Abhängigkeiten zu anderen Features

- F10 `accounts`: `deps.current_account`. Die Widgets selbst benutzen die Endpunkte ihres Features.

## Begriffe

| Begriff | Im Code |
| --- | --- |
| Dashboard | Reiter `start` |
| Widget | `frontend/features/<ordner>/widgets/<name>.js`, Name `<ordner>/<name>` |
| Eigene Auswahl | `DashboardLayout` |
