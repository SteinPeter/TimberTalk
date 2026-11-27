# F14 – Zeitkonto und Personal: Stundenkonto und Urlaub

## Ziel

Jede Person sieht ihr Stundenkonto und ihre Urlaubstage; der Chef sieht beides für alle
Mitarbeitenden auf einen Blick.

## Was der Zimmerer danach kann

Im neuen Reiter „Zeitkonto“ sieht jede Person ihre eigenen Konten: Max sieht groß
„− 13,00 h im Minus“ und „28 Tage noch übrig“, darunter, woraus sich das zusammensetzt: gebucht,
Soll, Anspruch, Rest aus dem Vorjahr, genommen, beantragt, Krankheitstage. Chef und Verwaltung
haben zusätzlich den Reiter „Personal“ (anderen Rollen oder einzelnen Konten schaltet der Admin
ihn unter „Rollen und Rechte“ frei – nur zum Sehen oder zum Sehen und Pflegen): eine Tabelle aller Mitarbeitenden mit
Wochenstunden, gebuchten Stunden, Soll, Stundenkonto, Resturlaub und Krankheitstagen; ein Klick auf
einen Namen öffnet dessen Konten. Dort trägt er Wochenstunden, Urlaubsanspruch, Eintritt und den
Rest aus dem Vorjahr ein.

## Abnahme

Im Meeting wird genau das vorgeführt:

1. **Urlaub beantragen** geht im Reiter „Zeitkonto“, nicht mehr im Kalender: In der Karte „Urlaub“
   steht neben „28 Tage noch übrig“ der Knopf „Urlaub beantragen“. Er öffnet ein Fenster; während
   Max den ersten und letzten Tag wählt, zählt die große Zahl live herunter – 21.12.2026 bis
   5.1.2027: „20 Tage“, darunter „vorher 28 Tage · dieser Antrag: 10 Arbeitstage · davon 2 im Jahr
   2027“ (Wochenenden und Feiertage zählen nicht). „Beantragen“ – der Antrag steht unter
   „Meine Urlaubsanträge“ als „Offen“, die Karte zeigt „Beantragt, offen“. „Zurückziehen“ nimmt
   ihn wieder heraus. Der Chef bekommt wie bisher eine Mitteilung und entscheidet auf dem Dashboard.
2. **Eigene Konten:** Max (Geselle) hat nur den Reiter „Zeitkonto“ mit seinen eigenen Konten – kein
   Reiter „Personal“, kein Formular, keine anderen Personen. `GET /api/employees/{andere Person}` antwortet ihm mit 404.
3. **Stundenkonto:** Soll sind die Wochenstunden, gleich verteilt auf Montag bis Freitag, vom
   1. Januar (oder vom Eintritt) bis heute. Feiertage im Bundesland des Betriebs (F15, erkannt an
   der Postleitzahl der Firmenadresse) sowie Urlaub, Krankheit und Berufsschule aus dem Kalender
   zählen als erfüllt.
   Beispiel im Test: Eintritt Mo 2.11.2026, Urlaub am Do, gebucht 9 + 8 + 8 + 8 Stunden → Soll
   32 h, gebucht 33 h, „+ 1,00 h“.
4. **Urlaub:** Anspruch + Rest aus dem Vorjahr − genehmigter Urlaub − offene Anträge, in
   Arbeitstagen. Beispiel im Test: 30 + 3 − 9 − 3 = 21; der 25.12. zählt nicht, das Wochenende nicht.
5. **Reiter „Personal“** (Recht „Personal: Stunden und Urlaub aller sehen“, `employees.view_all`,
   Voreinstellung Chef und Verwaltung): Tabelle aller aktiven Mitarbeitenden ohne das Admin-Konto;
   ‹ und › wechseln das Jahr. Chef und Verwaltung haben beide Reiter: „Zeitkonto“ für sich selbst,
   „Personal“ für alle.
6. **Pflegen** (Recht „Personal: … sehen und Vereinbarungen pflegen“, `employees.manage`,
   Voreinstellung Chef und Verwaltung): Wochenstunden 38,5 speichern – Soll und Stundenkonto
   ändern sich sofort. Rest aus dem Vorjahr gilt nur für das gewählte Jahr. Unsinnige Werte
   (400 Stunden) werden mit deutscher Meldung abgelehnt.
7. **Meister freischalten:** Sabine (Meisterin) hat zunächst nur „Zeitkonto“. Der Admin setzt in
   „Rollen und Rechte“ für Meister das Häkchen „sehen“ – nach dem Neuladen hat sie „Personal“ ohne
   Formular. Mit dem Häkchen „sehen und pflegen“ (allein genügt) kommt das Formular dazu.
8. `uv run pytest`, `uv run ruff check .` und `uv run ruff format --check .` sind grün.

## Nicht dabei

- Halbe Urlaubstage, Urlaubsanspruch anteilig im Eintrittsjahr berechnen, Resturlaub automatisch
  aus dem Vorjahr übernehmen (der Chef trägt ihn ein).
- Unterschiedliche Arbeitstage je Person (z. B. nur Mo–Do).
- Überstunden auszahlen oder abbauen, Stundenkonto zum Stichtag abschließen.
- Fahrzeuge und Maschinen ausleihen – kommt später.

## Neues Konzept fürs Team

- **Ein Reiter für eines von mehreren Rechten:** `permission` darf eine Liste sein;
  `can(["a", "b"])` in `shared/session.js` ist wahr, wenn das Konto eines davon hat. Gilt genauso
  für Abschnitte und Widgets.

- **Arbeitstage** kommen aus F15 (`holidays.service.workdays()`): Montag bis Freitag ohne die
  Feiertage im Bundesland des Betriebs.
- **Ein Feature, zwei Reiter:** „Zeitkonto“ (`timeaccount/`) für alle und „Personal“
  (`employees/`) nur mit Recht – `export const permission` blendet einen Reiter aus. Die Karten
  stehen einmal in `employees/cards.js` und werden von beiden benutzt.

## Reiter

- `frontend/features/timeaccount/timeaccount.js` („Zeitkonto“) – jede Person.
- `frontend/features/employees/employees.js` („Personal“,
  `permission = ["employees.view_all", "employees.manage"]` – eines genügt).

Beide eingetragen in `frontend/reiter.js`; gemeinsame Karten in `frontend/features/employees/cards.js`.

## Pate

<offen>
