# TimberTalk – Code-Handbuch

Dieses Handbuch erklärt den gesamten Code von TimberTalk so, dass jemand ohne Vorwissen über das
Projekt versteht, wie das Programm aufgebaut ist und was jede Datei tut. Es wächst mit jedem
Feature mit und beschreibt immer den **aktuellen** Stand des Arbeitszweigs – nicht Pläne und nicht
den alten Code aus Block 1.

> **Stand:** Feature F0d „Grundlagen für parallele Features“ · zuletzt aktualisiert am 2026-11-20

Wer nur wissen will, *was* ein Feature können soll, liest den Steckbrief in `docs/features/`.
Wer wissen will, *wie* der Code das umsetzt, liest hier – und für jedes fachliche Feature dessen
eigenes Kapitel unter `docs/handbuch/` (Abschnitt 10).

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
4. `run()` startet den Webserver `uvicorn` mit der FastAPI-App `app` aus `main.py`. Beim Laden
   von `main.py` ruft `load_features()` jeden Feature-Ordner unter `features/` auf: Es lädt
   dessen `models.py` (Tabellen) und hängt den `router` aus dessen `api.py` an die App (Abschnitt 5).
5. Beim Hochfahren der App läuft `lifespan()` in `main.py` und ruft `create_tables()` aus `db.py`.
   Dabei wird die Datenbankdatei angelegt (falls nötig) und fehlende Tabellen entstehen.
6. Der Browser lädt `/`. Das Backend liefert `frontend/index.html` aus; `app.js` baut daraus mit
   der Liste in `reiter.js` die Reiterleiste und zeigt den Reiter „Start“ (Abschnitt 7).

---

## 3. Was bei einer Anfrage passiert

Beispiel: der Reiter „Start“ zeigt den Zustand von Backend und Datenbank.

1. Der Browser lädt `index.html`, darin wird `app.js` als Modul geladen. `app.js` lädt über
   `reiter.js` alle Reiter-Dateien und ruft beim ersten Öffnen von „Start“ `render()` in
   `features/start/start.js` auf.
2. `start.js` ruft `getJson("/api/health")` aus `shared/api.js` auf. `api.js` holt die
   API-Adresse aus `config.js` (leer = dieselbe Adresse wie die Seite) und fragt
   `GET /api/health`.
3. FastAPI leitet die Anfrage an die Funktion `health()` in `main.py`.
4. `health()` fragt `database_ok()` in `db.py`. Diese Funktion schickt `SELECT 1` an die
   Datenbank und meldet `True` oder `False`.
5. Die Antwort `{"status": "ok", "database": "ok"}` geht als JSON zurück.
6. `start.js` schreibt „antwortet“ oder eine Fehlermeldung in die Seite.

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
| `timbertalk/db.py` | Verbindung zur Datenbank, Sitzung je Anfrage (`get_session`), Anlegen der Tabellen, Gesundheitsprüfung. |
| `timbertalk/features/__init__.py` | Findet die Feature-Ordner selbst und lädt ihre Tabellen und Router (`load_features()`). |
| `timbertalk/features/<name>/` | Je Feature ein eigener Ordner (Abschnitt 6). Noch keiner vorhanden. |
| `conftest.py` | Gemeinsame Test-Hilfen (Fixtures) `engine`, `session` und `client` für alle Tests. |
| `tests/test_health.py` | Tests für `/api/health`, das Gerüst der Startseite und dass jeder Reiter-Ordner in `reiter.js` steht. |
| `tests/test_grundlagen.py` | Tests für die Datenbank im Arbeitsspeicher und für `load_features()`. |

### `frontend/`

