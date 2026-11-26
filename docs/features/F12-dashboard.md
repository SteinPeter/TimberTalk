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
2. Der Chef genehmigt auf dem Dashboard; die Karte zeigt „Keine offenen Anträge.“
3. „Anpassen“: Systemstatus abwählen, „Stunden heute“ nach oben – nach dem Neuladen bleibt es so.
   „Voreinstellung“ stellt die Auswahl der Widgets selbst wieder her.
4. Ein Geselle sieht „Offene Urlaubsanträge“ nicht (Recht `calendar.approve_absence`).
5. **Für das Team:** Eine neue Datei `frontend/features/<ordner>/widgets/<name>.js` mit `title`
   und `render()` erscheint nach dem Neuladen unter „Anpassen“ – ohne Änderung an `start.js` oder
   einer Liste. Ein Test prüft, dass jedes Widget `title` und `render` hat.
6. `uv run pytest`, `uv run ruff check .` und `uv run ruff format --check .` sind grün.

## Nicht dabei

- Widgets verschieben per Ziehen, Größe einzelner Widgets, Widgets für Projekte und Kunden (die
  bringen F2 und F3 selbst mit, sobald sie in `main` sind).

## Neues Konzept fürs Team

- **Widgets werden gefunden, nicht eingetragen** – wie Feature-Ordner im Backend:
  `GET /api/dashboard/widgets` sucht alle `frontend/features/*/widgets/*.js`.
- **Bauplan eines Widgets** (steht oben in `frontend/features/start/start.js`):
  `export const title`, `export async function render(container)`, wahlweise `permission`,
  `order` und `defaultOn`.

## Reiter

`frontend/features/start/start.js` („Start“, über das Logo oben links). Die Widgets liegen in den
Ordnern ihrer Features: `start/widgets/status.js`, `planning/widgets/absence-requests.js`,
`planning/widgets/my-week.js`, `bookings/widgets/hours-today.js`.

## Pate

<offen>
