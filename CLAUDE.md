# TimberTalk – Regeln für Claude Code

TimberTalk ist eine Betriebssoftware für Zimmereien: Kunden, Projekte und Buchungen von Stunden,
Material und Fahrten, später per Sprache erfasst. Das Backend läuft lokal auf dem PC im Betrieb,
alle Oberflächen sind nur Clients seiner API.

Wir bauen Feature für Feature. Jedes Feature wird im Meeting vorgeführt und gemeinsam
durchgesehen, deshalb zählt Verständlichkeit mehr als Eleganz.

## Ordner

```
backend/timbertalk/     Backend: main.py (App), settings.py, db.py, features/
backend/tests/          Tests
frontend/               HTML, CSS, JavaScript – ohne Bauschritt und ohne Framework
docs/handbuch.md        Code-Handbuch: erklärt die gesamte Codebasis
docs/features/          Ein Steckbrief je Feature, dazu _vorlage.md
docs/archiv/            Unterlagen aus Block 1
```

## Die drei Regeln

1. **Die API ruft nur den Service auf.** Die Logik steht in `service.py` als Funktionen.
   `api.py` nimmt die Anfrage an, ruft eine Funktion und gibt das Ergebnis zurück – sonst nichts.
2. **Geld und Mengen sind `Decimal`, nie `float`.** Sonst stimmen die Summen nicht.
3. **Kein Feature ohne Test und Steckbrief.** Der Steckbrief liegt in `docs/features/`,
   der Test neben dem Feature.

## So sieht ein Feature aus

```
backend/timbertalk/features/<name>/
├── models.py          Tabellen als SQLModel-Klassen
├── service.py         die Logik, als einfache Funktionen
├── api.py             die Endpunkte unter /api/<name>
└── test_<name>.py     Tests für den Service und die Endpunkte
```

Jede Datei beginnt mit einem Kommentar in einfachem Deutsch: wofür sie da ist.
Bezeichner im Code auf Englisch, Kommentare und Doku auf Deutsch.

## Gestaltung der Oberflächen

Alles, was man sieht – heute `frontend/`, später Desktop- und Smartphone-App –, richtet sich nach
den Human Interface Guidelines von Apple. Maßstab ist der Skill **`apple-design`**, festgelegt auf
Commit `91e15664896f6f27e75dcf1414d1226cb95fa167` von
<https://github.com/dickwu/apple-design-skill>.

- **Vor der Arbeit:** Bei jeder Änderung an Aussehen, Aufbau oder Bedienung einer Oberfläche den
  Skill `apple-design` laden und die passenden Seiten unter `references/hig/` lesen – nicht aus
  dem Gedächtnis arbeiten. Für HTML/CSS/JavaScript gilt die Übersetzung in
  `references/cross-platform.md` (Spalten Tauri/Electron, also Web-Technik).
- **Nach der Arbeit:** Die geänderte Oberfläche mit dem Skill durchsehen (Screenshot im Browser
  und Code), Befunde beheben oder im Pull Request begründen, warum nicht.
- **Im Pull Request** unter „Was ist neu zu verstehen?“ die herangezogenen Seiten nennen,
  z. B. `tab-bars.md › Best practices`.
- Der Steckbrief bestimmt, *was* gebaut wird; der Skill bestimmt, *wie es aussieht*. Er ist kein
  Anlass, Bereiche zu bauen, die nicht im Steckbrief stehen.

Der Skill gehört nicht ins Repository (keine Lizenz). Jeder installiert ihn einmal selbst:

```bash
git clone https://github.com/dickwu/apple-design-skill ~/.claude/skills/apple-design
git -C ~/.claude/skills/apple-design checkout 91e15664896f6f27e75dcf1414d1226cb95fa167
```

Ein neuerer Stand des Skills wird bewusst übernommen: Commit hier ändern, Oberfläche neu durchsehen.

## Technik

Python 3.12 mit `uv`, FastAPI, SQLModel, pydantic-settings, pytest, ruff.
Kein mypy, keine Repository-Schicht, kein Streamlit. Tabellen entstehen vorerst beim Start
über `SQLModel.metadata.create_all`; Migrationen kommen mit Feature F3.

## Befehle (im Ordner `backend/`)

```bash
uv sync                        # Abhängigkeiten installieren
uv run timbertalk              # Server starten und Browser öffnen
uv run pytest                  # Tests
uv run ruff check .            # Lint
uv run ruff format .           # Format
```

Vor jedem Commit müssen `ruff check`, `ruff format --check` und `pytest` grün sein.
Ergänze nach einer Änderung eine Zeile in `docs/ki-nutzung.md`: Datum, Modell, Aufgabe.

## Code-Handbuch

`docs/handbuch.md` erklärt die gesamte Codebasis so, dass jemand ohne Vorwissen das Programm
versteht. Lies es zu Beginn einer Aufgabe, um dich zu orientieren.

**Jede Änderung am Code aktualisiert das Handbuch im selben Commit** – neue Dateien, Features,
Endpunkte, Tabellen, Einstellungen, Werkzeuge und Begriffe. Was nicht mehr stimmt, wird
korrigiert oder gelöscht. Es beschreibt nur, was im Code wirklich existiert. Die Checkliste
dafür steht im Handbuch selbst in Abschnitt 12.

**Baue nur, was im Steckbrief steht. Keine Vorarbeit für spätere Features.**
