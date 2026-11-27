# F15 – Feiertage je Bundesland (Handbuch-Kapitel)

> **Steckbrief:** `docs/features/F15-holidays.md` · **Pate:** <offen> · **Stand:** 2026-11-27

## Dateien

| Datei | Wofür |
| --- | --- |
| `backend/timbertalk/features/holidays/rules.py` | Reine Regeln ohne Datenbank: `STATES`, `easter_sunday()`, `holidays(jahr, land)`, `workdays()`, `postcode_in()`, `state_for_postcode()` mit `LEAD_REGIONS` und `EXCEPTIONS`. |
| `backend/timbertalk/features/holidays/models.py` | Tabelle `HolidaySetting` (von Hand festgelegtes Land); `StateInfo`, `StateIn`, `Holiday`, `StateOption`. |
| `backend/timbertalk/features/holidays/service.py` | `current_state()`, `set_state()`, `list_states()`, `holidays_between()`, `workdays()`. |
| `backend/timbertalk/features/holidays/api.py` | Endpunkte unter `/api/holidays`. |
| `backend/timbertalk/features/holidays/test_holidays.py` | Ostern, Feiertage in acht Ländern, Reformationstag im Norden ab 2018, 21 Postleitzahlen, Land aus Adresse oder von Hand, Arbeitstage je Land, Rechte. |
| `frontend/features/settings/sections/holidays.js` | Abschnitt „Feiertage“: Land und Herkunft, Auswahl „Bundesland festlegen“, Feiertage des Jahres. |

Geändert: `employees/service.py` (Arbeitstage von hier), `planning.js` (zeigt Feiertage),
`settings/sections.js` (eine Zeile), `style.css` (`--holiday`, Klassen `holidays-…`).

## Endpunkte

| Methode und Adresse | Recht | Service-Funktion | Was sie tut |
| --- | --- | --- | --- |
| `GET /api/holidays?start=&end=` | angemeldet | `holidays_between()` | Feiertage im Zeitraum (höchstens zwei Kalenderjahre). |
| `GET /api/holidays/state` | angemeldet | `current_state()` | Land, Name, Herkunft (`address`, `manual`, `none`), Postleitzahl, erkanntes Land. |
| `GET /api/holidays/states` | angemeldet | `list_states()` | Alle 16 Länder für die Auswahl. |
| `PUT /api/holidays/state` | `finance.edit` | `set_state()` | Land festlegen; `null` = wieder aus der Adresse. |

## Tabellen

| Tabelle | Spalten | Verweist auf |
| --- | --- | --- |
| `holidays_setting` | `id` (immer 1), `state` (Kürzel) | – |

## Woher das Bundesland kommt

1. `current_state()` liest die Firmenadresse mit `materials.service.get_company()` (F5).
2. `postcode_in()` sucht darin die erste fünfstellige Zahl, `state_for_postcode()` sucht sie in
   `EXCEPTIONS` (Bereiche an Landesgrenzen) und sonst nach den ersten zwei Ziffern.
3. Gibt es eine Zeile in `holidays_setting`, gilt die (Herkunft `manual`). Sonst das erkannte Land
   (`address`), sonst `None` – dann rechnet `rules.holidays()` nur die bundesweiten Feiertage.

Weil das Land bei jeder Anfrage aus der Adresse gerechnet wird, wirkt eine geänderte Adresse sofort.

## Abhängigkeiten zu anderen Features

- F5 `materials`: `service.get_company()` (Adresse).
- F10 `accounts`: `deps.require()`.
- Benutzt von F14 `employees` (`workdays()`, `current_state()`) und vom Kalender F8 (über
  `GET /api/holidays`).

## Begriffe

| Fachbegriff | Im Code |
| --- | --- |
| Bundesland | `state` (Kürzel wie „BB“), Namen in `rules.STATES` |
| Leitregion (erste zwei Ziffern der PLZ) | `rules.LEAD_REGIONS` |
| Feiertag | `Holiday` |
