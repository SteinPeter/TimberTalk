# F3 – Projekte (Handbuch-Kapitel)

> **Steckbrief:** `docs/features/F03-projects.md` · **Pate:** Licheng Ou, Tingyu Li · **Stand:** 2026-11-25

## Dateien

| Datei | Wofür |
| --- | --- |
| `backend/timbertalk/features/projects/models.py` | Tabellen `Project` und `ProjectDraft`, Statuskonstanten sowie Eingabe- und Antwortklassen. |
| `backend/timbertalk/features/projects/service.py` | Geschäftslogik: Projekte suchen, anlegen, ändern, Status setzen, archivieren, S-03 (`get_project`, `get_customer`), Kunden-Gruppierung und Entwürfe (`confirm_draft`, `reject_draft`). |
| `backend/timbertalk/features/projects/api.py` | REST-Endpunkte unter `/api/projects`. |
| `backend/timbertalk/features/projects/tools.py` | Fünf KI-Werkzeuge nach S-09 / S-12 (`TOOLS` und `call_tool()`). |
| `backend/timbertalk/features/projects/test_projects.py` | Tests für Service, S-03 (mit und ohne F2), Endpunkte und alle Werkzeuge. |
| `frontend/features/projects/projects.js` | Reiter „Projekte“: Suche, Filter, Ansicht „Alle Projekte“ und „Nach Kunde“, Formular zum Anlegen/Bearbeiten, Statuswechsel und Archivieren. |
| `frontend/features/projects/projects.css` | Gestaltung des Reiters im eigenen Ordner; nutzt ausschließlich die Farbvariablen aus `style.css`. |

Es werden **keine gemeinsamen Dateien** geändert. Daraus folgen zwei Abweichungen, die mit den
Leads abzustimmen sind:

- Das Handbuch (Abschnitt 7) sieht CSS in `style.css` vor. F3 lädt stattdessen `projects.css`
  selbst (`ensureStylesheet()`).
- `shared/api.js` kennt nur `getJson()`. Schreibende Anfragen schickt `sendJson()` in
  `projects.js`.

## Endpunkte

| Methode und Adresse | Service-Funktion | Was sie tut |
| --- | --- | --- |
| `GET /api/projects?text=&customer_id=&status=&include_archived=` | `list_projects()` | Sucht und filtert Projekte (standardmäßig ohne archivierte). |
| `POST /api/projects` | `create_project()` | Legt ein neues Projekt zu einem Kunden an (ohne Kunde: 422). |
| `GET /api/projects/customers` | `list_customers()` | Liefert Kunden für die Auswahl im Frontend (aus F2 oder aus vorhandenen Projekten). |
| `GET /api/projects/by-customer?include_archived=` | `list_customer_projects()` | Gruppiert alle Projekte je Kunde. |
| `GET /api/projects/{project_id}` | `get_project()` | Liefert ein einzelnes Projekt (sonst 404). |
| `PATCH /api/projects/{project_id}` | `update_project()` | Ändert die übergebenen Felder eines Projekts. |
| `PATCH /api/projects/{project_id}/status` | `set_project_status()` | Setzt den Status eines Projekts. |
| `POST /api/projects/{project_id}/archive` | `archive_project()` | Archiviert ein Projekt (`archived: true`) oder stellt es wieder her (`archived: false`). |

Fehler aus dem Service werden in `api.py` über `_run()` übersetzt: `LookupError` → 404,
`ValueError` → 422 mit deutschem Fehlertext.

Zusätzliche Service-Funktionen ohne eigenen Endpunkt (für andere Features):
- `get_project(session, project_id)` und `get_customer(session, customer_id)` für Team B (S-03) und F5.
- `list_projects_for_customer(session, customer_id)` für die Kundenliste in F2.
- `create_project_draft()`, `update_project_draft()`, `set_project_status_draft()`,
  `archive_project_draft()`, `confirm_draft()` und `reject_draft()` für F7 und `tools.py`.

## Tabellen

Alle Tabellennamen beginnen mit `projects_`.

| Tabelle | Spalten (wichtigste) | Verweist auf |
| --- | --- | --- |
| `projects_project` | `id`, `customer_id`, `customer_name`, `name`, `site_address`, `status`, `start_date`, `duration_days`, `end_date`, `notes`, `archived` | `customer_id` (logischer Verweis auf F2) |
| `projects_draft` | `id`, `action`, `project_id`, `payload_json`, `status` | `projects_project` (optional bei `update`, `set_status`, `archive`) |

- Erlaubte Statuswerte: `angefragt`, `geplant`, `in_arbeit`, `abgeschlossen`, `abgerechnet`.

## Zeitraum

- Sind `start_date` und `duration_days` angegeben, aber kein `end_date`, berechnet `service.py`
  `end_date = start_date + (duration_days - 1) Tage`. Gezählt werden Kalendertage.
- Passen alle drei Angaben nicht zusammen oder liegt das Ende vor dem Beginn, wird abgelehnt.
- Beim Ändern (`_merge_schedule()`) zählt, was sich wirklich ändert: Bei neuem Beginn oder neuer
  Dauer rückt das Ende nach, bei neuem Ende und gleicher Dauer rückt die Dauer nach. Ein
  unverändert mitgeschicktes Feld zählt nicht – deshalb darf die Oberfläche immer alle Felder
  senden.
- `projects.js` rechnet beim Ausfüllen genauso (`syncEndDate()`, `syncDuration()`).

