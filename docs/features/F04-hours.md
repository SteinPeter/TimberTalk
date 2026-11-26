# F4 – Stunden buchen (Grundversion mit Vorschlägen aus dem Kalender)

## Ziel

Jede Person bucht ihre Arbeitsstunden je Tag und Projekt. Was im Kalender (F8) steht, ist schon
als Vorschlag ausgefüllt – abends genügt „Bestätigen“.

## Was der Zimmerer danach kann

Im Reiter „Buchungen“ öffnet der Geselle abends den Abschnitt „Stunden“. Unter „Aus dem Kalender“
steht z. B. „Carport Berger, 07:00–16:00, Projekt 17, 8,5 Stunden“ – die Arbeitszeit laut Kalender
minus gesetzlicher Pause. Er prüft, ändert wenn nötig die Stunden und tippt auf „Ausgewählte
bestätigen“. Was nicht im Kalender stand, bucht er unter „Weitere Stunden“. Darunter sieht er,
was er diese Woche gebucht hat, mit Summe. Meister und Verwaltung sehen die Stunden aller.

## Abnahme

Im Meeting wird genau das vorgeführt:

1. Der Chef plant Max heute „Carport Berger“ 07:00–16:00 mit Projektnummer 17 und
   „Werkstatt: Abbund“ 16:00–17:30 ein.
2. Max sieht unter „Stunden“ beide Vorschläge: 8,5 h (9 h minus 30 Minuten Pause) und 1,5 h.
   Urlaub, krank und Berufsschule werden nicht vorgeschlagen; ein Termin ohne Uhrzeit mit 8 h.
3. Max bestätigt beide: Die Woche zeigt 10 h, die Vorschläge stehen auf „schon gebucht“. Ein
   zweites Bestätigen desselben Termins am selben Tag wird abgelehnt.
4. Max bucht von Hand 2,5 h „Aufmaß“ auf Projekt 18. 0 h, mehr als 16 h oder ohne Projekt und
   Beschreibung werden mit deutschem Text abgelehnt.
5. Max sieht nur seine eigenen Stunden; die Verwaltung wählt „Alle Mitarbeitenden“ und sieht je
   Person eine Summe. Fremde Buchungen löschen darf nur, wer „Stunden für andere buchen und
   löschen“ hat.
6. `uv run pytest`, `uv run ruff check .` und `uv run ruff format --check .` sind grün.

## Rechte (Voreinstellung, in „Rollen und Rechte“ änderbar)

| Recht | Admin | Meister | Verwaltung | Geselle | Azubi |
| --- | :-: | :-: | :-: | :-: | :-: |
| Eigene Stunden buchen (`hours.book_own`) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Stunden aller Mitarbeitenden sehen (`hours.view_all`) | ✓ | ✓ | ✓ | – | – |
| Stunden für andere buchen und löschen (`hours.manage`) | ✓ | – | ✓ | – | – |

## Nicht dabei

- **Stundenkosten in den Projektkosten (F5):** `project_costs()` rechnet Stunden noch mit 0. Dafür
  braucht es die Zuordnung Person → Stundensatz aus dem Feature Mitarbeitende.
- **Prüfen, ob es das Projekt gibt:** Die Projektnummer ist eine Zahl, bis F3 in `main` ist.
- **Stempeluhr, Überstundenkonto, Freigabe durch den Chef, Erinnerung abends:** später.

## Neues Konzept fürs Team

- **Minuten statt Kommazahl:** gespeichert werden ganze Minuten (`int`), nach außen Stunden als
  `Decimal` (7,5 h = 450 Minuten). So gibt es keine Rundungsfehler.
- **Ein Feature liest ein anderes über dessen Service:** Die Vorschläge kommen aus
  `planning.service.list_entries()`.

## Reiter

Abschnitt `frontend/features/bookings/sections/hours.js` („Stunden“) im Reiter „Buchungen“.

## Pate

<offen>
