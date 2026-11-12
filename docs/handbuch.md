# TimberTalk – Code-Handbuch

Dieses Handbuch erklärt den gesamten Code von TimberTalk so, dass jemand ohne Vorwissen über das
Projekt versteht, wie das Programm aufgebaut ist und was jede Datei tut. Es wächst mit jedem
Feature mit und beschreibt immer den **aktuellen** Stand des Arbeitszweigs – nicht Pläne und nicht
den alten Code aus Block 1.

> **Stand:** Feature F0 „Skelett“ · zuletzt aktualisiert am 2026-11-12

Wer nur wissen will, *was* ein Feature können soll, liest den Steckbrief in `docs/features/`.
Wer wissen will, *wie* der Code das umsetzt, liest hier.

---

## 1. Das Programm in einem Bild

```
┌──────────────────────────────────────────────────────────────┐
│  PC im Betrieb                                               │
│                                                              │
│   Browser ──fetch──►  Backend (FastAPI, uvicorn)  ──► SQLite  │
│   (frontend/)         /api/...                    backend/   │
│                       /  → liefert frontend/      data/      │
└──────────────────────────────────────────────────────────────┘
```

- **Backend** (`backend/timbertalk/`): ein Python-Programm. Es hält die Daten, enthält die
  Logik und bietet alles über eine API unter `/api` an. Es ist die einzige Quelle der Wahrheit.
- **Frontend** (`frontend/`): einfache HTML-, CSS- und JavaScript-Dateien. Sie holen ihre Daten
  ausschließlich über die API. Das Backend liefert diese Dateien gleich mit aus.
- **Datenbank**: eine SQLite-Datei, standardmäßig `backend/data/timbertalk.db`.

Spätere Oberflächen (Desktop-App, Smartphone-App) sind genauso nur Clients derselben API.

---

## 2. Was beim Start passiert

Befehl im Ordner `backend/`: `uv run timbertalk`

1. `uv` liest `backend/pyproject.toml`. Unter `[project.scripts]` steht
   `timbertalk = "timbertalk.main:run"` – also wird die Funktion `run()` in `main.py` aufgerufen.
2. `run()` liest die Einstellungen (`settings.py`): Adresse und Port, Standard `127.0.0.1:8000`.
3. `run()` stellt einen Zeitgeber, der nach einer Sekunde den Browser öffnet.
4. `run()` startet den Webserver `uvicorn` mit der FastAPI-App `app` aus `main.py`.
5. Beim Hochfahren der App läuft `lifespan()` in `main.py` und ruft `create_tables()` aus `db.py`.
   Dabei wird die Datenbankdatei angelegt (falls nötig) und fehlende Tabellen entstehen.
6. Der Browser lädt `/`. Das Backend liefert `frontend/index.html` aus.

---

## 3. Was bei einer Anfrage passiert

Beispiel: die Startseite zeigt den Zustand von Backend und Datenbank.

1. Der Browser lädt `index.html`, darin wird `app.js` als Modul geladen.
2. `app.js` holt die API-Adresse aus `config.js` (leer = dieselbe Adresse wie die Seite) und ruft
   `GET /api/health` auf.
3. FastAPI leitet die Anfrage an die Funktion `health()` in `main.py`.
4. `health()` fragt `database_ok()` in `db.py`. Diese Funktion schickt `SELECT 1` an die
   Datenbank und meldet `True` oder `False`.
5. Die Antwort `{"status": "ok", "database": "ok"}` geht als JSON zurück.
6. `app.js` schreibt „antwortet“ oder eine Fehlermeldung in die Seite.

So läuft später jede Anfrage: **Frontend → API → Service → Datenbank** und zurück.
Ab dem ersten echten Feature steht zwischen API und Datenbank die Service-Schicht (siehe
Abschnitt 6).

---

## 4. Ordner und Dateien

Nur Dateien, die im Repository liegen. Erzeugte Dinge (`.venv/`, `backend/data/`, Caches) stehen
in `.gitignore`.

### Hauptordner

