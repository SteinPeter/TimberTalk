# F0d – Grundlagen für parallele Features

## Ziel

Mehrere Personen können gleichzeitig je ein Feature bauen, ohne dieselben Dateien zu ändern, und
jedes Feature wird mit seinen eigenen Tests auf einer leeren Datenbank geprüft.

## Was der Zimmerer danach kann

Für ihn ändert sich nichts – Oberfläche und Bedienung bleiben wie nach F0c. Der Umbau betrifft
nur das Team: Wer ein Feature baut, legt nur neue Dateien in seinen eigenen Ordnern an und muss
keine gemeinsame Datei mehr anfassen.

## Abnahme

Im Meeting wird genau das vorgeführt:

1. Alle Abnahmepunkte aus F0b und F0c gelten unverändert.
2. Ein Probe-Feature `features/demo/` mit `models.py`, `service.py`, `api.py` und
   `test_demo.py` wird angelegt – ohne Änderung an `main.py` oder einer anderen gemeinsamen
   Datei. `uv run pytest` findet und führt seine Tests aus, und `/api/demo` antwortet.
   Danach wird der Ordner wieder gelöscht.
3. Jeder Test bekommt eine eigene, leere Datenbank im Arbeitsspeicher (Test in
   `tests/test_grundlagen.py`).
4. Ein neuer Reiter-Ordner ohne Eintrag in `frontend/reiter.js` lässt `uv run pytest` scheitern.
5. Ein Pull Request, der nur `docs/handbuch/<feature>.md` statt `docs/handbuch.md` ändert,
   besteht die Handbuch-Prüfung.
6. `uv run pytest`, `uv run ruff check .` und `uv run ruff format --check .` sind grün.

## Nicht dabei

Kein fachliches Feature, keine Tabelle, kein neuer Endpunkt außer denen des Probe-Features, das
nicht im Repository bleibt. Keine Migrationen (F3), keine Feature-Liste mit Paten, kein
`CODEOWNERS`, kein Schutz für `main` – das braucht Absprachen im Team.

## Neues Konzept fürs Team

- **Feature-Ordner werden gefunden, nicht eingetragen.** `load_features()` in
  `features/__init__.py` lädt jeden Ordner mit `__init__.py`: `models.py` für die Tabellen,
  `api.py` mit ihrem `router`.
- **Datenbank-Sitzung als Abhängigkeit.** Endpunkte bekommen ihre Sitzung über
  `session: Session = Depends(get_session)`. Tests tauschen sie gegen eine leere Datenbank aus.
- **Fixtures** in `backend/conftest.py`: `session` für Tests der Logik, `client` für Tests der
  Endpunkte. Ein Test nennt sie einfach als Parameter.
- **Eigene Dateien statt gemeinsamer Listen:** Handbuch-Kapitel je Feature unter
  `docs/handbuch/`, KI-Protokoll je Änderung unter `docs/ki-nutzung/`.

## Reiter

Keiner.

## Pate

<offen>
