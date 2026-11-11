# KI-Nutzung im Projekt TimberTalk Core

Protokoll der mit KI-Unterstützung erzeugten Code-Anteile (für den Abschlussbericht).

| Datum | Modell | Aufgabe |
| --- | --- | --- |
| 2026-11-10 | Claude Opus 5 (Claude Code) | Block 1, Schritt 1: Projektgerüst – `pyproject.toml`, `config.py`, `.env.example`, `/health`-Endpunkt, ruff/mypy/pytest-Konfiguration, Tests |
| 2026-11-10 | Claude Opus 5 (Claude Code) | Block 1, Schritt 2: DB-Grundlage – Basisklasse mit Naming-Convention, Mixins, Typen `GUID`/`Money`/`Quantity`/`UtcDateTime`, Session mit SQLite-Pragmas, Alembic-Einrichtung, Tests |
| 2026-11-10 | Claude Opus 5 (Claude Code) | Block 1, Schritt 3: ServiceContext, fachliche Fehler, zentrales Audit-Log über SQLAlchemy-Events, Operation-Registry für MCP, Migration `audit_events`, Tests |
| 2026-11-10 | Claude Opus 5 (Claude Code) | Block 1, Schritt 4: Referenzdaten – company, settings, tax_rates, units, cost_types, custom_field_definitions samt Repositories, Services und Validierung der Zusatzfelder |
| 2026-11-10 | Claude Opus 5 (Claude Code) | Block 1, Schritt 5: Mitarbeiter, Kunden, Projekte und Arbeitspakete samt Projektnummern-Vergabe und Zyklenprüfung bei Abhängigkeiten |
| 2026-11-10 | Claude Opus 5 (Claude Code) | Block 1, Schritt 6: Materialkatalog und Preise mit Gültigkeitszeiträumen, `get_price` mit Vorrangkette und Prüfung auf Überlappung |
| 2026-11-10 | Claude Opus 5 (Claude Code) | Block 1, Schritt 7: Buchungen mit Details-Registry je Buchungsart, Statusübergängen (draft/confirmed/locked/cancelled) und Preisermittlung |
| 2026-11-10 | Claude Opus 5 (Claude Code) | Block 1, Schritt 8: Anhänge (nur Metadaten), Modellpreise und KI-Verbrauch mit `record_usage` und `usage_summary`; Fehlerbehebung am Audit-Listener |
| 2026-11-10 | Claude Opus 5 (Claude Code) | Block 1, Schritt 9: REST-API mit einem Router je Domäne, Problem-JSON nach RFC 9457, Platzhalter-Authentifizierung und Architekturtests |
| 2026-11-10 | Claude Opus 5 (Claude Code) | Block 1, Schritt 10: Seed mit Beispiel-Zimmerei, `docs/datenmodell.md` mit ER-Diagramm und Erweiterungswegen, Abdeckungsschwelle; Fehlerbehebung an der Transaktionsgrenze der API |
| 2026-11-11 | Claude Opus 5 (Claude Code) | Fehlerbehebung aus der Abnahmeprüfung: Rundung des Buchungsbetrags, `system` als Vorgabe für `X-Actor-Type`, Löschschutz für stornierte Buchungen samt Tests |
