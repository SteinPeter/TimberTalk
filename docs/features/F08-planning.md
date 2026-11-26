# F8 – Kalender je Mitarbeiter (Dispatching)

## Ziel

Für jede Person im Betrieb gibt es einen Kalender. Wer plant, teilt Leute auf einer Plantafel
Baustellen und Terminen zu und sieht sofort, wer schon verplant oder abwesend ist.
Erster Teil des Features `planning/` aus dem Programmaufbau („Kalender je Mitarbeiter“).

## Was der Zimmerer danach kann

Im Reiter „Kalender“ sieht der Chef die Woche als Plantafel: eine Zeile je Person, eine Spalte je
Tag. Mit einem Klick auf „+“ in einer Zelle oder auf „Termin eintragen“ legt er einen Termin an –
z. B. „Carport Berger“ von Montag bis Mittwoch für Max und Tom, mit Ort und Uhrzeit. Ist jemand
schon verplant oder im Urlaub, sagt TimberTalk es nach dem Speichern. Ein Geselle sieht auf dem
Handy seine eigene Woche als Liste nach Tagen – wo er wann ist und mit wem.

## Abnahme

Im Meeting wird genau das vorgeführt:

1. **Plantafel:** Der Chef sieht KW 49 mit allen aktiven Konten als Zeilen, blättert mit
   „Vorwoche“, „Heute“, „Nächste“, und der heutige Tag ist hervorgehoben.
2. **Einplanen:** Er trägt „Carport Berger, Potsdam“ von Mo bis Mi für Max und Tom ein. Der
   Termin steht in beiden Zeilen an allen drei Tagen.
3. **Überschneidung:** Er trägt für Tom am Dienstag Urlaub ein. Nach dem Speichern steht dort
   „Achtung: Tom Adler ist am 01.12.2026 schon eingeplant: Carport Berger.“ – gespeichert ist es
   trotzdem. Vormittags- und Nachmittagstermine am selben Tag gelten nicht als Überschneidung.
4. **Ändern und löschen:** Ein Klick auf den Termin öffnet ihn; Zeitraum, Personen und Uhrzeit
   lassen sich ändern, der Termin lässt sich nach Rückfrage löschen.
5. **Persönlicher Kalender:** Max meldet sich auf dem Handy an und sieht „Meine Woche“ mit seinen
   Terminen, Ort und Kollegen – ohne „+“ und ohne „Termin eintragen“.
6. **Rechte:** Nimmt der Chef (Admin-Konto) in „Rollen und Rechte“ den Gesellen das Häkchen „Kalender aller
   Mitarbeitenden sehen“, sieht Max nur noch seinen eigenen Kalender, auch über die API.
   Eintragen ohne „Termine für alle planen“ antwortet mit 403.
7. `uv run pytest`, `uv run ruff check .` und `uv run ruff format --check .` sind grün.

## Rechte (Voreinstellung, in „Rollen und Rechte“ änderbar)

| Recht | Admin (Chef) | Meister | Verwaltung | Geselle |
| --- | :-: | :-: | :-: | :-: |
| Kalender aller Mitarbeitenden sehen (`calendar.view_all`) | ✓ | ✓ | ✓ | ✓ |
| Termine für alle planen und ändern (`calendar.dispatch`) | ✓ | ✓ | ✓ | – |

Ohne `calendar.view_all` sieht man nur den eigenen Kalender.

## Nicht dabei

- **Verknüpfung mit Projekten:** Der Termin hat einen freien Titel. Die Projektnummer kommt dazu,
  sobald F3 (Projekte) in `main` ist.
- **Arbeitspakete und Gantt-Ansicht:** späterer Teil von `planning/`.
- **Urlaubsanträge durch Gesellen, wiederkehrende Termine, Export in den Handy-Kalender (iCal),
  Fahrzeuge und Maschinen als „Personen“:** Vorschläge für spätere Features.

## Neues Konzept fürs Team

- **Termin über mehrere Tage und Personen:** Ein Termin (`planning_entry`) hat ersten und letzten
  Tag; wer dabei ist, steht in einer eigenen Tabelle (`planning_assignment`), eine Zeile je Person.
- **Hinweis statt Verbot:** Überschneidungen werden gemeldet, aber nicht verhindert – die
  Entscheidung bleibt beim Planenden.
- **`<dialog>`:** Der Browser bringt das Fenster „Termin eintragen“ selbst mit (`showModal()`);
  Escape und „Abbrechen“ schließen es.

## Reiter

`frontend/features/planning/planning.js` („Kalender“) – war bisher leer.

## Pate

<offen>
