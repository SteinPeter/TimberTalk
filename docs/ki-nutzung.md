# KI-Nutzung im Projekt TimberTalk

Protokoll der mit KI-Unterstützung erzeugten Code-Anteile (für den Abschlussbericht).

**Neue Einträge kommen nicht mehr in diese Datei**, sondern als eigene kleine Datei nach
`docs/ki-nutzung/<datum>-<thema>.md` (eine Tabelle wie unten). So hängen nicht mehrere Pull
Requests gleichzeitig eine Zeile an dasselbe Dateiende. Für den Abschlussbericht werden diese Datei
und der Ordner zusammen gelesen. Diese Tabelle hier ist der Stand bis 2026-11-20.

Die Zeilen bis einschließlich 2026-11-11 gehören zu Block 1. Dieser Code liegt nicht mehr im
Arbeitsstand; er ist im Branch `archiv/block1` und im Tag `archiv-block1-2026-11` aufbewahrt.

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
| 2026-11-11 | Claude Opus 5 (Claude Code) | Entwickler-Oberfläche „Werkbank“ unter `/dev`: statische Dateien als REST-Client, nur in der lokalen Installation; dazu `GET /bookings/detail-schemas`, damit Clients die Detailfelder je Buchungsart kennen |
| 2026-11-12 | Claude Opus 5 (Claude Code) | Block 1 nach `archiv/block1` ausgelagert; Neustart mit Feature F0 „Skelett“: Backend (`main.py`, `settings.py`, `db.py`, `/api/health`), Frontend aus HTML/JS ohne Bauschritt, Test, CI-Workflow, `CLAUDE.md`, `README.md` und Steckbrief-Vorlage |
| 2026-11-12 | Claude Opus 5.5 (Claude Code) | Code-Handbuch `docs/handbuch.md` für die gesamte Codebasis; Pflegeregel in `CLAUDE.md`, Hinweis in `README.md` und Punkt in der PR-Vorlage; CI-Prüfung `handbuch.yml`, die bei Code-Änderungen ohne Handbuch-Änderung fehlschlägt |
| 2026-11-18 | Claude Opus 5.5 (Claude Code) | F0b „Reiter für die Funktionsbereiche“: Reiterleiste mit Start, Kalender, Projekte, Kunden, Buchungen, Einstellungen über `#` in der Adresse; Steckbrief, Test, Handbuch |
| 2026-11-18 | Claude Opus 5.5 (Claude Code) | Skill `apple-design` (Commit `91e1566`) als Gestaltungsmaßstab in `CLAUDE.md`, Handbuch und PR-Vorlage verankert |
| 2026-11-18 | Claude Opus 5.5 (Claude Code) | Durchsicht der Reiter-Oberfläche mit `apple-design` und Befunde behoben: Dunkelmodus, erhöhter Kontrast, Texte der leeren Bereiche, Überschrift „Übersicht“ |
| 2026-11-20 | Claude Opus 5.5 (Claude Code) | F0c „Ein Modul je Reiter“: Frontend aufgeteilt in `reiter.js`, `shared/api.js` und `features/<id>/<id>.js` je Reiter, damit Backend und Reiter eines Features parallel von einer Person gebaut werden; Steckbrief, Tests, `CLAUDE.md`, Steckbrief-Vorlage, CI-Pfade, Handbuch |
