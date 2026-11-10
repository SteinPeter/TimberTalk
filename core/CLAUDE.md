# TimberTalk Core (Backend) – Regeln für Claude Code

Dieses Verzeichnis (`core/`) enthält das Backend von TimberTalk: eine Sprach-App und Betriebssoftware für Zimmereien.
Das Backend läuft lokal auf dem PC im Betrieb. Web-App, PC-Oberfläche, eine spätere native App, das CAD-Modul (Modul B)
und ein späterer MCP-Server sind **nur Clients** dieses Backends.

## Architektur (verbindlich)

```
Clients:      REST-API (FastAPI)      MCP-Server (später)      CLI/Skripte
                    \                        |                     /
Service-Schicht:     ───────────  services (Geschäftslogik)  ───────────
                                             |
Daten:                         repositories → SQLAlchemy-Modelle → DB
```

- **Geschäftslogik nur in der Service-Schicht.** Router (und später MCP-Tools) sind dünne Adapter: Eingabe prüfen,
  Service aufrufen, Ergebnis zurückgeben. Keine Datenbankzugriffe in Routern.
- **Services kennen kein FastAPI.** Sie bekommen Pydantic-Schemas plus einen `ServiceContext` (Session, Akteur, Quelle,
  Korrelations-ID) und geben Pydantic-Schemas zurück. So kann ein MCP-Server dieselben Funktionen später direkt nutzen.
- **Jede öffentliche Service-Funktion** hat Typannotationen und einen Docstring (Deutsch, ein Satz Zweck, Parameter
  mit Einheiten). Daraus werden später MCP-Tool-Beschreibungen erzeugt.
- **Domänen sind eigene Pakete** unter `src/timbertalk_core/domain/<name>/` mit `models.py`, `schemas.py`,
  `repository.py`, `service.py`. Neue Domänen dürfen bestehende nicht umbauen müssen.

## Datenregeln

- **IDs:** UUID (bevorzugt UUIDv7, zeitlich sortierbar). Keine fortlaufenden Integer-IDs als Primärschlüssel.
- **Geld und Mengen:** niemals `float`. In Python immer `Decimal`. In der DB über eigene Typen `Money` und `Quantity`
  (siehe `db/types.py`), die auf SQLite verlustfrei als TEXT und auf Postgres als NUMERIC gespeichert werden.
- **Zeit:** immer timezone-aware UTC in der DB. Reine Kalendertage (Buchungsdatum) als `date`.
- **Jede Tabelle** hat `id`, `created_at`, `updated_at`, `deleted_at` (Soft Delete), `version` (optimistisches Sperren).
- **Enums** als String-Spalten mit Prüfung in Pydantic, keine nativen DB-Enums (einfachere Migrationen).
- **Erweiterbare Felder:** Kern-Entitäten haben eine JSON-Spalte `attributes`. Zulässige Zusatzfelder werden in
  `custom_field_definitions` beschrieben und im Service validiert. Neue Kostenarten sind Daten (`cost_types`), kein Code.
- **Datenbank:** SQLite ist Standard (lokale Installation). Code muss auch auf Postgres laufen: keine SQLite-Spezialitäten
  in Abfragen. SQLite immer mit `PRAGMA foreign_keys=ON` und `journal_mode=WAL`.
- **Schemaänderungen nur über Alembic-Migrationen.** Nie `create_all()` außerhalb von Tests.

## Status und Nachvollziehbarkeit

- Buchungen haben einen Status: `draft` → `confirmed` → `locked` (später durch Rechnung) bzw. `cancelled`.
  Einträge aus KI oder Import starten immer als `draft`. Nur ein menschlicher Akteur darf bestätigen.
  `locked` ist unveränderbar.
- Jede schreibende Service-Operation erzeugt einen Eintrag im Audit-Log (Akteur, Aktion, Entität, Änderungen,
  Quelle, Korrelations-ID). Das passiert zentral, nicht in jedem Service von Hand.

## Code-Stil und Werkzeuge

- Python 3.12, Paketverwaltung mit `uv`.
- FastAPI, SQLAlchemy 2.x (typed `Mapped[...]`), Alembic, Pydantic v2, pydantic-settings.
- Tests mit `pytest`; Lint/Format mit `ruff`; Typprüfung mit `mypy --strict` für `src/`.
- **Bezeichner im Code auf Englisch**, fachliche Begriffe laut Glossar unten. Docstrings, Fehlermeldungen
  für Nutzer und Doku auf Deutsch.
- Keine Geheimnisse im Repo. Konfiguration über `.env` (Vorlage `.env.example`).
- Kein Streamlit.

## Befehle

```bash
uv sync                          # Abhängigkeiten
uv run alembic upgrade head      # DB auf aktuellen Stand
uv run pytest                    # Tests
uv run ruff check . && uv run ruff format --check .
uv run mypy src
uv run python -m timbertalk_core.scripts.seed   # Beispieldaten
uv run uvicorn timbertalk_core.api.app:app --reload
```

Vor jedem Commit müssen Tests, ruff und mypy grün sein.

## Glossar (Deutsch → Code)

| Fachbegriff | Code |
| --- | --- |
| Betrieb / Firmendaten | `company` |
| Mitarbeiter | `employee` |
| Kunde | `customer` |
| Projekt / Auftrag | `project` |
| Arbeitspaket | `work_package` |
| Buchung (Stunden, Material, Fahrt, …) | `booking` |
| Kostenart | `cost_type` |
| Einheit | `unit` |
| Materialkatalog / Artikel | `material_item` |
| Preis / Preisliste | `price` |
| Beleg / Anhang | `attachment` |
| Änderungsprotokoll | `audit_event` |
| KI-Verbrauch | `llm_usage` |

## KI-Nutzung dokumentieren

Wenn du (Claude Code) Code erzeugst, ergänze `docs/ki-nutzung.md` um eine Zeile: Datum, Modell, Aufgabe.
Das wird für den Abschlussbericht gebraucht.
