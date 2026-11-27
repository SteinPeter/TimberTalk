# F12 – Dashboard mit Widgets

## Ziel

Die Startseite zeigt jeder Person auf einen Blick, was heute wichtig ist – als Widgets, die die
einzelnen Features selbst mitbringen und die jede Person selbst zusammenstellt.

## Was der Zimmerer danach kann

Ein Klick auf das Logo oben links öffnet das Dashboard: „Hallo Klaus“ und darunter Karten wie
„Offene Urlaubsanträge“ (mit Genehmigen und Ablehnen), „Meine nächsten Termine“, „Stunden heute“
und „Systemstatus“. Mit „Anpassen“ wählt er Karten ab und an und ändert ihre Reihenfolge; das gilt
nur für ihn. Ein Geselle sieht nur Karten, für die er das Recht hat.

## Abnahme

Im Meeting wird genau das vorgeführt:

1. Max beantragt Urlaub. Der Chef bekommt eine Mitteilung „Urlaubsantrag von Max Berger: … – bitte
   auf dem Dashboard entscheiden.“; ein Klick darauf öffnet das Dashboard. Dort steht der Antrag,
   bis er entschieden ist – kein Popup, das sich wegklickt.
2. Der Chef genehmigt auf dem Dashboard; die Karte zeigt „Keine offenen Anträge.“ und die Mitteilung
   „bitte entscheiden“ ist aus der Glocke verschwunden. Beim nächsten Öffnen des Dashboards fehlt die
   Karte ganz – sie erscheint erst wieder, wenn jemand Urlaub beantragt.
3. **Nur bei Bedarf:** „Systemstatus“ erscheint nur, wenn Backend oder Datenbank nicht antworten;
   „Stunden heute“ nur, solange heute noch etwas zu bestätigen ist. Unter „Anpassen“ steht das
   jeweils dabei („Erscheint nur, …“).
4. **Größe passt sich an:** Jede Karte ist so hoch wie ihr Inhalt, die Spalten füllen die Breite.
   Wird eine Karte kürzer (Antrag entschieden), rücken die Karten darunter nach – ohne Lücke.
5. „Anpassen“: Systemstatus abwählen, „Stunden heute“ nach oben – nach dem Neuladen bleibt es so.
   „Voreinstellung“ stellt die Auswahl der Widgets selbst wieder her.
6. Ein Geselle sieht „Offene Urlaubsanträge“ nicht (Recht `calendar.approve_absence`).
7. **Für das Team:** Eine neue Datei `frontend/features/<ordner>/widgets/<name>.js` mit `title`
   und `render()` erscheint nach dem Neuladen unter „Anpassen“ – ohne Änderung an `start.js` oder
   einer Liste. Ein Test prüft, dass jedes Widget `title` und `render` hat.
8. `uv run pytest`, `uv run ruff check .` und `uv run ruff format --check .` sind grün.

## Nicht dabei

- Widgets verschieben per Ziehen, Größe einzelner Widgets von Hand einstellen, Widgets für Projekte und Kunden (die
  bringen F2 und F3 selbst mit, sobald sie in `main` sind).

## Neues Konzept fürs Team

- **Widgets werden gefunden, nicht eingetragen** – wie Feature-Ordner im Backend:
  `GET /api/dashboard/widgets` sucht alle `frontend/features/*/widgets/*.js`.
- **Bauplan eines Widgets** (steht oben in `frontend/features/start/start.js`):
  `export const title`, `export async function render(container)`, wahlweise `permission`,
  `order`, `defaultOn` und `showsWhen`. Gibt `render()` `false` zurück, erscheint die Karte nicht
  („nur bei Bedarf“).

## Reiter

`frontend/features/start/start.js` („Start“, über das Logo oben links). Die Widgets liegen in den
Ordnern ihrer Features: `start/widgets/status.js`, `planning/widgets/absence-requests.js`,
`planning/widgets/my-week.js`, `bookings/widgets/hours-today.js`.

## Pate

<offen>
