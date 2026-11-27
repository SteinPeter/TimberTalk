# F13 – Einstellungen exportieren und importieren

## Ziel

Alle Einstellungen des Betriebs lassen sich mit einem Klick als Datei sichern und mit einem Klick
wieder einlesen.

## Was der Zimmerer danach kann

Unter „Einstellungen → Export und Import“ klickt der Chef auf „Alles exportieren“ und bekommt eine
Datei `timbertalk-einstellungen-<datum>.json` mit Firmendaten, Stundensätzen, Materialstamm samt
Preisen sowie Fahrzeugen und Maschinen. Auf einem neuen Rechner wählt er „Importieren …“ und die
Datei; TimberTalk sagt vorher, was drinsteht, und danach, was übernommen wurde.

## Abnahme

Im Meeting wird genau das vorgeführt:

1. „Alles exportieren“ lädt eine Datei herunter; die Meldung nennt Firma, Zahl der Stundensätze,
   Materialien und Fahrzeuge/Maschinen.
2. In einem leeren Betrieb (neue Datenbank) bringt „Importieren …“ mit dieser Datei genau dieselben
   Einstellungen zurück – Preise auf den Cent genau, mit ihrem Gültig-ab-Datum.
3. Derselbe Import ein zweites Mal legt nichts doppelt an. Ein Material, das nur im Betrieb und
   nicht in der Datei steht, bleibt erhalten – der Import ergänzt nur, er löscht nie.
4. Eine fremde Datei oder eine aus einer neueren Version wird mit einer deutschen Meldung abgelehnt.
5. Ein Geselle sieht den Abschnitt nicht; die API antwortet ihm mit 403 (Recht `finance.edit`).
6. `uv run pytest`, `uv run ruff check .` und `uv run ruff format --check .` sind grün.

## Nicht dabei

- Konten, Passwörter und Rechte (gehören zu F10 und sollen nicht in einer Datei herumliegen).
- Bewegungsdaten: Termine, Buchungen, Stunden, Projekte – das ist eine vollständige
  Datensicherung, sie kommt später im selben Ordner `backup/`.
- Einstellungen löschen oder ersetzen statt ergänzen.

## Neues Konzept fürs Team

- **Ein Feature ohne eigene Tabellen:** `backup/` liest und schreibt nur über die `service.py` der
  Features, denen die Daten gehören (`materials`, `planning`). Kommt eine neue Einstellung dazu,
  ergänzt man `models.py` (Dateiformat) und `service.py` hier um wenige Zeilen.
- **Dateiformat mit Kennung und Version** (`format`, `version`): So erkennt der Import fremde und
  zu neue Dateien.

## Reiter

`frontend/features/settings/sections/backup.js` – Abschnitt „Export und Import“ im Reiter
„Einstellungen“ (eingetragen in `settings/sections.js`).

## Pate

<offen>