| Datei / Ordner | Wofür |
| --- | --- |
| `CLAUDE.md` | Regeln für die Arbeit mit Claude Code – gelten aber genauso für Menschen. |
| `README.md` | Kurzer Einstieg: was TimberTalk ist und wie man es startet. |
| `.gitignore` | Was nicht ins Repository gehört (Datenbank, `.env`, virtuelle Umgebung, Caches). |
| `.github/workflows/backend.yml` | Automatische Prüfung des Backends bei jedem Pull Request (Abschnitt 8). |
| `.github/workflows/handbuch.yml` | Prüft bei jedem Pull Request, ob das Handbuch mitgepflegt wurde (Abschnitt 8). |
| `.github/pull_request_template.md` | Vorlage, die sich beim Öffnen eines Pull Requests füllt. |

### `backend/`

| Datei | Wofür |
| --- | --- |
| `pyproject.toml` | Paketbeschreibung: Abhängigkeiten, Startbefehl, Einstellungen für ruff und pytest. |
| `uv.lock` | Genau festgelegte Versionen aller Abhängigkeiten, damit jeder dasselbe installiert. |
| `.env.example` | Vorlage für eigene Einstellungen. Kopiert als `backend/.env` wird sie gelesen. |
| `timbertalk/__init__.py` | Markiert den Ordner als Python-Paket. Sonst leer. |
| `timbertalk/main.py` | Die App: FastAPI-Objekt, `/api/health`, Auslieferung des Frontends, `run()`. |
| `timbertalk/settings.py` | Einstellungen (Datenbankadresse, Host, Port) aus Umgebung oder `.env`. |
| `timbertalk/db.py` | Verbindung zur Datenbank, Anlegen der Tabellen, Gesundheitsprüfung. |
| `timbertalk/features/` | Hier entsteht je Feature ein eigener Ordner. Noch leer. |
| `tests/test_health.py` | Tests für `/api/health` und die Startseite. |

### `frontend/`

| Datei | Wofür |
| --- | --- |
| `index.html` | Die Startseite „TimberTalk läuft“ mit zwei Statusfeldern. |
| `app.js` | Holt `/api/health` und schreibt das Ergebnis in die Seite. |
| `config.js` | Die einzige Stelle mit der Adresse der API. |
| `style.css` | Ein paar Zeilen Gestaltung, damit die Seite lesbar ist. |

### `docs/`

| Datei / Ordner | Wofür |
| --- | --- |
| `handbuch.md` | Dieses Handbuch. |
| `features/_vorlage.md` | Vorlage für einen neuen Steckbrief. |
| `features/F00-skelett.md` | Steckbrief von F0. |
| `ki-nutzung.md` | Protokoll, welche Teile mit KI-Hilfe entstanden sind. |
| `archiv/` | Unterlagen aus Block 1, nur zum Nachschlagen. |

---

## 5. Das Backend im Detail

### `main.py` – die App

- **`app = FastAPI(...)`**: das zentrale Objekt. Alle Endpunkte hängen daran.
- **`lifespan()`**: läuft einmal beim Start (vor dem `yield`) und einmal beim Beenden (danach).
  Zurzeit legt es nur die Tabellen an.
- **`health()`** unter `GET /api/health`: meldet `status` und `database`. Er ist bewusst die
  einfachste Frage an das Programm und wird bei jedem Feature mitgetestet.
- **Frontend-Auslieferung**: `app.mount("/", StaticFiles(...))` liefert den Ordner `frontend/`
  unter `/` aus. Diese Zeile steht **nach** allen API-Endpunkten, weil FastAPI in Reihenfolge
  sucht – sonst würde `/api/health` als Datei im Frontend gesucht.
- **`run()`**: Startbefehl. Öffnet nach einer Sekunde den Browser und startet `uvicorn`.

### `settings.py` – die Einstellungen

- Die Klasse `Settings` erbt von `BaseSettings` (pydantic-settings). Jedes Feld hat einen
  Standardwert und kann über eine Umgebungsvariable mit dem Präfix `TIMBERTALK_` oder über die
  Datei `backend/.env` überschrieben werden. Beispiel: `TIMBERTALK_PORT=8080`.