| Datei | Wofür |
| --- | --- |
| `index.html` | Die einzige Seite – nur das Gerüst: leere Reiterleiste `<nav class="tabs">` und leeres `<main>`. |
| `app.js` | Baut aus `reiter.js` je Reiter einen Link und einen Bereich, schaltet die Reiter um und ruft beim ersten Öffnen `render()` des Reiters auf. |
| `reiter.js` | Liste aller Reiter in der Reihenfolge der Leiste. |
| `config.js` | Die einzige Stelle mit der Adresse der API. |
| `shared/api.js` | `getJson(path)`: der gemeinsame Weg aller Reiter zur API. |
| `features/start/start.js` | Reiter „Start“: Überschrift „Übersicht“, „TimberTalk läuft“ und der Status von Backend und Datenbank. |
| `features/kalender/kalender.js` | Reiter „Kalender“, noch leer. |
| `features/projekte/projekte.js` | Reiter „Projekte“, noch leer. |
| `features/kunden/kunden.js` | Reiter „Kunden“, noch leer. |
| `features/buchungen/buchungen.js` | Reiter „Buchungen“, noch leer. |
| `features/einstellungen/einstellungen.js` | Reiter „Einstellungen“, noch leer. |
| `style.css` | Gestaltung: Farben als Variablen für hell, dunkel und erhöhten Kontrast, Reiterleiste, Bereiche, Statuskasten. |

### `docs/`

| Datei / Ordner | Wofür |
| --- | --- |
| `handbuch.md` | Dieses Handbuch: das Grundgerüst. |
| `handbuch/_vorlage.md` | Vorlage für das Handbuch-Kapitel eines Features. |
| `handbuch/F<nr>-<name>.md` | Je fachliches Feature ein Kapitel. Noch keines vorhanden. |
| `features/_vorlage.md` | Vorlage für einen neuen Steckbrief. |
| `features/F00-skelett.md` | Steckbrief von F0. |
| `features/F00b-reiter.md` | Steckbrief von F0b. |
| `features/F00c-reiter-module.md` | Steckbrief von F0c. |
| `features/F00d-parallele-features.md` | Steckbrief von F0d. |
| `ki-nutzung.md` | Protokoll, welche Teile mit KI-Hilfe entstanden sind – Stand bis 2026-11-20, wird nicht mehr ergänzt. |
| `ki-nutzung/<datum>-<thema>.md` | Neue Einträge im KI-Protokoll, eine Datei je Änderung. |
| `archiv/` | Unterlagen aus Block 1, nur zum Nachschlagen. |

---

## 5. Das Backend im Detail

### `main.py` – die App

- **`app = FastAPI(...)`**: das zentrale Objekt. Alle Endpunkte hängen daran.
- **`lifespan()`**: läuft einmal beim Start (vor dem `yield`) und einmal beim Beenden (danach).
  Zurzeit legt es nur die Tabellen an.
- **`health()`** unter `GET /api/health`: meldet `status` und `database`. Er ist bewusst die
  einfachste Frage an das Programm und wird bei jedem Feature mitgetestet.
- **Features einbinden**: `for router in load_features(): app.include_router(router)`. Jedes
  Feature bringt seine Endpunkte als `router` in seiner `api.py` mit; `main.py` kennt die
  Features nicht mit Namen und wird für ein neues Feature nicht geändert.
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

Alle Features teilen sich **eine** Datenbank. Jedes Feature bringt eigene Tabellen mit.

- **`make_engine(database_url)`**: baut eine Verbindung zur Datenbank unter dieser Adresse. Bei
  SQLite wird vorher der Ordner `backend/data/` angelegt. `check_same_thread=False` ist nötig,
  weil der Webserver Anfragen in mehreren Threads beantwortet.
- **`IN_MEMORY_URL`** (`sqlite://`) bedeutet: Datenbank nur im Arbeitsspeicher, ohne Datei – so
  laufen die Tests. Dort hätte jede neue Verbindung eine eigene, leere Datenbank. Deshalb benutzt
  `make_engine()` dafür `StaticPool`: alle Verbindungen teilen sich eine und sehen dieselben Tabellen.
- **`get_engine()`**: die Verbindung aus den Einstellungen, einmal gebaut und danach gemerkt.
- **`get_session()`**: gibt einer Anfrage ihre Datenbank-Sitzung und schließt sie danach. Ein
  Endpunkt bekommt sie mit `session: Session = Depends(get_session)`. Die Tests tauschen genau
  diese Funktion gegen eine leere Datenbank aus (Abschnitt 8).
- **`create_tables()`**: legt alle Tabellen an, die als SQLModel-Klassen bekannt sind und noch
  fehlen. Bestehende Tabellen werden **nicht** verändert – dafür kommen mit F3 Migrationen.
- **`database_ok()`**: schickt `SELECT 1` und meldet, ob das klappt.

### `features/__init__.py` – Features finden

