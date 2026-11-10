# KI-Nutzung im Projekt TimberTalk Core

Protokoll der mit KI-Unterstützung erzeugten Code-Anteile (für den Abschlussbericht).

| Datum | Modell | Aufgabe |
| --- | --- | --- |
| 2026-11-10 | Claude Opus 5 (Claude Code) | Block 1, Schritt 1: Projektgerüst – `pyproject.toml`, `config.py`, `.env.example`, `/health`-Endpunkt, ruff/mypy/pytest-Konfiguration, Tests |
| 2026-11-10 | Claude Opus 5 (Claude Code) | Block 1, Schritt 2: DB-Grundlage – Basisklasse mit Naming-Convention, Mixins, Typen `GUID`/`Money`/`Quantity`/`UtcDateTime`, Session mit SQLite-Pragmas, Alembic-Einrichtung, Tests |
| 2026-11-10 | Claude Opus 5 (Claude Code) | Block 1, Schritt 3: ServiceContext, fachliche Fehler, zentrales Audit-Log über SQLAlchemy-Events, Operation-Registry für MCP, Migration `audit_events`, Tests |
| 2026-11-10 | Claude Opus 5 (Claude Code) | Block 1, Schritt 4: Referenzdaten – company, settings, tax_rates, units, cost_types, custom_field_definitions samt Repositories, Services und Validierung der Zusatzfelder |
| 2026-11-10 | Claude Opus 5 (Claude Code) | Block 1, Schritt 5: Mitarbeiter, Kunden, Projekte und Arbeitspakete samt Projektnummern-Vergabe und Zyklenprüfung bei Abhängigkeiten |