- `BACKEND_DIR` und `DATA_DIR` werden vom Speicherort der Datei aus berechnet. Dadurch liegt die
  Datenbank immer am selben Platz, egal aus welchem Ordner der Server gestartet wird.
- `get_settings()` liest die Einstellungen nur einmal (`lru_cache`) und gibt danach immer
  dasselbe Objekt zurück.

| Einstellung | Umgebungsvariable | Standard |
| --- | --- | --- |
| `database_url` | `TIMBERTALK_DATABASE_URL` | `sqlite:///…/backend/data/timbertalk.db` |
| `host` | `TIMBERTALK_HOST` | `127.0.0.1` |
| `port` | `TIMBERTALK_PORT` | `8000` |

### `db.py` – die Datenbank

- **`get_engine()`**: baut die Verbindung zur Datenbank einmal auf und merkt sie sich. Bei SQLite
  wird vorher der Ordner `backend/data/` angelegt. `check_same_thread=False` ist nötig, weil der
  Webserver Anfragen in mehreren Threads beantwortet.
- **`create_tables()`**: legt alle Tabellen an, die als SQLModel-Klassen bekannt sind und noch
  fehlen. Bestehende Tabellen werden **nicht** verändert – dafür kommen mit F3 Migrationen.
- **`database_ok()`**: schickt `SELECT 1` und meldet, ob das klappt.

---

## 6. Wie ein Feature aufgebaut ist

Noch gibt es kein Feature-Modul. Sobald es eins gibt, sieht es so aus:

```
backend/timbertalk/features/<name>/
├── models.py          Tabellen als SQLModel-Klassen
├── service.py         die Logik, als einfache Funktionen
├── api.py             die Endpunkte unter /api/<name>
└── test_<name>.py     Tests für den Service und die Endpunkte
```

Der Weg einer Anfrage durch ein Feature:

```
api.py  ──ruft──►  service.py  ──liest/schreibt──►  models.py (Tabellen)
```

- **`api.py`** nimmt die Anfrage an, ruft eine Funktion aus `service.py` und gibt das Ergebnis
  zurück. Sonst nichts – keine Rechnungen, keine Datenbankabfragen.
- **`service.py`** enthält die eigentliche Logik. Dieselben Funktionen können später auch von
  anderen Stellen (z. B. dem Sprach-Agenten) aufgerufen werden.
- **Geld und Mengen** sind immer `Decimal`, nie `float`.

*Sobald das erste Feature existiert, wird dieser Abschnitt durch eine Tabelle aller Features mit
ihren Endpunkten und Tabellen ergänzt (Abschnitt 10).*

---

## 7. Das Frontend im Detail

- **Ohne Bauschritt und ohne Framework**: Die Dateien werden genau so ausgeliefert, wie sie
  im Ordner liegen. Kein npm, kein Webpack.
- **`config.js`** exportiert `API_BASE`. Leer bedeutet: die API liegt auf derselben Adresse wie
  die Seite. Für eine andere Adresse (z. B. Backend auf einem anderen PC) wird nur diese eine
  Zeile geändert.
- **`app.js`** wird als ES-Modul geladen (`<script type="module">`), damit es `config.js` mit
  `import` einbinden kann. Es nutzt nur `fetch` und `textContent`.
- Kommt keine Antwort, zeigt die Seite „nicht erreichbar“ mit dem Grund statt einer leeren Seite.

---

## 8. Tests, Prüfungen und CI

Alle Befehle laufen im Ordner `backend/`.

| Befehl | Was er prüft |
| --- | --- |
| `uv run pytest` | Die Tests. |
| `uv run ruff check .` | Lint: typische Fehler und unsaubere Stellen. |
| `uv run ruff format --check .` | Ob der Code einheitlich formatiert ist. |

- **Tests mit Datenbank im Speicher**: `tests/test_health.py` setzt vor dem Import der App
  `TIMBERTALK_DATABASE_URL=sqlite://`. So entsteht bei Tests keine Datei auf der Platte.