- **`feature_names()`**: alle Unterordner von `features/`, die eine `__init__.py` haben,
  alphabetisch. Ein Ordner ohne `__init__.py` ist kein Feature und wird übergangen.
- **`load_features()`**: importiert je Feature `models.py` und `api.py`, sofern es sie gibt.
  `models.py` muss geladen sein, bevor `create_tables()` läuft – sonst kennt SQLModel die Tabellen
  nicht. Aus `api.py` sammelt es das Objekt `router`. Fehlt `router`, bricht der Start mit einer
  klaren Meldung ab. Fehlt eine Datei, die `models.py` oder `api.py` selbst importiert, bleibt
  dieser Fehler sichtbar und wird nicht verschluckt.

---

## 6. Wie ein Feature aufgebaut ist

Noch gibt es kein fachliches Feature. Sobald es eins gibt, sieht es so aus:

```
backend/timbertalk/features/<name>/
├── __init__.py        leer – macht den Ordner zum Feature, das load_features() findet
├── models.py          Tabellen als SQLModel-Klassen
├── service.py         die Logik, als einfache Funktionen
├── api.py             router = APIRouter(prefix="/api/<name>") mit den Endpunkten
└── test_<name>.py     Tests für den Service und die Endpunkte

frontend/features/<id>/
└── <id>.js            der Reiter, der das Feature zeigt (Abschnitt 7)

docs/features/F<nr>-<name>.md    Steckbrief
docs/handbuch/F<nr>-<name>.md    Handbuch-Kapitel nach docs/handbuch/_vorlage.md
```

Ein neues Feature legt **nur neue Dateien** an. `main.py`, `db.py`, die Tests in `tests/` und
dieses Handbuch bleiben unverändert. Im Frontend kommt höchstens eine Zeile in `reiter.js` dazu,
wenn es einen ganz neuen Reiter braucht.

So sieht `api.py` im Kern aus:

```python
router = APIRouter(prefix="/api/kunden", tags=["kunden"])


@router.get("")
def list_customers(session: Session = Depends(get_session)) -> list[Customer]:
    return service.list_customers(session)
```

Backend und Reiter eines Features baut dieselbe Person, parallel zu den anderen Features. Der
Reiter-Ordner heißt wie der Reiter in der Adresse; welcher Reiter dazugehört, steht im Steckbrief
unter „Reiter“.

Der Weg einer Anfrage durch ein Feature:

```
<id>.js ──getJson──► api.py ──ruft──► service.py ──liest/schreibt──► models.py (Tabellen)
```

- **`api.py`** nimmt die Anfrage an, ruft eine Funktion aus `service.py` und gibt das Ergebnis
  zurück. Sonst nichts – keine Rechnungen, keine Datenbankabfragen.
- **`service.py`** enthält die eigentliche Logik. Dieselben Funktionen können später auch von
  anderen Stellen (z. B. dem Sprach-Agenten) aufgerufen werden.
- **Geld und Mengen** sind immer `Decimal`, nie `float`.
- **Andere Features** werden nur über deren `service.py` benutzt, nie über deren Tabellen oder
  `api.py`. Wer ein anderes Feature braucht, nennt das im eigenen Handbuch-Kapitel unter
  „Abhängigkeiten“.
- **Tests** (`test_<name>.py`) nennen die Fixtures aus `backend/conftest.py` als Parameter:
  `session` für Tests von `service.py`, `client` für Tests der Endpunkte (Abschnitt 8).

---

## 7. Das Frontend im Detail

- **Ohne Bauschritt und ohne Framework**: Die Dateien werden genau so ausgeliefert, wie sie
  im Ordner liegen. Kein npm, kein Webpack.
- **`config.js`** exportiert `API_BASE`. Leer bedeutet: die API liegt auf derselben Adresse wie
  die Seite. Für eine andere Adresse (z. B. Backend auf einem anderen PC) wird nur diese eine
  Zeile geändert.
- **ES-Module**: `app.js` wird mit `<script type="module">` geladen. Dadurch können alle Dateien
  einander mit `import` einbinden – ohne Bauschritt.
- **`shared/api.js`** enthält `getJson(path)`. Alle Reiter fragen die API darüber; antwortet sie
  mit einem Fehler, wirft `getJson` eine Ausnahme mit dem Statuscode.
