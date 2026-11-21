# F5 – Material, Fahrten und Preise

## Ziel

Holz, Kleinteile und Fahrten werden je Projekt gebucht; Preise mit Gültigkeitsdatum ergeben die
Projektkosten. Lastenheft LA-19 und LA-11, Schnittstellen S-04, S-05 und S-14.

## Was der Zimmerer danach kann

In den Einstellungen legt er Materialien an, trägt ihre Preise mit dem Datum ein, ab dem sie
gelten, und hinterlegt die Stammdaten der Abrechnung: Firma, Logo, Bank, Stundensätze, Fahrtkosten
je km und Umsatzsteuer. Im Reiter „Buchungen“ wählt er ein Projekt, bucht Material und Fahrten
darauf und sieht sofort die Gesamtkosten und die Liste aller Buchungen. Die KI kann dasselbe über
vier Werkzeuge tun; was sie bucht, ist erst ein Entwurf, den der Zimmerer bestätigt.

## Abnahme

Im Meeting wird genau das vorgeführt:

1. **Materialstamm:** Ein Material wird mit Kategorie und Einheit angelegt und bekommt zwei Preise
   mit verschiedenen Gültigkeitsdaten. Gebucht wird zum Preis, der am Buchungstag gilt.
2. **Stammdaten der Abrechnung (LA-11):** Firma, Adresse, Logo, Bank (Name, IBAN, BIC), Stundensätze,
   Fahrtkosten je km und Umsatzsteuer lassen sich eintragen, speichern und nach dem Neuladen wieder
   sehen.
3. **Buchen über die Oberfläche (LA-19):** Fünf Material- und Fahrtbuchungen auf ein Projekt landen
   mit den richtigen Werten in der Liste, und die Gesamtkosten (netto) stimmen auf den Cent.
4. **Services für Team B:** `list_materials()` (S-04) und `book_material_draft()` (S-05) laufen
   mit Test. Ein Entwurf zählt erst zu den Kosten, wenn er bestätigt ist.
5. **Werkzeuge (S-14, S-09):** `material_suchen`, `material_buchen`, `fahrt_buchen` und
   `projekt_kosten` sind mit Name, deutscher Beschreibung, JSON-Schema und Beispiel registriert.
   Ein automatischer Test ruft jedes Werkzeug mit seinem Beispiel auf und bekommt das
   dokumentierte Ergebnis.
6. `uv run pytest`, `uv run ruff check .` und `uv run ruff format --check .` sind grün.

## Nicht dabei

- **Stundenkosten:** Sie kommen mit dem Feature Stunden (`hours`). Bis dahin sind sie in den Projektkosten 0.
  Die Stundensätze sind hinterlegt, werden aber noch nicht benutzt.
- **Projekte prüfen:** Die Projektnummer ist vorerst nur eine Zahl. Ob es das Projekt gibt, prüft
  F3 (Projekte), sobald dessen `service.py` existiert.
- **Entwürfe bestätigen oder verwerfen:** Die Bestätigungskarte und die Tabelle der Entwürfe gehören
  zu F7. Hier gibt es nur den Status `draft`/`confirmed` und `confirm_draft()`, die F7 aufrufen kann.
- **Rechnung:** Dass die Stammdaten auf einer erzeugten Rechnung erscheinen (Abnahme von LA-11),
  zeigt F9. Hier werden sie hinterlegt.
- **Der gemeinsame Werkzeugkatalog** `@werkzeug` aus S-09 (AP-0.5). Bis er da ist, hat dieses Feature
  einen eigenen kleinen Katalog mit denselben Feldern.
- **Buchungen ändern oder löschen** und der Preisverlauf in der Oberfläche. Die API kennt den
  Preisverlauf (`GET /api/materials/items/{id}/prices`); die Oberfläche zeigt nur den aktuellen Preis.

## Neues Konzept fürs Team

- **Preis mit Gültigkeitsdatum:** Ein Preis gilt ab einem Datum, bis ein neuerer beginnt. Beim
  Buchen wird der Preis des Buchungstags **in der Buchung festgehalten**; spätere Preisänderungen
  ändern alte Buchungen nicht.
- **Decimal in SQLite:** SQLite kennt kein Decimal und würde Zahlen als `float` speichern. Die
  Spalte `DecimalText` speichert sie als Text und liest sie als `Decimal` zurück.
- **Entwurf:** Eine Buchung hat einen Status. `draft` zählt nicht zu den Kosten, `confirmed` schon.
  Mehrere Buchungen eines Entwurfs teilen sich die `draft_id`.
- **Werkzeug:** Eine Aktion, die die KI aufrufen kann, mit Name, Beschreibung, Schema und Beispiel
  (S-09). Fehlt eine Angabe, antwortet sie mit einer Rückfrage statt zu raten.

## Reiter

Zwei bestehende Reiter, in beiden kommt eine eigene Datei dazu:

- `bookings` („Buchungen“): `frontend/features/bookings/materials-booking.js` – Material und Fahrten
  buchen, Gesamtkosten, Buchungsliste.
- `settings` („Einstellungen“): `frontend/features/settings/materials-master.js` (Materialstamm und
  Preise) und `frontend/features/settings/materials-company.js` (Stammdaten der Abrechnung).

Kein neuer Reiter, also keine Änderung an `frontend/reiter.js`.

## Pate

Tingyu Li