- **`TestClient`** aus FastAPI spielt einen Browser nach, ohne einen echten Server zu starten.
  Mit `with TestClient(app)` läuft auch `lifespan()`, die Tabellen werden also angelegt.
- **CI** (`.github/workflows/backend.yml`): Bei jedem Pull Request und jedem Push auf `main`,
  der etwas unter `backend/` ändert, laufen auf GitHub dieselben drei Prüfungen.
  `uv sync --locked` sorgt dafür, dass genau die Versionen aus `uv.lock` installiert werden.
- **Handbuch-Prüfung** (`.github/workflows/handbuch.yml`): Ändert ein Pull Request etwas unter
  `backend/` oder `frontend/`, aber nicht `docs/handbuch.md`, schlägt die Prüfung fehl. Hat das
  Handbuch wirklich nichts Neues zu sagen, setzt man am Pull Request das Label
  `handbuch-unveraendert` – dann wird die Prüfung übersprungen.

---

## 9. Werkzeuge

| Werkzeug | Wofür |
| --- | --- |
| Python 3.12 | Sprache des Backends. |
| `uv` | Installiert Python-Pakete und führt Befehle in der richtigen Umgebung aus. |
| FastAPI | Baut die API: Endpunkte, JSON, Prüfung der Eingaben. |
| uvicorn | Der Webserver, der FastAPI ausführt. |
| SQLModel | Tabellen als Python-Klassen; baut auf SQLAlchemy und pydantic auf. |
| pydantic-settings | Liest Einstellungen aus Umgebung und `.env`. |
| pytest, httpx | Tests; httpx braucht der `TestClient`. |
| ruff | Lint und Formatierung. |

---

## 10. Features im Überblick

| Nr. | Name | Steckbrief | Neue Endpunkte | Neue Tabellen |
| --- | --- | --- | --- | --- |
| F0 | Skelett | `docs/features/F00-skelett.md` | `GET /api/health` | – |

---

## 11. Begriffe

| Begriff | Bedeutung |
| --- | --- |
| API | Die Schnittstelle des Backends unter `/api`. Alle Oberflächen reden nur über sie. |
| Endpunkt | Eine Adresse der API mit Methode, z. B. `GET /api/health`. |
| Service | Die Funktionen in `service.py`, in denen die Logik steht. |
| Steckbrief | Kurze Beschreibung eines Features in `docs/features/`: Ziel, Abnahme, Abgrenzung. |
| Lifespan | Code, der beim Start und beim Beenden der App einmal läuft. |
| Migration | Schrittweise Änderung bestehender Tabellen. Kommt mit F3. |
| CI | Automatische Prüfung auf GitHub bei jedem Pull Request. |

Fachbegriffe und ihre Namen im Code (Kunde → `customer` usw.) stehen im Glossar der `README.md`.

---

## 12. Wie dieses Handbuch gepflegt wird

Das Handbuch wird **im selben Commit** angepasst wie der Code, den es beschreibt. Ein Pull
Request ohne passende Änderung hier ist nicht fertig – die CI-Prüfung `Handbuch` meldet das
(Abschnitt 8).

Bei jeder Änderung prüfen:

1. **Neue, verschobene oder gelöschte Datei?** → Tabelle in Abschnitt 4.
2. **Neues Feature?** → Zeile in Abschnitt 10, Abschnitt 6 bei Bedarf ergänzen, eigener
   Unterabschnitt mit dem Weg einer typischen Anfrage durch das Feature.
3. **Start, Einstellungen oder Datenbank geändert?** → Abschnitte 2, 5 und die Tabelle der
   Einstellungen.
4. **Neues Werkzeug oder neue Abhängigkeit?** → Abschnitt 9.
5. **Neuer Begriff?** → Abschnitt 11.
6. **Stand-Zeile** oben auf das aktuelle Feature und Datum setzen.

Grundsätze: Es steht nur drin, was es im Code wirklich gibt. Falsches wird korrigiert, nicht
ergänzt. Erklärt wird in einfachem Deutsch, Bezeichner aus dem Code bleiben in `Code-Schrift`.