- Kommt keine Antwort, zeigt „Start“ „nicht erreichbar“ mit dem Grund statt einer leeren Seite.
- **Daten aus der API** kommen mit `textContent` in die Seite, nie über `innerHTML`.
  `innerHTML` steht nur für festen Text aus der eigenen Datei (Regel in `CLAUDE.md`).

### Reiter

Die Oberfläche ist **eine** Seite (`index.html`), die nur das Gerüst enthält. Jeder Reiter ist
eine eigene Datei `features/<id>/<id>.js` – ein **Reiter-Modul**. So kann jede Person den Reiter
ihres Features bauen, ohne die Dateien der anderen anzufassen.

| Reiter | Adresse | Datei | Inhalt |
| --- | --- | --- | --- |
| Start | `/#start` (auch `/`) | `features/start/start.js` | Überschrift „Übersicht“, darunter „TimberTalk läuft“ und der Status von Backend und Datenbank |
| Kalender | `/#kalender` | `features/kalender/kalender.js` | noch leer – ein Satz sagt, was hier hinkommt |
| Projekte | `/#projekte` | `features/projekte/projekte.js` | noch leer – ein Satz sagt, was hier hinkommt |
| Kunden | `/#kunden` | `features/kunden/kunden.js` | noch leer – ein Satz sagt, was hier hinkommt |
| Buchungen | `/#buchungen` | `features/buchungen/buchungen.js` | noch leer – ein Satz sagt, was hier hinkommt |
| Einstellungen | `/#einstellungen` | `features/einstellungen/einstellungen.js` | noch leer – ein Satz sagt, was hier hinkommt |

Ein Reiter-Modul exportiert drei Dinge:

| Export | Bedeutung |
| --- | --- |
| `id` | Name hinter `#` in der Adresse und `id` des Bereichs, z. B. `"kunden"`. |
| `title` | Text in der Reiterleiste, z. B. `"Kunden"`. |
| `render(panel)` | Füllt den Bereich `panel` (ein `<section>`). Darf `async` sein. |

So entsteht die Seite:

1. `app.js` importiert `REITER` aus `reiter.js` und legt für jeden Eintrag einen Link
   `<a href="#<id>">` in der Leiste und einen leeren `<section id="<id>" class="panel" hidden>`
   in `<main>` an.
2. Wird ein Reiter zum ersten Mal gezeigt, ruft `renderOnce()` seine Funktion `render(panel)` auf.
   Danach bleibt der Inhalt stehen; beim nächsten Öffnen wird nichts neu aufgebaut.
3. Wirft `render()` einen Fehler, zeigt nur dieser Bereich „Dieser Bereich konnte nicht geladen
   werden“ mit dem Grund; der Fehler steht zusätzlich in der Browser-Konsole. Die anderen Reiter
   funktionieren weiter.

So funktioniert das Umschalten:

1. Jeder Reiter ist ein normaler Link auf `#<id>`. Ein Klick ändert nur den Teil hinter `#` in
   der Adresse; die Seite wird nicht neu geladen und der Server wird nicht gefragt.
2. Der Browser meldet die Änderung mit dem Ereignis `hashchange` – auch bei Zurück und Vor.
3. `showTabFromAddress()` in `app.js` liest den Namen hinter `#`, blendet den `<section>` mit
   dieser `id` ein und alle anderen aus (Attribut `hidden`) und ruft `renderOnce()` für ihn auf.
   Den passenden Link markiert es mit `aria-current="page"`; `style.css` hebt ihn darüber hervor.
4. Ist der Name leer oder unbekannt, wird der Reiter `start` gezeigt.

Weil der Reiter in der Adresse steht, öffnen Neu laden und Lesezeichen denselben Bereich.

**Einen bestehenden Reiter füllen:** nur die eigene Datei `features/<id>/<id>.js` ändern.

**Einen neuen Reiter ergänzen:**

1. Ordner `features/<id>/` mit der Datei `<id>.js` anlegen – am einfachsten eine leere Datei wie
   `kunden.js` kopieren und `id`, `title` und Text anpassen.
2. In `reiter.js` eine `import`-Zeile und einen Eintrag in `REITER` ergänzen. Die Reihenfolge in
   `REITER` ist die Reihenfolge in der Leiste.
