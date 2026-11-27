# F4 – Stunden buchen (Handbuch-Kapitel)

> **Steckbrief:** `docs/features/F04-hours.md` · **Pate:** offen · **Stand:** 2026-11-26

## Dateien

| Datei | Wofür |
| --- | --- |
| `backend/timbertalk/features/hours/models.py` | Tabelle `HoursEntry`, Eingaben `HoursIn`, `DayIn`, Antworten `HoursInfo`, `Suggestion`. |
| `backend/timbertalk/features/hours/service.py` | Vorschläge aus dem Kalender, buchen, Tag bestätigen, löschen, lesen; Pausen nach Arbeitszeitgesetz. |
| `backend/timbertalk/features/hours/api.py` | Endpunkte unter `/api/hours`. |
| `backend/timbertalk/features/hours/test_hours.py` | Tests. |
| `frontend/features/bookings/sections/hours.js` | Abschnitt „Stunden“: Tag wählen, Vorschläge bestätigen, von Hand buchen, Woche mit Summe. |

In gemeinsamen Dateien geändert:

| Datei | Änderung |
| --- | --- |
| `backend/timbertalk/features/accounts/permissions.py` | Rechte `hours.book_own`, `hours.view_all`, `hours.manage`. |
| `backend/timbertalk/features/planning/` | Termine haben eine freiwillige `project_id` (Feld „Projektnummer“ im Dialog). |
| `frontend/features/bookings/sections.js`, `frontend/style.css` | Abschnitt `hours` eingetragen (vor „Material und Fahrten“); Klassen `hours-…`. |

## Endpunkte

| Methode und Adresse | Recht | Service-Funktion | Was sie tut |
| --- | --- | --- | --- |
| `GET /api/hours/suggestions?day=` | `hours.book_own` | `suggestions()` | Termine dieser Person an dem Tag (ohne Abwesenheiten) mit vorgeschlagenen Stunden und `booked`. |
| `GET /api/hours?start=&end=&account_id=` | angemeldet | `list_hours()` | Gebuchte Stunden (höchstens 62 Tage); ohne `hours.view_all` nur die eigenen. |
| `POST /api/hours` | `hours.book_own` | `book()` | Stunden buchen; mit `account_id` für andere (nur mit `hours.manage`). |
| `POST /api/hours/confirm-day` | `hours.book_own` | `confirm_day()` | Mehrere Vorschläge auf einmal – alle oder keiner. |
| `DELETE /api/hours/{id}` | angemeldet | `delete_hours()` | Eigene Buchung löschen; fremde nur mit `hours.manage`. |

Fehler: `PermissionError` → 403, `LookupError` → 404, `ValueError` → 422.

## Tabellen

| Tabelle | Spalten (wichtigste) | Verweist auf |
| --- | --- | --- |
| `hours_entry` | `account_id`, `work_date`, `minutes`, `project_id`, `title`, `note`, `calendar_entry_id`, `created_by` | `calendar_entry_id` → Termin in F8 (ohne Fremdschlüssel) |

## Wie der Vorschlag entsteht

1. `suggestions()` holt mit `planning.service.list_entries(session, tag, tag, person, view_all=False)`
   die Termine der Person an dem Tag und lässt Urlaub, krank und Berufsschule weg.
2. Mit Uhrzeit: `working_minutes()` = Ende − Beginn, ab 6 Stunden minus 30 Minuten, ab 9 Stunden
   minus 45 Minuten (Arbeitszeitgesetz §4). Ohne Uhrzeit: 8 Stunden.
3. `booked` ist wahr, wenn es für Person, Tag und Termin schon eine Buchung gibt.
   `_new_entry()` lehnt eine solche zweite Buchung ab.
4. `to_minutes()`/`to_hours()` rechnen zwischen Stunden (`Decimal`, zwei Nachkommastellen) und
   ganzen Minuten.

## Abhängigkeiten zu anderen Features

- F8 `planning`: `service.list_entries()`, `models.ABSENCE_KINDS`.
- Benutzt wird F4 von F14 `employees` über `service.minutes_per_day()` (gebuchte Minuten je Tag
  über einen beliebig langen Zeitraum, für das Stundenkonto) und `to_hours()`/`to_minutes()`.
- F10 `accounts`: `service.list_people()`, `deps.require()`, `deps.can()`, `deps.current_account`.

## Begriffe

| Begriff | Im Code |
| --- | --- |
| Stundenbuchung | `HoursEntry` (`hours_entry`) |
| Vorschlag aus dem Kalender | `Suggestion` |
| Tag bestätigen | `confirm_day()` |