## Ändern ohne halbe Stände

`update_project()` prüft zuerst alles (`_clean_changes()`, `_merge_schedule()`) und schreibt erst
dann in das Objekt. So bleibt nach einer abgelehnten Änderung nichts in der Sitzung zurück. Bleibt
der Kunde derselbe, wird er nicht erneut gegen F2 geprüft.

## Weg einer typischen Anfrage

Neues Projekt im Reiter „Projekte“ anlegen:

1. Der Zimmerer klickt auf „Neues Projekt“, wählt einen Kunden, trägt Name („Carport“), Baustelle
   („Potsdam“), Startdatum und Dauer ein und klickt auf „Projekt anlegen“.
2. `projects.js` sendet `POST /api/projects` über `sendJson()`.
3. `create_project()` in `api.py` ruft `service.create_project()` auf (über `_run()`).
4. Der Service prüft Kundennummer (über `customers/service.py`, sobald F2 aktiv ist), Name, Status
   und Zeitraum, berechnet das Enddatum und speichert die Zeile in `projects_project`.
5. Das neue `ProjectInfo` geht als JSON zurück. `projects.js` schließt das Formular, zeigt eine
   Bestätigungsmeldung und lädt Liste sowie Kundenansicht neu.

Derselbe Vorgang durch die KI: `call_tool(session, "projekt_anlegen", args)` in `tools.py` ruft
`service.create_project_draft()` auf. Das Projekt landet zuerst in `projects_draft` und entsteht
erst nach `service.confirm_draft(session, entwurf_id)`.

Der Reiter lädt neu, wenn man auf ihn oder in das Browser-Fenster zurückkehrt (`hashchange`,
`visibilitychange`), weil `app.js` jeden Reiter nur einmal aufbaut. So erscheinen Einträge von
anderen Geräten (LS-03) und neue Kunden. Eine verspätete Antwort überschreibt keine neuere
(`listRequest`, `overviewRequest`).

## Werkzeuge (S-09, S-12)

| Werkzeug | Art | Service-Funktion |
| --- | --- | --- |
| `projekt_suchen` | `lesen` | `list_projects(..., limit=10)` |
| `projekt_anlegen` | `entwurf` | `create_project_draft()` |
| `projekt_aendern` | `entwurf` | `update_project_draft()` |
| `projekt_status_setzen` | `entwurf` | `set_project_status_draft()` |
| `projekt_archivieren` | `entwurf` | `archive_project_draft()` |

`test_projects.py` prüft automatisch für jedes registrierte Werkzeug, dass `call_tool()` mit dem
hinterlegten `beispiel["args"]` genau `beispiel["ergebnis"]` zurückgibt – auf dem Beispielstand
aus `seed_example_data()` – und dass das Beispiel zu den Schemata passt.

`call_tool()` antwortet immer mit `status`:

| Fall | Antwort |
| --- | --- |
| Pflichtangabe fehlt | `rueckfrage` mit Feldname und Frage |
| Eingabe verstößt gegen `schema_ein` (Typ, Wertliste, unbekanntes Feld) | `fehler` „ungueltig“ mit Feldname (`schema_violation()`) |
| Der Service lehnt ab | `fehler` „ungueltig“ mit seiner Meldung |
| Werkzeug unbekannt | `fehler` „unbekannt“ |

Eine freiwillige Angabe mit dem Wert `null` gilt als nicht gemacht; innerhalb von `felder` leert
`null` bei `start`, `dauer_tage` und `ende` das Feld.

## Entwürfe

Ein Änderungsentwurf merkt sich nur die verlangten Änderungen; das Enddatum wird erst beim
Bestätigen berechnet. `confirm_draft()` speichert Aktion und Abschluss gemeinsam. Ein Entwurf
lässt sich nur einmal abschließen; schlägt die Aktion fehl, bleibt er offen.

## Abhängigkeiten zu anderen Features

- **Ruft auf (optional, über `service.py`):** `timbertalk.features.customers.service` (`get_customer`,
  `list_customers`), sobald Feature F2 diese Funktionen bereitstellt. Solange F2 noch leer ist,
  arbeitet F3 übergangsweise mit Kundennummer + optionalem Kundennamen.
- **Wird aufgerufen von:**
  - Team B / `bridge.py` (S-03): `get_project()`, `get_customer()`.
  - F2 (Kunden): `list_projects_for_customer()`, `list_customer_projects()`.
  - F4 (Stunden), F5 (Material/Preise), F9 (Rechnung), F12 (Planung): `get_project()`, `list_projects()`.
  - F7 (Entwürfe/Bestätigung): `confirm_draft()`, `reject_draft()`.

## Begriffe

| Begriff | Im Code |
| --- | --- |
| Projekt | `Project` (Tabelle `projects_project`), `ProjectInfo` (Antwort) |
| Baustelle | `site_address` in der Tabelle, `baustelle` in `ProjectInfo` (nach S-03) |
| Projektstatus | `PROJECT_STATUSES` (`angefragt`, `geplant`, `in_arbeit`, `abgeschlossen`, `abgerechnet`) |
| Archivierung | `archived` (Flag statt Löschen) |
| Entwurf | `ProjectDraft` (Tabelle `projects_draft`) mit `confirm_draft()` und `reject_draft()` |
| Werkzeug | `Tool` in `tools.py` nach S-09 / S-12 |
