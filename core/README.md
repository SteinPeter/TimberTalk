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
uv run pytest                                   # Tests
uv run pytest --cov                             # Tests mit Abdeckung (Schwelle 80 %)
uv run ruff check . && uv run ruff format --check .
uv run mypy src
```

Der Postgres-Migrationstest läuft nur, wenn `TEST_DATABASE_URL` gesetzt ist:

```bash
TEST_DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/timbertalk_test" \
  uv run pytest tests/test_migrations.py
```

## Aufbau

- `src/timbertalk_core/domain/<name>/` – je Domäne `models.py`, `schemas.py`, `repository.py`, `service.py`
- `src/timbertalk_core/api/` – REST-API, nur Adapter auf die Services
- `src/timbertalk_core/operations.py` – Registry aller Service-Operationen (Grundlage für MCP)
- `docs/datenmodell.md` – Datenmodell, ER-Diagramm und Erweiterungswege

## Zugang zur API

Jede Anfrage außer `/health` braucht den Platzhalter-Schlüssel und einen Akteur:

| Kopfzeile | Bedeutung |
| --- | --- |
| `X-API-Key` | Schlüssel aus `.env` (`TIMBERTALK_API_KEY`) |
| `X-Actor` | UUID des Akteurs |
| `X-Actor-Type` | `user`, `agent` oder `system`; nur `user` darf Buchungen bestätigen |
| `X-Source` | `manual`, `agent`, `voice`, `import`, `cad`, `system` |
| `X-Correlation-Id` | verbindet zusammengehörige Vorgänge im Änderungsprotokoll |

Interaktive Beschreibung: <http://localhost:8000/docs>, Katalog aller Operationen:
<http://localhost:8000/operations>
