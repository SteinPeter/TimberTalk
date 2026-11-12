# F0 – Skelett

## Ziel

Die Seite „TimberTalk läuft“ öffnet sich im Browser und zeigt, dass Backend und Datenbank
antworten.

## Was der Zimmerer danach kann

Noch nichts von seiner Arbeit erledigen. Er startet TimberTalk mit einem Befehl, der Browser
öffnet sich von selbst und auf der Seite steht, dass das Programm läuft und die Datenbank
erreichbar ist. Damit ist bewiesen, dass alle Teile zusammenpassen: Start, Backend, Datenbank
und Oberfläche. Darauf setzen alle weiteren Features auf.

## Abnahme

Im Meeting wird genau das vorgeführt:

1. `uv sync` im Ordner `backend/` läuft durch.
2. `uv run timbertalk` startet den Server auf <http://127.0.0.1:8000> und öffnet den Browser.
3. Die Seite zeigt „TimberTalk läuft“ sowie Backend und Datenbank mit dem Zustand „antwortet“.
4. `http://127.0.0.1:8000/api/health` liefert `{"status": "ok", "database": "ok"}`.
5. `uv run pytest`, `uv run ruff check .` und `uv run ruff format --check .` sind grün.

## Nicht dabei

Keine Kunden, Projekte, Buchungen oder Tabellen – die erste echte Tabelle kommt mit dem nächsten
Feature. Keine Anmeldung, keine Benutzerverwaltung, keine Exe-Datei (F1), keine Migrationen (F3),
kein Sprachteil.

## Neues Konzept fürs Team

Drei Dinge kommen zum ersten Mal vor:

- **Die Trennung von Backend und Frontend.** Das Backend liefert Daten unter `/api`, das Frontend
  ist nur eine Seite, die diese Daten per `fetch` abholt. Beide reden ausschließlich über die API
  miteinander – so kann später eine App denselben Weg nutzen.
- **Der Gesundheitsendpunkt.** `/api/health` ist die einfachste Frage, die man dem Programm
  stellen kann: „Lebst du, und erreichst du die Datenbank?“ Er wird bei jedem Feature mitgeprüft.
- **Der Startbefehl `uv run timbertalk`.** Er steht in `pyproject.toml` unter `[project.scripts]`
  und ist die Vorlage für die Exe-Datei in F1.

## Pate

Peter Stein
