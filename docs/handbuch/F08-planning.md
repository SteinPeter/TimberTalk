# F8 – Kalender je Mitarbeiter (Handbuch-Kapitel)

> **Steckbrief:** `docs/features/F08-planning.md` · **Pate:** offen · **Stand:** 2026-11-26

## Dateien

| Datei | Wofür |
| --- | --- |
| `backend/timbertalk/features/planning/models.py` | Die Arten von Terminen (`KINDS`, `ABSENCE_KINDS`), die Tabellen `CalendarEntry` und `CalendarAssignment` sowie die Antwort- und Eingabeklassen. |
| `backend/timbertalk/features/planning/service.py` | Die Logik: prüfen, eintragen, ändern, löschen, für einen Zeitraum lesen, Überschneidungen finden. |
| `backend/timbertalk/features/planning/api.py` | Die Endpunkte unter `/api/planning` mit den Rechten aus F10. |
| `backend/timbertalk/features/planning/test_planning.py` | Tests für Service und Endpunkte. |
| `frontend/features/planning/planning.js` | Der Reiter „Kalender“: Plantafel, persönlicher Kalender, Dialog „Termin eintragen“. |

In gemeinsamen Dateien geändert:

| Datei | Änderung |
| --- | --- |
| `backend/timbertalk/features/accounts/permissions.py` | Rechte `calendar.view_all` und `calendar.dispatch` mit Voreinstellung. |
| `backend/timbertalk/features/accounts/service.py`, `models.py` | Neue Funktion `list_people()` mit der Antwortklasse `Person` (nur Nummer und Name – die Rolle sieht nur der Admin). |
| `frontend/style.css` | Ein Block am Ende mit Klassen `planning-…`. Keine neuen Farben. |

## Endpunkte

| Methode und Adresse | Recht | Service-Funktion | Was sie tut |
| --- | --- | --- | --- |
| `GET /api/planning/kinds` | angemeldet | `kinds()` | Arten von Terminen (Baustelle, Werkstatt, Termin, Urlaub, Krank, Berufsschule). |
| `GET /api/planning/people` | angemeldet | `visible_people()` | Personen, deren Kalender man sehen darf: alle oder nur sich selbst. |
| `GET /api/planning/entries?start=&end=&account_id=` | angemeldet | `list_entries()` | Termine im Zeitraum (höchstens 62 Tage); mit `account_id` nur die dieser Person. Ohne `calendar.view_all` immer nur die eigenen. |
| `POST /api/planning/entries` | `calendar.dispatch` | `create_entry()` | Termin eintragen; Antwort mit `warnings`. |
| `PUT /api/planning/entries/{id}` | `calendar.dispatch` | `update_entry()` | Termin ändern; Antwort mit `warnings`. |
| `DELETE /api/planning/entries/{id}` | `calendar.dispatch` | `delete_entry()` | Termin mit allen Einplanungen löschen. |

Fehler: `ValueError` → 422, `LookupError` → 404, jeweils mit deutschem Text (`_run()` in `api.py`).

## Tabellen

| Tabelle | Spalten (wichtigste) | Verweist auf |
| --- | --- | --- |
| `planning_entry` | `title`, `kind`, `start_date`, `end_date` (beide eingeschlossen), `start_time`, `end_time` (beide leer = ganzer Tag), `location`, `note`, `created_by` | – |
| `planning_assignment` | `entry_id`, `account_id` (zusammen der Schlüssel) | `planning_entry`; `account_id` ist ein Konto aus F10 |

`account_id` hat bewusst keinen Fremdschlüssel auf `accounts_account`: Tabellen anderer Features
werden nicht direkt benutzt. Namen holt der Service über `accounts.service.list_people()`.

## Wie die Prüfung auf Überschneidungen funktioniert

`_warnings()` sucht alle Termine, in denen eine der eingeplanten Personen steckt und die sich mit
dem Zeitraum des neuen Termins überschneiden (`start_date <= neues Ende` und
`end_date >= neuer Anfang`). `_overlaps()` lässt eine Ausnahme zu: Liegen beide Termine an
**demselben einzelnen Tag** und haben beide Uhrzeiten, zählen sie nur, wenn sich die Zeiten
treffen. Je Treffer entsteht ein Satz; bei Urlaub, krank und Schule heißt es „abwesend“. Beim
Ändern zählt der Termin selbst nicht mit (`except_id`). Gespeichert wird immer – die Hinweise
gehen in der Antwort als `warnings` zurück und stehen in der Oberfläche über der Plantafel.

## Weg einer typischen Anfrage

Der Chef klickt in der Zeile von Max beim Montag auf „+“:

1. `planning.js` öffnet den `<dialog>` mit Max und dem Montag vorausgefüllt.
2. „Speichern“ schickt `sendJson("POST", "/api/planning/entries", {...})`.
3. `require_login` (aus `main.py`) und `require("calendar.dispatch")` prüfen Anmeldung und Recht.
4. `service.create_entry()` prüft die Angaben in `_clean()` (Titel, Art, Zeitraum, Uhrzeiten,
   Personen aktiv?), sammelt die Hinweise, speichert `planning_entry` und je Person eine
   `planning_assignment`.
5. Die Antwort `{entry, warnings}` geht zurück; `planning.js` zeigt „Gespeichert …“ mit den
   Hinweisen und lädt die Woche neu (`GET /api/planning/entries?start=…&end=…`).

## Oberfläche

- **Datum ohne Zeitzonen-Ärger:** `planning.js` rechnet nur mit Text `JJJJ-MM-TT` und erzeugt
  Datumsobjekte immer mittags (`parseDate()`), damit die Sommerzeit keinen Tag verschiebt.
- **Ansicht:** Die Auswahl oben wechselt zwischen „Plantafel – alle“ und einer Person. Sie wird im
  Browser gemerkt (`timbertalk.planning.view`). Wer planen darf, beginnt mit der Plantafel, alle
  anderen mit dem eigenen Kalender. Ein Klick auf einen Namen in der Plantafel öffnet dessen Kalender.
- **Barrierefreiheit:** Jedes „+“ hat einen vorlesbaren Namen („Termin für Max Berger am Mo 30.11.
  eintragen“), der heutige Tag hat `aria-current="date"`, Abwesenheiten sind gestrichelt **und**
  tragen ihren Namen (nicht nur Farbe).
- Gestaltung nach `apple-design`: `modality.md` (kurze Aufgabe, Titel nennt die Aufgabe, klarer
  Weg hinaus), `sheets.md` (Speichern immer mit Abbrechen), `pickers.md` (Uhrzeit in
  15-Minuten-Schritten), `lists-and-tables.md` (kurze Spaltenköpfe).

## Abhängigkeiten zu anderen Features

- F10 `accounts`: `service.list_people()` für Namen und gültige Personen; `deps.current_account`,
  `deps.can()` und `deps.require()` für Rechte.

## Begriffe

| Begriff | Im Code |
| --- | --- |
| Termin, Einsatz | `CalendarEntry` (`planning_entry`) |
| Einplanung (Person bei einem Termin) | `CalendarAssignment` (`planning_assignment`) |
| Art des Termins | `kind`: `job`, `workshop`, `appointment`, `vacation`, `sick`, `school` |
| Abwesenheit | `ABSENCE_KINDS` (Urlaub, krank, Berufsschule) |
| Plantafel | Ansicht `board` in `planning.js` |
| Hinweis auf Überschneidung | `warnings` |
