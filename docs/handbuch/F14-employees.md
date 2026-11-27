# F14 – Zeitkonto und Personal: Stundenkonto und Urlaub (Handbuch-Kapitel)

> **Steckbrief:** `docs/features/F14-employees.md` · **Pate:** <offen> · **Stand:** 2026-11-27

## Dateien

| Datei | Wofür |
| --- | --- |
| `backend/timbertalk/features/employees/models.py` | Tabellen `EmployeeContract`, `VacationCarryover`; Eingaben `ContractIn`, `CarryoverIn`; Antworten `HoursAccount`, `VacationAccount`, `VacationPreview`, `EmployeeSummary`. |
| `backend/timbertalk/features/employees/service.py` | Rechnen: `summary()`, `overview()`, `visible_summary()`; Pflegen: `save_contract()`, `set_carryover()`. |
| `backend/timbertalk/features/employees/api.py` | Endpunkte unter `/api/employees`. |
| `backend/timbertalk/features/employees/test_employees.py` | Stundenkonto (Urlaub und Schule zählen als erfüllt, vor dem Eintritt nichts), Urlaubskonto mit Rest, Antrag und Feiertag, falsche Angaben, Rechte. |
| `frontend/features/timeaccount/timeaccount.js` | Reiter „Zeitkonto“: die eigenen Konten (`GET /api/employees/me`), für alle. |
| `frontend/features/timeaccount/absence.js` | `requestDialog()`: Fenster „Urlaub beantragen“ (geöffnet vom Knopf in der Karte „Urlaub“) mit Live-Anzeige des Resturlaubs über `GET /api/employees/me/vacation-preview`; gespeichert über `POST /api/planning/requests` (F8). `requestList()`: „Meine Urlaubsanträge“ mit „Zurückziehen“. Nur mit `calendar.request_absence` und ohne `calendar.approve_absence`. Danach lädt das Zeitkonto Karten und Liste neu. |
| `frontend/features/employees/employees.js` | (Wird es eng, fallen zuerst „Std./Woche“ und „Soll“, dann „Gebucht“ und „Krank“ weg – `data-priority`.) Reiter „Personal“ (nur mit `employees.view_all` oder `employees.manage`): Übersicht aller, Klick öffnet eine Person; mit `employees.manage` das Formular „Vereinbarung“. |
| `frontend/features/employees/cards.js` | Gemeinsame Bausteine beider Reiter (`vacationCard(data, action)`: ein Knopf neben der großen Zahl, im Zeitkonto „Urlaub beantragen“): `cards()`, `hoursCard()`, `vacationCard()`, `yearSwitcher()`, Zahlen auf Deutsch. |

Geändert: `accounts/permissions.py` (Rechte `employees.view_all` und `employees.manage`,
Voreinstellung Chef und Verwaltung; der Meister hat sie nicht), `shared/session.js` (`can()` nimmt
auch eine Liste), `hours/service.py` (`minutes_per_day()`), `planning/service.py` (`absence_days()`),
`demo.py` (Vereinbarungen ab diesem Montag, Rest aus dem Vorjahr für Max und Tom),
`frontend/reiter.js` (eine Zeile), `frontend/style.css` (Klassen `employees-…`).

## Endpunkte

| Methode und Adresse | Recht | Service-Funktion | Was sie tut |
| --- | --- | --- | --- |
| `GET /api/employees/me?year=` | angemeldet | `summary()` | Eigene Konten; ohne `year` das laufende Jahr. |
| `GET /api/employees/me/vacation-preview?start=&end=` | angemeldet | `vacation_preview()` | Arbeitstage des Zeitraums, davon im Folgejahr, Resturlaub vorher und nachher – für die Live-Anzeige beim Beantragen. |
| `GET /api/employees/overview?year=` | `employees.view_all` oder `employees.manage` | `overview()` | Konten aller aktiven Personen außer Admin-Konten. |
| `GET /api/employees/{id}?year=` | angemeldet | `visible_summary()` | Konten einer Person; fremde nur mit `employees.view_all` oder `employees.manage`, sonst 404. |
| `PUT /api/employees/{id}/contract` | `employees.manage` | `save_contract()` | Wochenstunden, Urlaubstage, Eintritt speichern. |
| `PUT /api/employees/{id}/carryover/{jahr}` | `employees.manage` | `set_carryover()` | Rest aus dem Vorjahr für dieses Jahr eintragen. |

