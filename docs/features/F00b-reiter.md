# F0b – Reiter für die Funktionsbereiche

## Ziel

Die Oberfläche hat ein festes Gerüst: Jeder Funktionsbereich von TimberTalk öffnet sich über einen
eigenen Reiter.

## Was der Zimmerer danach kann

Er sieht oben eine Leiste mit den Reitern Start, Kalender, Projekte, Kunden, Buchungen und
Einstellungen. Ein Klick öffnet den Bereich, der gewählte Reiter ist hervorgehoben. Auf „Start“
steht unter der Überschrift „Übersicht“ wie bisher, dass TimberTalk läuft und die Datenbank
antwortet. Die anderen Bereiche sind noch leer und sagen in einem Satz, was dort hinkommt. Ist am
Rechner die dunkle Darstellung eingeschaltet, erscheint auch TimberTalk dunkel.

## Abnahme

Im Meeting wird genau das vorgeführt:

1. `uv run timbertalk` öffnet die Seite; der Reiter „Start“ ist gewählt und zeigt
   „TimberTalk läuft“ mit Backend und Datenbank auf „antwortet“.
2. Ein Klick auf jeden der sechs Reiter zeigt den passenden Bereich und hebt den Reiter hervor.
3. Die Adresse ändert sich mit, z. B. `http://127.0.0.1:8000/#planning`. Neu laden oder die
   Adresse direkt aufrufen öffnet denselben Reiter; Zurück im Browser springt zum vorigen Reiter.
4. Eine unbekannte Adresse wie `/#gibtsnicht` zeigt den Reiter „Start“.
5. Mit eingeschaltetem Dunkelmodus im Betriebssystem erscheint die Seite dunkel und gut lesbar.
6. `uv run pytest`, `uv run ruff check .` und `uv run ruff format --check .` sind grün.

## Nicht dabei

Keine Inhalte in Kalender, Projekte, Kunden, Buchungen und Einstellungen – jeder Bereich wird mit
seinem eigenen Feature gefüllt. Keine neuen Endpunkte, keine Tabellen, keine Anmeldung.

## Neues Konzept fürs Team

- **Reiter über den Teil hinter `#` in der Adresse.** Alle Bereiche stehen in derselben Seite
  `index.html`; `app.js` blendet nur den Bereich ein, dessen Name hinter dem `#` steht. Dadurch
  braucht es weder einen Server-Weg je Bereich noch ein Framework, und Neu laden, Lesezeichen und
  Zurück funktionieren trotzdem.
- **Ein neuer Bereich = zwei Zeilen HTML.** Ein Link in der Reiterleiste und ein `<section>` mit
  derselben `id`.

## Pate

<offen>
