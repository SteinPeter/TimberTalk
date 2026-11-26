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
frontend/features/      ein Ordner je Reiter mit der Datei <id>.js
docs/handbuch.md        Code-Handbuch: erklärt das Grundgerüst
docs/handbuch/          ein Handbuch-Kapitel je Feature, dazu _vorlage.md
docs/ki-nutzung/        KI-Protokoll: eine Datei je Änderung
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
├── __init__.py        leer – macht den Ordner zum Feature, das automatisch geladen wird
├── models.py          Tabellen als SQLModel-Klassen
├── service.py         die Logik, als einfache Funktionen
├── api.py             router = APIRouter(prefix="/api/<name>") mit den Endpunkten
└── test_<name>.py     Tests für den Service und die Endpunkte

frontend/features/<id>/
└── <id>.js            der Reiter: exportiert id, title und render(panel)

docs/features/F<nr>-<name>.md    Steckbrief: was das Feature kann
docs/handbuch/F<nr>-<name>.md    Handbuch-Kapitel: wie der Code es umsetzt (_vorlage.md)
```

Ein neues Feature legt **nur neue Dateien** an. Gemeinsame Dateien im Backend werden dafür nicht
geändert:

- Das Feature trägt sich nirgends ein. `load_features()` findet jeden Ordner mit `__init__.py`,
  lädt `models.py` (Tabellen) und hängt den `router` aus `api.py` an die App.
- Endpunkte holen ihre Datenbank-Sitzung mit `session: Session = Depends(get_session)` aus
  `timbertalk.db` – nie selbst eine Verbindung bauen.
- Tests benutzen die Fixtures aus `backend/conftest.py`: `session` für `service.py`, `client` für
  `api.py`. Jeder Test bekommt eine leere Datenbank. `client` ist als Admin angemeldet;
  `client_as("journeyman")` gibt einen Browser mit einer anderen Rolle.
- Jeder Endpunkt verlangt eine Anmeldung (`main.py`). Braucht er ein Recht, steht es im Endpunkt:
  `Depends(require("finance.view"))` aus `features/accounts/deps.py`; neue Rechte stehen in
  `features/accounts/permissions.py` (F10).
- Ein Dashboard-Widget ist eine Datei `frontend/features/<ordner>/widgets/<name>.js` im eigenen
  Ordner (Bauplan oben in `frontend/features/start/start.js`); es wird nirgends eingetragen (F12).
- Jeder ändernde Endpunkt (POST, PUT, DELETE) bekommt `summary="…"` – das ist sein Name im
  Änderungsprotokoll (F11).
- Andere Features werden nur über deren `service.py` benutzt, nie über deren Tabellen oder
  `api.py`. So kann jede Person ihr Feature intern umbauen, ohne andere zu brechen.

Backend und Reiter eines Features baut **dieselbe Person** – parallel zu den anderen Features.
Der Reiter-Ordner heißt wie der Reiter in der Adresse (`#customers` → `frontend/features/customers/`);
welcher Reiter zu einem Feature gehört, steht im Steckbrief unter „Reiter“.

Im Frontend arbeitet ein Feature nur in seinem eigenen Ordner. Gemeinsame Dateien werden nur
dafür angefasst:

- `frontend/reiter.js` – eine Zeile, wenn ein ganz neuer Reiter dazukommt.
- `frontend/features/settings/` und `frontend/features/bookings/` – gemeinsame Reiter: Ein Feature
  legt dort nur eine eigene Datei `sections/<feature>.js` (oder `<feature>-<thema>.js`) an und
  trägt sie mit einer Zeile in `sections.js` ein (F0e).
- `frontend/shared/api.js` – alle Abfragen an die API laufen über `getJson()`.
- `frontend/style.css` – das gemeinsame Aussehen. Eigene CSS-Klassen eines Reiters beginnen mit
  `<id>-`, z. B. `customers-list`, damit sie sich nicht mit anderen Reitern überschneiden.

Daten aus der API kommen mit `textContent` in die Seite, nie über `innerHTML` – sonst könnte ein
Kundenname wie `<b>` die Seite verändern. `innerHTML` nur für festen Text aus der eigenen Datei.

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
Lege nach einer Änderung eine Datei `docs/ki-nutzung/<datum>-<thema>.md` an: eine Tabelle
mit Datum, Modell, Aufgabe. Die alte Sammeldatei `docs/ki-nutzung.md` wird nicht mehr ergänzt.

## Code-Handbuch

`docs/handbuch.md` erklärt die gesamte Codebasis so, dass jemand ohne Vorwissen das Programm
versteht. Lies es zu Beginn einer Aufgabe, um dich zu orientieren.

Ein fachliches Feature schreibt sein **eigenes Kapitel** `docs/handbuch/F<nr>-<name>.md` nach
`docs/handbuch/_vorlage.md`; `docs/handbuch.md` wird nur bei Änderungen am Grundgerüst angefasst.

**Jede Änderung am Code aktualisiert das Handbuch im selben Commit** – neue Dateien, Features,
Endpunkte, Tabellen, Einstellungen, Werkzeuge und Begriffe. Was nicht mehr stimmt, wird
korrigiert oder gelöscht. Es beschreibt nur, was im Code wirklich existiert. Die Checkliste
dafür steht im Handbuch selbst in Abschnitt 12.

**Baue nur, was im Steckbrief steht. Keine Vorarbeit für spätere Features.**
