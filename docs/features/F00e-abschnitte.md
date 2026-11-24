# F0e – Abschnitte in gemeinsamen Reitern

## Ziel

Die Reiter „Einstellungen“ und „Buchungen“ werden von mehreren Features gefüllt. Jedes Feature
bringt dort seinen Abschnitt als eigene Datei mit, ohne die Dateien der anderen zu ändern.

## Was der Zimmerer danach kann

In den Einstellungen sieht er links eine Liste der Bereiche, z. B. „Firma und Bank“ oder
„Material und Preise“. Ein Klick zeigt rechts nur diesen Bereich, statt einer langen Seite, in
der man suchen muss. Öffnet er die Einstellungen wieder, ist der Bereich gewählt, den er zuletzt
benutzt hat. Im Reiter „Buchungen“ wechselt er ebenso zwischen den Buchungsarten.

Für das Team gilt: Wer einen Abschnitt baut, legt eine Datei an und trägt sie mit einer Zeile in
die Liste ein – so wie ein Reiter in `reiter.js`.

## Abnahme

Im Meeting wird genau das vorgeführt:

1. Alle Abnahmepunkte aus F0b, F0c und F0d gelten unverändert.
2. Unter `frontend/features/settings/sections/` und `frontend/features/bookings/sections/` liegt
   je Abschnitt eine Datei. Sie exportiert `id` (gleich dem Dateinamen), `title` und
   `render(container)`, genau wie ein Reiter. Die Auswahl baut `frontend/shared/sections.js`.
3. Die Reihenfolge steht in der Liste `sections.js` im jeweiligen Reiter-Ordner. Ein neuer
   Abschnitt ist eine neue Datei und eine Zeile in dieser Liste; `settings.js` und `bookings.js`
   werden dafür nicht geändert.
4. Ein Probe-Abschnitt wird in den Einstellungen ergänzt und erscheint in der Liste. Danach wird
   er wieder gelöscht.
5. Wirft ein Abschnitt beim Aufbauen einen Fehler, zeigt nur dieser Abschnitt eine Meldung – die
   anderen Abschnitte funktionieren weiter.
6. Ein Abschnitt wird erst aufgebaut, wenn man ihn zum ersten Mal öffnet. Der zuletzt gewählte
   Abschnitt ist nach dem Neuladen wieder gewählt.
7. Eine Datei unter `sections/` ohne Eintrag in `sections.js` lässt `uv run pytest` scheitern
   (wie der Test für `reiter.js` in `tests/test_health.py`).
8. Die Oberfläche ist mit dem Skill `apple-design` durchgesehen; die Seiten sind im Pull Request
   genannt.
9. `uv run pytest`, `uv run ruff check .` und `uv run ruff format --check .` sind grün.

## Nicht dabei

- **Keine fachlichen Inhalte.** Die Abschnitte bleiben leer, bis ein Feature sie füllt. Ist F5
  (Material, Fahrten und Preise) schon gemergt, werden dessen Dateien nur in `sections/`
  verschoben und eingetragen – ohne Änderung an ihrem Inhalt.
- **Keine Unteradressen** wie `#settings/company`. `app.js` bleibt, wie es ist; der zuletzt
  gewählte Abschnitt wird im Browser gemerkt (`localStorage`).
- **Kein Backend.** Wem die Stammdaten der Abrechnung gehören (Firma, Bank, Umsatzsteuer,
  Stundensätze, Fahrtkosten je km), ist eine eigene Frage für das Team: Vorschlag ist ein
  eigenes Feature `company`, das alle anderen über `company.service` lesen. Darüber wird im
  Meeting entschieden, nicht in diesem Steckbrief.

## Neues Konzept fürs Team

- **Abschnitt:** ein Teil eines gemeinsamen Reiters, der einem Feature gehört. Er ist aufgebaut
  wie ein Reiter (`id`, `title`, `render`), steht aber in der Liste `sections.js` seines Reiters
  statt in `reiter.js`.
- **Wer besitzt welche Datei:** Die Datei eines Abschnitts beginnt mit dem Namen des Features im
  Backend: `sections/materials.js`, oder `sections/materials-company.js`, wenn ein Feature mehrere
  Abschnitte hat. Die Reiter-Datei selbst (`settings.js`, `bookings.js`) gehört zum Grundgerüst
  und wird von Features nicht geändert.
- **Gestaltung:** Die Einstellungen bekommen eine Seitenleiste (`sidebars.md › Best practices`,
  `settings.md › Platform considerations`: zuletzt benutzten Bereich wieder öffnen). Die
  Buchungen bekommen Reiter über dem Inhalt, also eine Tab-Ansicht – kein Umschalter, denn
  `segmented-controls.md › Platform considerations` empfiehlt für das Umschalten von Ansichten im
  Hauptbereich eine Tab-Ansicht.

## Reiter

Zwei bestehende Reiter, kein neuer:

- `settings` („Einstellungen“): `frontend/features/settings/settings.js` und `sections.js`
- `bookings` („Buchungen“): `frontend/features/bookings/bookings.js` und `sections.js`

Keine Änderung an `frontend/reiter.js`.

## Pate

<offen>
