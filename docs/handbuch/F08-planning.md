# F8 – Kalender je Mitarbeiter (Handbuch-Kapitel)

> **Steckbrief:** `docs/features/F08-planning.md` · **Pate:** offen · **Stand:** 2026-11-26

## Dateien

| Datei | Wofür |
| --- | --- |
| `backend/timbertalk/features/planning/models.py` | Die Arten von Terminen (`KINDS`, `ABSENCE_KINDS`), Fahrzeug-Arten (`RESOURCE_CATEGORIES`), Antrags-Status (`REQUEST_STATUS`), die Tabellen und die Antwort- und Eingabeklassen. |
| `backend/timbertalk/features/planning/service.py` | Die Logik: Termine prüfen, eintragen, ändern, löschen, lesen, Überschneidungen finden, Mitteilungen schicken; Fahrzeuge und Maschinen; Urlaubsanträge; Kalender-Abo (iCalendar). |
| `backend/timbertalk/features/planning/api.py` | Die Endpunkte unter `/api/planning` mit den Rechten aus F10. |
| `backend/timbertalk/features/planning/test_planning.py` | Tests für Service und Endpunkte. |
| `frontend/features/planning/planning.js` | Der Reiter „Kalender“: Plantafel mit Personen und Fahrzeugen, Ziehen mit „Rückgängig“, persönlicher Kalender, Dialog „Termin eintragen“. |
| `frontend/features/planning/dialog.js` | `makeDialog(titel)`: ein Fenster mit Überschrift, Inhalt und „Schließen“. |
| `frontend/features/planning/requests.js` | `openOwnRequests()`: Fenster „Urlaub beantragen“ mit den eigenen Anträgen (über „Mehr ▾“); `card()` und `range()` für die Anzeige eines Antrags. |
| `frontend/features/planning/widgets/absence-requests.js`, `my-week.js` | Dashboard-Widgets (F12): offene Urlaubsanträge entscheiden; eigene nächste Termine. |
| `frontend/features/planning/ical.js` | `openIcal()`: Fenster „Kalender aufs Handy holen“ (über „Mehr ▾“): Abo-Link erzeugen, kopieren, ungültig machen. |
| `frontend/features/settings/sections/planning-resources.js` | Abschnitt „Fahrzeuge und Maschinen“ in den Einstellungen (Recht `calendar.dispatch`). |
| `backend/timbertalk/features/notifications/` | Eigenes kleines Feature „Mitteilungen“: Tabelle `notifications_message`, `notify()`, `list_notifications()`, `unread_count()`, `mark_all_read()`; Endpunkte `GET /api/notifications`, `GET /api/notifications/unread-count`, `POST /api/notifications/read-all` (jeweils nur die eigenen). |
| `frontend/shared/notifications.js` | Knopf „Mitteilungen“ oben rechts mit Zahl der ungelesenen; holt die Zahl jede Minute neu. |

In gemeinsamen Dateien geändert:

