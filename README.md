# TimberTalk

TimberTalk ist eine Betriebssoftware für Zimmereien. Sie erfasst Kunden, Projekte und Buchungen
von Stunden, Material und Fahrten – später auch per Sprache – und läuft lokal auf dem PC im
Betrieb. Das Backend ist die einzige Quelle der Wahrheit; Weboberfläche, eine spätere App und
das CAD-Modul sind nur Clients seiner API.

## Schnellstart

```bash
cd backend
uv sync
uv run timbertalk
```

Der Server läuft dann auf <http://127.0.0.1:8000> und der Browser öffnet sich.

**Zum Ausprobieren ist alles schon da:** Eine neue Datenbank bekommt beim ersten Start einen
Beispielbetrieb (Firma, Materialkatalog mit Preisen, Fahrzeuge, Konten aller Rollen, Termine,
Urlaubsanträge, gebuchte Stunden) und der **Demo-Modus** ist an: Man ist ohne Passwort als Chef
Klaus Schulz angemeldet; nach „Abmelden“ wählt man jedes andere Konto per Klick. Eine schon
vorhandene Datenbank bekommt den Beispielbetrieb mit `uv run python -m timbertalk.demo`.

**Für den echten Betrieb** in `backend/.env` eintragen: `TIMBERTALK_DEMO=false` und
`TIMBERTALK_DEV_LOGIN_HINT=false`. Dann gibt es weder Demo-Modus noch Beispieldaten; beim ersten
Start entsteht nur das Konto `admin` mit Passwort `admin`, das man bei der ersten Anmeldung ersetzt.

Passwort des einzigen Admin-Kontos vergessen? Direkt am Rechner im Betrieb (im Ordner `backend/`):

```bash
uv run python -m timbertalk.features.accounts.cli admin
```

Das Konto bekommt wieder das Standardpasswort (`timbertalk-start`, falls nicht geändert); bei der
nächsten Anmeldung legt man ein eigenes fest.

## Aufbau

```
backend/     Backend (FastAPI, SQLModel). Die API liegt unter /api.
frontend/    HTML, CSS und JavaScript – ohne Bauschritt und ohne Framework.
docs/        Steckbriefe der Features, Archivunterlagen, KI-Nutzung.
```

Wir bauen Feature für Feature. Was ein Feature enthält, steht in seinem Steckbrief unter
`docs/features/`; die Regeln für den Code stehen in `CLAUDE.md`. Wie der Code aufgebaut ist und
was jede Datei tut, erklärt das Code-Handbuch `docs/handbuch.md`; jedes fachliche Feature hat
dazu ein eigenes Kapitel unter `docs/handbuch/`.

## Glossar

| Fachbegriff | Im Code |
| --- | --- |
| Kunde | `customer` |
| Projekt | `project` |
| Buchung | `booking` |
| Kostenart | `cost_type` |
| Konto | `account` |
| Rolle (Admin, Chef, Meister, Verwaltung, Geselle, Azubi) | `role` (`admin`, `owner`, `master`, `office`, `journeyman`, `apprentice`) |
| Widget (Dashboard) | `frontend/features/<ordner>/widgets/<name>.js` |
| Recht | `permission` |

## Den alten Code ansehen

Der Code aus Block 1 (Service-Schicht, Alembic, vollständiges Datenmodell) wird nicht
weiterentwickelt, bleibt aber als Vorlage erhalten – im Branch `archiv/block1` und im Tag
`archiv-block1-2026-11`. So liegt er in einem zweiten Ordner neben diesem, ohne dass der
Arbeitsstand sich ändert:

```bash
git worktree add ../timbertalk-archiv archiv/block1
```

Wieder entfernen: `git worktree remove ../timbertalk-archiv`.
Das Datenmodell von damals ist zusätzlich als `docs/archiv/datenmodell-block1.md` abgelegt.
