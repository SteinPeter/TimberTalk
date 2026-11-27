# F3 – Projekte

## Ziel

Jeder Auftrag hat ein eigenes Projekt mit Kunde, Baustelle, Zeitraum und Status – über die
Weboberfläche, als Service für Team B (S-03) und als KI-Werkzeuge nach S-09 / S-12.
Lastenheft LA-03, LA-04 und LS-03.

## Was der Zimmerer danach kann

Im Reiter „Projekte“ legt er neue Projekte zu einem Kunden mit Baustelle, Zeitraum, Notiz und
Status an – ohne Kunde lässt sich ein Projekt nicht speichern. Er sucht und filtert nach Projekt,
Kunde, Baustelle, Status oder Archiv, ändert Angaben oder den Status direkt in der Liste,
archiviert abgeschlossene Aufträge und kann alle Projekte gruppiert nach Kunde ansehen. Beginn,
Dauer und Ende passen sich beim Ausfüllen gegenseitig an; ein widersprüchlicher Zeitraum wird
nicht gespeichert. Die KI kann dieselben Aktionen über fünf Werkzeuge ausführen; schreibende Werkzeuge legen zuerst einen
Entwurf zur Bestätigung an.

## Abnahme

Im Meeting wird genau das vorgeführt:

1. **Projekte verwalten (LA-03):** Ein Projekt zu einem Kunden mit Baustelle und Status lässt sich
   über die Oberfläche anlegen, suchen, ändern und archivieren (sowie wiederherstellen). Ohne Kunde
   ist der Speichern-Knopf deaktiviert und auch die API lehnt das Speichern ab.
2. **Status und Kundenübersicht (LA-04):** Alle fünf Statuswerte (`angefragt`, `geplant`,
   `in_arbeit`, `abgeschlossen`, `abgerechnet`) lassen sich über die Oberfläche und per Werkzeug
   setzen und werden in der Projektliste und in der Ansicht „Nach Kunde“ richtig angezeigt.
3. **Service für Team B (S-03):** `get_project(session, project_id)` und
   `get_customer(session, customer_id)` liefern die dokumentierten Felder (und `None` bei
   unbekannter ID), geprüft durch Tests.
4. **Werkzeuge (S-09, S-12):** `projekt_suchen`, `projekt_anlegen`, `projekt_aendern`,
   `projekt_status_setzen` und `projekt_archivieren` sind mit deutschem Namen, Beschreibung,
   JSON-Schema und Beispiel registriert. Ein automatischer Test ruft jedes Werkzeug mit seinem
   Beispiel auf und erhält das dokumentierte Ergebnis.
5. **Zentrale Datenbank (LS-03):** Alle Projekte liegen in derselben lokalen SQLite-Datenbank.
   Ein Eintrag von einem anderen Gerät erscheint, sobald man auf den Reiter „Projekte“ oder in das
   Browser-Fenster zurückkehrt – ohne die Seite neu zu laden.
6. `uv run pytest`, `uv run ruff check .` und `uv run ruff format --check .` sind grün.

## Nicht dabei

- **Kunden anlegen oder pflegen:** Gehört zu F2 (`customers`). Sobald `customers/service.py`
  `get_customer()` und `list_customers()` bereitstellt, nutzt F3 diese automatisch und prüft jede
  Kundennummer gegen F2. Bis dahin ist eine gültige Kundennummer (ab 1) Pflicht.
- **Kundenreiter selbst ändern:** Der Ordner `frontend/features/customers/` gehört zu F2. Für
  „Kundenliste zeigt die Projekte“ stellt F3 die Service-Funktion `list_projects_for_customer()`
  (und `list_customer_projects()`) bereit sowie die Ansicht „Nach Kunde“ im Reiter „Projekte“.
- **Gemeinsamer Werkzeugkatalog (`@werkzeug`) und Bestätigungskarte:** Kommen mit AP-0.5 / F7
  (`drafts`). Bis dahin hat F3 einen eigenen kleinen Katalog `TOOLS` nach S-09 und eine eigene
  Entwurfstabelle `projects_draft` mit `confirm_draft()` und `reject_draft()`.
- **Datenbank-Migrationen (Alembic):** `CLAUDE.md`, das Handbuch und `db.py` kündigen sie „mit
  F3“ an. Im Arbeitspaket AP-1.5 stehen sie nicht, und sie bräuchten eine neue Bibliothek und
  Änderungen an gemeinsamen Dateien (`pyproject.toml`, `db.py`). Das entscheiden die Leads; F3
  legt nur neue Tabellen an, dafür reicht `create_all`.
- **Teile von S-09 und S-10, die in den Kern gehören:** `list_tools()`, die Angaben `quelle` und
  `originaltext` bei `call_tool()`, das Änderungsprotokoll und der Fehler „veraltet“ beim
  Bestätigen kommen mit AP-0.5 / F7.
- **Projektkosten und Gantt-Planung:** Kosten kommen aus F4/F5, die Gantt-Ansicht aus F12. F3
  speichert dafür bereits `start_date`, `duration_days` und `end_date`.

## Neues Konzept fürs Team

- **Archivieren statt Löschen:** Projekte werden über ein Kennzeichen `archived` ausgeblendet,
  nicht aus der Datenbank entfernt – damit spätere Buchungen und Rechnungen ihren Bezug behalten.
- **Übergangs-Kopplung an F2 (`customers/service.py`):** F3 liest Kunden ausschließlich über
  `customers/service.py` (nie aus fremden Tabellen). Solange F2 noch leer ist, greift ein kleiner
  Übergangsweg, der automatisch verschwindet, sobald F2 `get_customer()` anbietet.
- **Eigene CSS-Datei im Feature-Ordner:** `frontend/features/projects/projects.css` nutzt nur die
  Farbvariablen aus `style.css`, ohne die gemeinsame Datei `style.css` zu ändern.

## Reiter

`frontend/features/projects/projects.js` (bestehender Reiter `#projects` – keine Änderung an
`frontend/reiter.js` oder `frontend/style.css`).

## Pate

Licheng Ou, Tingyu Li