| Datei | Änderung |
| --- | --- |
| `backend/timbertalk/features/accounts/permissions.py` | Rechte `calendar.view_all`, `calendar.dispatch`, `calendar.request_absence`, `calendar.approve_absence` mit Voreinstellung. |
| `backend/timbertalk/features/accounts/service.py`, `models.py` | Neue Funktionen `list_people()` (Antwortklasse `Person`: nur Nummer und Name – die Rolle sieht nur der Admin) und `people_with_permission()` (an wen ein Urlaubsantrag geht). |
| `backend/timbertalk/features/accounts/deps.py` | `PUBLIC_PREFIXES`: Der Abo-Link `/api/planning/ical/…` geht ohne Anmeldung. |
| `frontend/app.js` | Hängt den Knopf „Mitteilungen“ vor den Namen in der Leiste. |
| `frontend/features/settings/sections.js` | Abschnitt `planning-resources` eingetragen. |
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
| `GET /api/planning/resources?include_inactive=` | angemeldet | `list_resources()` | Fahrzeuge und Maschinen (ausgemusterte nur auf Wunsch); `rate_per_km` nur mit `finance.view`. |
| `PUT /api/planning/resources/{id}/rate` | `finance.edit` | `set_vehicle_rate()` | Kilometersatz eines Fahrzeugs (0 bis 10 €, leer = keiner). |
| `POST /api/planning/resources` | `calendar.dispatch` | `create_resource()` | Fahrzeug oder Maschine anlegen. |
| `PUT /api/planning/resources/{id}` | `calendar.dispatch` | `update_resource()` | Umbenennen, Art ändern, ausmustern. |
| `GET /api/planning/requests` | angemeldet | `list_requests()` | Mit `calendar.approve_absence` alle Anträge, sonst die eigenen; offene zuerst, mit `conflicts`. |
| `POST /api/planning/requests` | `calendar.request_absence` | `request_absence()` | Urlaub beantragen; Genehmigende bekommen eine Mitteilung. |
| `POST /api/planning/requests/{id}/approve` | `calendar.approve_absence` | `decide_request()` | Genehmigen: Termin „Urlaub“ entsteht; Antwort mit `warnings`. |
| `POST /api/planning/requests/{id}/reject` | `calendar.approve_absence` | `decide_request()` | Ablehnen, wahlweise mit Grund. |
| `DELETE /api/planning/requests/{id}` | angemeldet | `withdraw_request()` | Eigenen offenen Antrag zurückziehen. |
| `GET /api/planning/ical-link` | angemeldet | `ical_link()` | Gibt es einen Abo-Link? (`active`) |
| `POST /api/planning/ical-link` | angemeldet | `new_ical_link()` | Neuen Abo-Link erzeugen; `path` steht nur in dieser Antwort. |
| `DELETE /api/planning/ical-link` | angemeldet | `delete_ical_link()` | Abo-Link ungültig machen. |
| `GET /api/planning/ical/{schlüssel}.ics` | **ohne Anmeldung** | `ical_feed()` | Der Kalender der Person als iCalendar (60 Tage zurück, 365 voraus). |

Fehler: `ValueError` → 422, `LookupError` → 404, jeweils mit deutschem Text (`_run()` in `api.py`).

## Tabellen

| Tabelle | Spalten (wichtigste) | Verweist auf |
| --- | --- | --- |
| `planning_entry` | `title`, `kind`, `start_date`, `end_date` (beide eingeschlossen), `start_time`, `end_time` (beide leer = ganzer Tag), `location`, `note`, `project_id` (freiwillig, für F4), `created_by` | – |
| `planning_assignment` | `entry_id`, `account_id` (zusammen der Schlüssel) | `planning_entry`; `account_id` ist ein Konto aus F10 |
| `planning_resource` | `name`, `category` (`vehicle`/`machine`), `active`, `rate_per_km` (Euro je km, nur Fahrzeuge, als Text-Decimal) | – |
| `planning_resource_assignment` | `entry_id`, `resource_id` (zusammen der Schlüssel) | `planning_entry`, `planning_resource` |
| `planning_absence_request` | `account_id`, `start_date`, `end_date`, `note`, `status` (`pending`/`approved`/`rejected`), `decided_by`, `decided_at`, `decision_note`, `entry_id` | `entry_id` → der Termin „Urlaub“ |
| `planning_ical_token` | `account_id` (Schlüssel), `token_hash` | – |

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

## Mitteilungen, Ziehen, Urlaub, Abo

- **Mitteilungen:** `create_entry()`, `update_entry()` und `delete_entry()` schicken nach dem
  Speichern über `notifications.service.notify()` je eine Zeile an die Betroffenen – außer an die
  Person, die plant (`created_by`/`acting_id`). Den Text baut `describe()`, z. B.
  „Carport Berger, Mo 30.11.–Mi 02.12., 07:00–16:00 Uhr, Potsdam“. Beim Ändern bekommen neue
  Personen „Neu eingeplant“, entfernte „Ausgeplant“, verbliebene nur dann „Geändert“, wenn sich
  `describe()` geändert hat.
