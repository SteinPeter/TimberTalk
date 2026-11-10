# TimberTalk Core

Backend von TimberTalk – einer Sprach-App und Betriebssoftware für Zimmereien.
Das Backend läuft lokal auf dem PC im Betrieb. Web-App, PC-Oberfläche, eine spätere native App,
das CAD-Modul und ein späterer MCP-Server sind nur Clients dieses Backends.

## Einstieg

```bash
uv sync                          # Abhängigkeiten
cp .env.example .env             # Konfiguration anpassen
uv run alembic upgrade head      # Datenbank auf aktuellen Stand
uv run python -m timbertalk_core.scripts.seed   # Beispieldaten
uv run uvicorn timbertalk_core.api.app:app --reload
```

## Prüfen

```bash
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy src
```

## Aufbau

- `src/timbertalk_core/domain/<name>/` – je Domäne `models.py`, `schemas.py`, `repository.py`, `service.py`
- `src/timbertalk_core/api/` – REST-API, nur Adapter auf die Services
- `docs/datenmodell.md` – Datenmodell und Erweiterungswege