## Tabellen

| Tabelle | Spalten | Verweist auf |
| --- | --- | --- |
| `employees_contract` | `account_id` (Schlüssel), `weekly_minutes` (Standard 2400 = 40 h), `vacation_days` (Standard 30), `start_date` | Konto aus F10 (ohne Fremdschlüssel) |
| `employees_carryover` | `account_id` + `year` (Schlüssel), `days` | Konto aus F10 |

Fehlt eine Zeile in `employees_contract`, gelten die Vorgaben. Stunden stehen wie in F4 als ganze
Minuten in der Datenbank.

## So wird gerechnet

**Stundenkonto** (`_hours_account()`):

1. Zeitraum: vom 1. Januar oder vom Eintritt (das Spätere) bis heute oder bis 31. Dezember.
2. `planning.absence_days()` liefert die Tage mit Urlaub, Krankheit oder Berufsschule.
3. Soll-Tage = `holidays.service.workdays()` (F15) im Zeitraum ohne diese Abwesenheiten. Soll = Soll-Tage × Wochenminuten / 5.
4. Gebucht = Summe aus `hours.minutes_per_day()` im Zeitraum. Stundenkonto = gebucht − Soll.

**Urlaubskonto** (`_vacation_account()`):

1. Genehmigter Urlaub = Tage mit Abwesenheit „vacation“ im ganzen Jahr, die Arbeitstage sind;
   davon „genommen“ bis heute, „kommt noch“ danach.
2. Beantragt = offene Anträge (`planning.list_requests()`), in Arbeitstagen.
3. Übrig = Anspruch + Rest Vorjahr − genehmigt − beantragt. Krankheitstage = Arbeitstage mit
   „sick“ bis heute.

## Weg einer typischen Anfrage

Der Chef öffnet „Personal“ (den Reiter blendet `app.js` nur ein, wenn
`can(["employees.view_all", "employees.manage"])`); `employees.js` fragt
`GET /api/employees/overview?year=2026`. Die API holt mit `can()` beide Rechte, `may_see_all()`
in `service.py` entscheidet („pflegen“ schließt „sehen“ ein),
`overview()` holt die Personen aus `accounts.list_people()` (ohne Admin-Konten) und rechnet je
Person `summary()`. Die Tabelle zeigt Stunden mit Vorzeichen („− 14,50 h“), ein Klick auf den
Namen holt `GET /api/employees/{id}`.

## Abhängigkeiten zu anderen Features

- F10 `accounts`: `service.list_people()`, `service.get_account()`, `permissions.ADMIN_ROLE`,
  `deps.require()`, `deps.can()`, `deps.current_account`.
- F4 `hours`: `service.minutes_per_day()`, `to_hours()`, `to_minutes()`.
- F8 `planning`: `service.absence_days()`, `service.list_requests()`.
- F15 `holidays`: `service.workdays()` und `service.current_state()` (Name des Bundeslands für
  den Hinweis in der Oberfläche, Feld `holiday_region`).

## Begriffe

| Fachbegriff | Im Code |
| --- | --- |
| Stundenkonto (Plus/Minus) | `HoursAccount.balance_hours` |
| Soll | `HoursAccount.target_hours` |
| Vereinbarung (Wochenstunden, Urlaubsanspruch, Eintritt) | `EmployeeContract` |
| Rest aus dem Vorjahr | `VacationCarryover` |
| Arbeitstag | `holidays.service.workdays()` (F15) |