- **Fahrzeuge und Maschinen** werden wie Personen behandelt: eigene Zuordnungstabelle, eigene
  Hinweise auf Überschneidungen („… ist am … schon verplant“), eigene Zeilen auf der Plantafel.
  Ein Termin braucht mindestens eine Person **oder** ein Fahrzeug.
- **Ziehen** (nur `planning.js`, kein eigener Endpunkt): Beim Ablegen berechnet `moveEntry()` den
  Abstand in Tagen, verschiebt ersten und letzten Tag, ersetzt bei einem Zeilenwechsel die alte
  Person (das alte Fahrzeug) durch die neue und schickt alles mit `PUT /entries/{id}`. „Rückgängig“
  schickt den alten Stand mit demselben Endpunkt zurück.
- **Urlaubsanträge:** `request_absence()` speichert den Antrag und benachrichtigt alle Konten mit
  `calendar.approve_absence` (`accounts.service.people_with_permission()`, voreingestellt der Chef)
  mit dem Link `#start` – ein Klick auf die Mitteilung öffnet das Dashboard. `list_requests()`
  rechnet für offene Anträge mit `_warnings()` aus, was in der Zeit schon eingeplant ist.
  `decide_request()` legt beim Genehmigen mit `create_entry(..., notify=False)` den Termin
  „Urlaub“ an und schickt stattdessen „Urlaub genehmigt: …“.
- **Kilometersatz für F5:** `vehicle_rate()` liefert Nummer, Name und Satz des Fahrzeugs für eine
  Fahrt. Ohne Fahrzeug nimmt es das einzige Fahrzeug mit Satz; gibt es mehrere oder keines, kommt
  ein Fehler mit deutschem Text. `vehicles_with_rate()` nutzt das KI-Werkzeug `fahrt_buchen` zum
  Nachfragen, `resource_name()` die Buchungsliste („Fahrt (Transporter)“).
- **Oberfläche:** Was man selten braucht, öffnet ein Fenster (`dialog.js`) statt dauerhaft unter
  der Woche zu stehen. Notizen sind mehrzeilige Felder, die mit dem Text wachsen.
- **Kalender-Abo:** `new_ical_link()` erzeugt 32 Byte Zufall, speichert nur den SHA-256-Hash und
  gibt die Adresse einmal zurück. `ical_feed()` sucht den Hash, liest die Termine der Person und
  schreibt iCalendar: ganztägige Termine mit `DTSTART;VALUE=DATE` (Ende = Tag nach dem letzten
  Tag), Termine mit Uhrzeit als Ortszeit mit `RRULE:FREQ=DAILY;COUNT=…` über mehrere Tage. Texte
  werden mit `_ical_text()` maskiert, Zeilen mit `_fold()` nach 75 Byte umbrochen.

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

- F10 `accounts`: `service.list_people()` für Namen und gültige Personen,
  `service.people_with_permission()` für Urlaubsanträge; `deps.current_account`, `deps.can()` und
  `deps.require()` für Rechte.
- `notifications`: `service.notify()`.

## Begriffe

| Begriff | Im Code |
| --- | --- |
| Termin, Einsatz | `CalendarEntry` (`planning_entry`) |
| Einplanung (Person bei einem Termin) | `CalendarAssignment` (`planning_assignment`) |
| Art des Termins | `kind`: `job`, `workshop`, `appointment`, `vacation`, `sick`, `school` |
| Abwesenheit | `ABSENCE_KINDS` (Urlaub, krank, Berufsschule) |
| Plantafel | Ansicht `board` in `planning.js` |
| Hinweis auf Überschneidung | `warnings` |
