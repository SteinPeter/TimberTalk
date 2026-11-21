# F0c – Ein Modul je Reiter

## Ziel

Jeder Reiter hat eine eigene Datei im Frontend, damit Backend und Reiter eines Features von
derselben Person parallel zu den anderen Features gebaut werden können.

## Was der Zimmerer danach kann

Für ihn ändert sich nichts: Er sieht dieselbe Reiterleiste mit denselben Bereichen wie nach F0b.
Der Umbau betrifft nur das Team. Wer ein Feature wie „Kunden“ baut, arbeitet im Frontend nur noch
in seinem eigenen Ordner `frontend/features/customers/` und kommt den anderen nicht in die Quere.

## Abnahme

Im Meeting wird genau das vorgeführt:

1. Alle Abnahmepunkte 1 bis 5 aus F0b gelten unverändert: Start mit Status, sechs Reiter,
   Adresse mit `#`, unbekannte Adresse zeigt „Start“, Dunkelmodus.
2. Unter `frontend/features/` liegt je Reiter ein Ordner mit einer Datei `<id>.js`; darin steht
   alles, was dieser Reiter zeigt.
3. `index.html` enthält nur noch das Gerüst (Leiste und leeres `<main>`); die Reiter stehen in
   der Liste `frontend/reiter.js`.
4. Wirft ein Reiter beim Aufbauen einen Fehler, zeigt nur dieser Bereich eine Fehlermeldung –
   die anderen Reiter funktionieren weiter.
5. `uv run pytest`, `uv run ruff check .` und `uv run ruff format --check .` sind grün.

## Nicht dabei

Keine neuen Inhalte in den Reitern, kein anderes Aussehen, keine neuen Endpunkte, keine Tabellen.
Kein eigenes CSS je Reiter – das kommt mit dem ersten Feature, das es braucht.

## Neues Konzept fürs Team

- **Ein Feature = Backend-Ordner + Reiter-Ordner, gebaut von derselben Person.** Der
  Reiter-Ordner heißt wie der Reiter in der Adresse (`#customers` → `frontend/features/customers/`).
  Welcher Reiter zu einem Feature gehört, steht in dessen Steckbrief unter „Reiter“.
- **Ein Reiter-Modul exportiert drei Dinge:** `id` (Name hinter `#`), `title` (Text in der Leiste)
  und `render(panel)` (füllt den Bereich, wenn er zum ersten Mal geöffnet wird).
- **Gemeinsames liegt an einer Stelle:** Umschalten der Reiter in `app.js`, die Liste der Reiter
  in `reiter.js`, Abfragen an die API über `shared/api.js`, Grundaussehen in `style.css`.

## Reiter

Alle sechs – sie werden nur in eigene Dateien verschoben.

## Pate

<offen>