`index.html`, `app.js` und die Tests werden dafür nicht geändert – der Test liest die Reiter
selbst aus den Ordnern unter `frontend/features/` und prüft, dass jeder in `reiter.js` steht.

**Eigene CSS-Klassen** eines Reiters beginnen mit `<id>-` (z. B. `kunden-liste`) und stehen in
`style.css`. Eine eigene CSS-Datei je Reiter gibt es noch nicht.

### Farben, hell und dunkel

Alle Farben stehen als CSS-Variablen (`--text`, `--muted`, `--page`, `--card`, `--line`,
`--accent`) oben in `style.css`. Der Rest der Datei benutzt nur diese Variablen, nie feste Werte.

- **Hell oder dunkel** richtet sich nach der Einstellung des Betriebssystems. Der Block
  `@media (prefers-color-scheme: dark)` belegt die Variablen dafür neu. Einen eigenen Schalter in
  TimberTalk gibt es bewusst nicht (Vorgabe aus dem Skill `apple-design`, `dark-mode.md`).
- **Erhöhter Kontrast** (`@media (prefers-contrast: more)`) macht Grautöne und Rahmen kräftiger,
  für hell und dunkel getrennt.
- Hinter jeder Textfarbe steht im Kommentar ihr Kontrast zum Hintergrund. Untergrenze ist 4,5:1.
  Wer eine Farbe ändert, rechnet den Wert neu aus und trägt ihn ein.

---

## 8. Tests, Prüfungen und CI

Alle Befehle laufen im Ordner `backend/`.

| Befehl | Was er prüft |
| --- | --- |
| `uv run pytest` | Die Tests. |
| `uv run ruff check .` | Lint: typische Fehler und unsaubere Stellen. |
| `uv run ruff format --check .` | Ob der Code einheitlich formatiert ist. |

- **Wo Tests liegen**: in `tests/` (Grundgerüst) und neben jedem Feature in
  `timbertalk/features/<name>/test_<name>.py`. Beide Orte stehen in `pyproject.toml` unter
  `testpaths`; `uv run pytest` findet sie ohne weitere Angabe.
- **`backend/conftest.py`** lädt pytest von selbst, für alle Tests. Es setzt als Erstes
  `TIMBERTALK_DATABASE_URL=sqlite://`, damit Tests nie die echte Datei berühren, und stellt drei
  **Fixtures** bereit. Ein Test bekommt eine Fixture, indem er ihren Namen als Parameter nennt:

  | Fixture | Was der Test bekommt |
  | --- | --- |
  | `engine` | Eine frische, leere Datenbank im Arbeitsspeicher – für jeden Test eine neue. |
  | `session` | Eine Sitzung auf dieser Datenbank, zum Testen von `service.py`. |
  | `client` | Einen `TestClient`, dessen Anfragen alle diese Datenbank benutzen. |

- **`TestClient`** aus FastAPI spielt einen Browser nach, ohne einen echten Server zu starten.
  `client` tauscht dafür `get_session` über `app.dependency_overrides` aus und setzt es nach dem
  Test zurück.
- **Frontend in den Tests**: Die Tests holen `index.html`, `reiter.js` und jede Reiter-Datei
  über den `TestClient`. Die Reiter werden nicht aufgezählt, sondern aus den Ordnern unter
  `frontend/features/` gelesen: Jeder Ordner muss in `reiter.js` stehen und eine Datei
  `<id>.js` haben, die genau diese `id` exportiert. Das Verhalten im Browser selbst wird im Meeting
  vorgeführt (Abnahme im Steckbrief).
- **CI** (`.github/workflows/backend.yml`): Bei jedem Pull Request und jedem Push auf `main`,
  der etwas unter `backend/` oder `frontend/` ändert, laufen auf GitHub dieselben drei Prüfungen.
  `uv sync --locked` sorgt dafür, dass genau die Versionen aus `uv.lock` installiert werden.
- **Handbuch-Prüfung** (`.github/workflows/handbuch.yml`): Ändert ein Pull Request etwas unter
  `backend/` oder `frontend/`, aber weder `docs/handbuch.md` noch eine Datei unter
  `docs/handbuch/`, schlägt die Prüfung fehl. Hat das
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
| Skill `apple-design` | Gestaltungsmaßstab für alle Oberflächen (Apple Human Interface Guidelines) für Claude Code. Nicht im Repository; Installation und festgelegter Commit stehen in `CLAUDE.md` unter „Gestaltung der Oberflächen“. |

