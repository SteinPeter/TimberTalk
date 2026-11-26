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

Der Server läuft dann auf <http://127.0.0.1:8000> und der Browser öffnet sich mit der Anmeldung.
Beim allerersten Start gibt es ein Konto: Anmeldename `admin`, Passwort `admin`. Bei der ersten
Anmeldung muss man ein eigenes Passwort festlegen; danach legt man in „Einstellungen →
Benutzerkonten“ die Konten für den Betrieb an.

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
| Rolle (Admin, Meister, Verwaltung, Geselle) | `role` (`admin`, `master`, `office`, `journeyman`) |
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