---

## 10. Features im Überblick

**Grundgerüst** – in diesem Handbuch beschrieben:

| Nr. | Name | Steckbrief | Neue Endpunkte | Neue Tabellen |
| --- | --- | --- | --- | --- |
| F0 | Skelett | `docs/features/F00-skelett.md` | `GET /api/health` | – |
| F0b | Reiter für die Funktionsbereiche | `docs/features/F00b-reiter.md` | – | – |
| F0c | Ein Modul je Reiter | `docs/features/F00c-reiter-module.md` | – | – |
| F0d | Grundlagen für parallele Features | `docs/features/F00d-parallele-features.md` | – | – |

**Fachliche Features** – jedes hat sein eigenes Kapitel `docs/handbuch/F<nr>-<name>.md` mit
Dateien, Endpunkten, Tabellen und Abhängigkeiten. Sie werden hier bewusst **nicht** aufgezählt,
damit parallele Pull Requests nicht dieselbe Tabelle ändern. Die Liste ist der Ordner selbst.
Noch gibt es keines.

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
| Dunkelmodus | Dunkle Darstellung, die das Betriebssystem einschaltet. Die Seite folgt ihr über `prefers-color-scheme`. |
| Fixture | Eine Test-Hilfe aus `backend/conftest.py` (`engine`, `session`, `client`). Ein Test bekommt sie, indem er ihren Namen als Parameter nennt. |
| Handbuch-Kapitel | Die Datei `docs/handbuch/F<nr>-<name>.md` eines Features: wie sein Code aufgebaut ist. |
| Router | Das Objekt `router` in der `api.py` eines Features. Es sammelt dessen Endpunkte; `load_features()` hängt es an die App. |
| Sitzung | Eine Verbindung zur Datenbank für die Dauer einer Anfrage (`Session`). Endpunkte bekommen sie über `get_session`. |
| Reiter | Ein Bereich der Oberfläche (Start, Kalender …), erreichbar über die Leiste oben und die Adresse `/#<id>`. |
| Reiter-Modul | Die Datei `frontend/features/<id>/<id>.js` eines Reiters. Exportiert `id`, `title` und `render(panel)`. |
| ES-Modul | JavaScript-Datei, die andere Dateien mit `import` einbindet. Der Browser lädt sie ohne Bauschritt. |

Fachbegriffe und ihre Namen im Code (Kunde → `customer` usw.) stehen im Glossar der `README.md`.

---

## 12. Wie dieses Handbuch gepflegt wird

Das Handbuch wird **im selben Commit** angepasst wie der Code, den es beschreibt. Ein
fachliches Feature pflegt dafür nur **sein eigenes Kapitel** unter `docs/handbuch/`; diese Datei
hier wird nur bei Änderungen am Grundgerüst angefasst. Ein Pull
Request ohne passende Änderung hier ist nicht fertig – die CI-Prüfung `Handbuch` meldet das
(Abschnitt 8).

Bei jeder Änderung prüfen:

1. **Neue, verschobene oder gelöschte Datei?** → Tabelle in Abschnitt 4.
2. **Neues fachliches Feature?** → eigenes Kapitel `docs/handbuch/F<nr>-<name>.md` nach
   `docs/handbuch/_vorlage.md`. Diese Datei bleibt unverändert.
   **Änderung am Grundgerüst?** → Zeile in Abschnitt 10 und die betroffenen Abschnitte hier.
3. **Start, Einstellungen oder Datenbank geändert?** → Abschnitte 2, 5 und die Tabelle der
   Einstellungen.
4. **Neues Werkzeug oder neue Abhängigkeit?** → Abschnitt 9.
5. **Neuer Begriff?** → Abschnitt 11.
6. **Stand-Zeile** oben auf das aktuelle Feature und Datum setzen.

Grundsätze: Es steht nur drin, was es im Code wirklich gibt. Falsches wird korrigiert, nicht
ergänzt. Erklärt wird in einfachem Deutsch, Bezeichner aus dem Code bleiben in `Code-Schrift`.
