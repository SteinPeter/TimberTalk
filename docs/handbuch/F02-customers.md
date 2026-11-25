# F2 – Kunden (Handbuch-Kapitel)

> **Steckbrief:** `docs/features/F02-customers.md` · **Pate:** noch mit Peter/Anton zu klären · **Stand:** 2026-11-25
> (Tabelle, Service, Endpunkte, Demo-Datensatz und S-11-Vorbereitung mit Tests; Reiter mit
> Formularen und Dialogen, Speichern ausgeschaltet; Registrierung der KI-Werkzeuge folgt)

## Dateien

| Datei | Wofür |
| --- | --- |
| `backend/timbertalk/features/customers/models.py` | Tabelle `Customer`; Eingaben `CustomerInput` (Anlegen) und `CustomerUpdate` (Ändern) mit Kundenart und Höchstlängen; Antwort `CustomerRead` (ohne `search_text`) |
| `backend/timbertalk/features/customers/service.py` | Prüfen, Anlegen, Lesen, Suchen, Bearbeiten, Archivieren, Wiederherstellen, Löschen, CSV-Export; Fehler `CustomerError` |
| `backend/timbertalk/features/customers/api.py` | Endpunkte unter `/api/customers`; übersetzt `CustomerError` in HTTP-Statuscodes |
| `backend/timbertalk/features/customers/demo.py` | Demo-Datensatz (LD-09): zehn erfundene Kunden, `load_demo_customers()` und Befehl zum Laden in eine eigene Datei |
| `backend/timbertalk/features/customers/tools.py` | S-11-Vorbereitung: übersetzt Werkzeug-Eingaben auf den Service, prüft ohne Speichern; kein Katalog, keine Registrierung |
| `backend/timbertalk/features/customers/test_customers.py` | Tests für Service, Endpunkte, Demo-Datensatz, Export und `tools.py` mit erfundenen Daten; Regelprüfungen am Quelltext von `customers.js` (nur `getJson`, `innerHTML` nur fest, Schreiben aus, Längen und Pflicht wie im Backend) |
| `frontend/features/customers/customers.js` | Reiter „Kunden“: Liste mit Suche, Schalter „Archivierte zeigen“, Kundendaten, CSV-Link; Formular Anlegen/Bearbeiten, Dialoge Archivieren/Wiederherstellen/Löschen; Speichern über `sendChange()`, ausgeschaltet |

## Der Reiter

Abfragen laufen laut `CLAUDE.md` nur über `getJson()` aus `shared/api.js`, und das kann bisher nur
GET (Steckbrief D6). Lesen funktioniert deshalb vollständig; **Speichern ist ausgeschaltet**
(`WRITE_ENABLED = false`). Eigene CSS-Klassen gibt es noch nicht; der Reiter benutzt nur `hint`,
`empty`, `status` und Standard-Elemente des Browsers (`<details>`, `<dialog>`, `<fieldset>`).

- **Liste:** `GET /api/customers` über `getJson()`. Jeder Kunde ist ein `<details>`: die Zeile
  zeigt Name und Ort, aufgeklappt die Daten als `<dl class="status">` und die Aktionen.
- **Suche:** sucht 250 ms nach dem letzten Tastendruck (`SEARCH_DELAY`). Jede Suche hat eine
  Nummer; eine verspätete ältere Antwort wird verworfen.
- **Export:** ein normaler Link mit `download` auf `/api/customers/export.csv` (mit `API_BASE` aus
  `config.js`). Der Browser lädt die Datei; das ist keine `fetch`-Abfrage.
- **Felder:** `FIELDS` sagt je Feld: Beschriftung, Kundenart (`types`), Pflicht (`required`) und
  Höchstlänge (`max`, wie in `models.py`). Anzeige, Formular und Prüfung nutzen dieselbe Liste.
- **Formular** (`openCustomerForm`): ein `<dialog>` mit Kundenart als Auswahl (Privatkunde/Firma);
  es zeigt nur die Felder dieser Art. `validateCustomer()` prüft bei jeder Eingabe; Meldungen
  erscheinen unter dem Feld, sobald jemand hineingetippt oder „Speichern“ versucht hat. Solange
  etwas fehlt, ist der Knopf gesperrt. Esc oder „Abbrechen“ schließt ohne Änderung.
- **Dialoge** (`openConfirmDialog`): Archivieren und Wiederherstellen fragen einmal nach;
  „Endgültig löschen“ (nur bei archivierten Kunden) braucht zusätzlich das Häkchen
  „Ja, ich möchte diesen Kunden endgültig löschen.“. „Abbrechen“ hat jeweils den Fokus.
- **Schreiben** (`sendChange(action, id, body)`): der einzige Weg für Änderungen. Methode und
  Adresse stehen in `ACTIONS`. Ist `WRITE_ENABLED` aus, wirft die Funktion sofort einen Fehler –
  es geht keine Abfrage hinaus. Sonst prüft `confirmsChange()` die Antwort: Anlegen/Bearbeiten
  müssen jeden gesendeten Wert zurückgeben, Archivieren `archived: true`, Wiederherstellen
  `archived: false`, Löschen eine leere Antwort (204). Nur dann schließt der Dialog und oben
  erscheint „… wurde gespeichert/archiviert/…“. Sonst bleibt er offen mit einer Meldung aus
  `errorMessage()` (404, 409, 422, ausgeschaltet, unbestätigt).
- **Freischalten** nach Erweiterung von `shared/api.js` zu `getJson(path, options)`:
  `WRITE_ENABLED = true` setzen. Der Test `test_schreiben_bleibt_aus_solange_getjson_nur_get_kann`
  schlägt fehl, wenn jemand vorher umschaltet.
- `validateCustomer`, `confirmsChange` und `errorMessage` sind zusätzlich exportiert, damit sie
  sich im Browser prüfen lassen; `app.js` nutzt nur `id`, `title` und `render`.
- Alle Daten kommen mit `textContent` oder als `value` in die Seite; `innerHTML` steht nur einmal,
  für das feste Gerüst. Ein Name wie `<b>Test</b>` erscheint als Text.

## Endpunkte

| Methode und Adresse | Service-Funktion | Was sie tut |
| --- | --- | --- |
| `GET /api/customers?q=&include_archived=` | `list_customers()` | Liste und Suche, ohne archivierte |
| `GET /api/customers/export.csv?include_archived=` | `export_customers_csv()` | CSV-Datei `kunden.csv` zum Herunterladen |
| `GET /api/customers/{customer_id}` | `require_customer()` | Ein Kunde, auch archiviert |
| `POST /api/customers` | `create_customer()` | Anlegen → 201 |
| `PATCH /api/customers/{customer_id}` | `update_customer()` | Mitgeschickte Felder ändern |
| `POST /api/customers/{customer_id}/archive` | `archive_customer()` | Archivieren |
| `POST /api/customers/{customer_id}/restore` | `restore_customer()` | Wiederherstellen |
| `DELETE /api/customers/{customer_id}` | `delete_customer()` | Endgültig löschen, nur archivierte → 204 |

Fehler: `nicht_gefunden` → 404, `ungueltig` → 422, `nicht_archiviert` → 409, jeweils mit
`{"detail": {"code": …, "message": …}}`. Falsche Kundenart oder zu lange Texte → 422 von FastAPI.
`export.csv` steht in `api.py` vor `/{customer_id}`, damit es nicht als Kundennummer gilt.
Wegen `Depends(...)` im Parameter steht oben in `api.py` `# ruff: noqa: B008`.

## Service-Funktionen

| Funktion | Was sie tut |
| --- | --- |
| `check_customer_input(data)` | Entfernt Leerzeichen und prüft die Pflicht: Nachname (privat) bzw. Firmenname (Firma). Speichert nichts. |
| `create_customer(session, data)` | Prüft, bildet Anzeigename und Suchtext, speichert. |
| `get_customer(session, customer_id)` | Ein Kunde, auch archiviert; unbekannte Nummer → `None` (für andere Features). |
| `require_customer(session, customer_id)` | Wie `get_customer`, aber unbekannte Nummer → `CustomerError` `nicht_gefunden` (für die API). |
| `list_customers(session, query=None, include_archived=False)` | Kunden alphabetisch, ohne archivierte; `query` sucht wortweise im Suchtext. |
| `check_customer_update(session, customer_id, changes)` | Wie sähe der Kunde nach der Änderung aus? Prüft alles, speichert nichts (Vorschau). |
| `update_customer(session, customer_id, changes)` | Ändert nur mitgeschickte Felder: prüft über `check_customer_update`, speichert dann. |
| `archive_customer` / `restore_customer` | Setzt bzw. löscht das Kennzeichen `archived`. |
| `delete_customer(session, customer_id)` | Löscht endgültig – vorläufig nur archivierte Kunden. |
| `export_customers_csv(session, include_archived=False)` | CSV als Bytes: Semikolon, UTF-8 mit BOM, Spalten aus `EXPORT_COLUMNS`; `_safe_cell` setzt `'` vor Werte, die mit `= + - @` (oder Tab/CR) beginnen. |

Fachliche Fehler sind `CustomerError` mit `code`: `ungueltig`, `nicht_gefunden`,
`nicht_archiviert`; in `tools.py` zusätzlich `offen` (noch nicht festgelegt, z. B. `name` ändern). Falsche Kundenart oder zu lange Texte weist schon pydantic beim Bau von
`CustomerInput`/`CustomerUpdate` ab (`ValidationError`).

## Tabellen

| Tabelle | Spalten (wichtigste) | Verweist auf |
| --- | --- | --- |
| `customer` | `id` (ganze Zahl), `customer_type`, `name`, `company_name`, `first_name`, `last_name`, `street`, `zip`, `city`, `phone`, `email`, `note`, `search_text`, `archived`, `created_at`, `updated_at` | – |

`name` und `search_text` bildet nur der Service. Bankdaten werden nicht gespeichert.

## Weg einer typischen Anfrage

Archivierten Kunden löschen: `DELETE /api/customers/4`

1. FastAPI findet über den `router` aus `api.py` die Funktion `delete_customer` und gibt ihr
   über `Depends(get_session)` eine Datenbank-Sitzung.
2. `api.py` ruft über `_run` die Funktion `service.delete_customer(session, 4)`.
3. Der Service holt Kunde 4 aus der Tabelle `customer`. Ist er nicht archiviert, wirft er
   `CustomerError("nicht_archiviert", …)`; `_run` macht daraus 409 mit Meldung.
4. Sonst löscht er die Zeile; die API antwortet 204 ohne Inhalt.

Andere Features lesen ohne HTTP: F3 ruft `customers.service.get_customer(session, 4)` und bekommt
einen `Customer` mit `id` und `name` – oder `None`.

Suche: `list_customers(session, query="Müller Musterstadt")` macht daraus mit `casefold()` die
Wörter `müller` und `musterstadt`. Jedes Wort muss in `search_text` vorkommen
(`contains(…, autoescape=True)`, damit `%` und `_` keine Platzhalter sind). Sortiert wird danach in
Python nach `name.casefold()`, damit Umlaute und Kleinschreibung richtig einsortiert werden.

## Demo-Datensatz (`demo.py`)

`DEMO_CUSTOMERS` ist eine feste Liste mit zehn erfundenen Kunden (PLZ `00…`, Telefon `0000…`,
E-Mail unter `example.*`). `load_demo_customers(session)` legt sie in dieser Reihenfolge über
`create_customer()` an und archiviert die mit `archived: True` – nur in eine Datenbank ohne Kunden,
sonst `DemoRefused`. Gleiche Reihenfolge ergibt in jeder leeren Datenbank dieselben Nummern.

Befehl (im Ordner `backend/`): `uv run python -m timbertalk.features.customers.demo data/demo.db`.
`main()` prüft das Ziel mit `demo_database_url()`: nicht `data/timbertalk.db` (`REAL_DATABASE`),
nur Dateien mit `.db`. Dann legt es die Tabellen an und lädt. Vorführen:
`TIMBERTALK_DATABASE_URL=sqlite:///data/demo.db uv run timbertalk`.

## S-11-Vorbereitung (`tools.py`)

Nur Übersetzung und Prüfung, kein Katalog (S-09), keine Bestätigung (S-10), nichts registriert.
`load_features()` lädt diese Datei nicht; sie wird erst über S-09 angeschlossen.

| Funktion | Werkzeug (S-11 v0.1) | Was sie tut |
| --- | --- | --- |
| `S11_FIELDS` | `kunde_anlegen`, `kunde_aendern` | `strasse`→`street`, `plz`→`zip`, `ort`→`city`, `telefon`→`phone`, `email`→`email` |
| `changes_from_s11(fields)` | `kunde_aendern` | `felder` → `CustomerUpdate`; leere, unbekannte Felder → `ungueltig`, `name` → `offen` (D10) |
| `search_customers(session, text)` | `kunde_suchen` | `list_customers(query=text)`, ohne archivierte |
| `preview_customer_change(session, id, fields)` | `kunde_aendern` | `check_customer_update()` – Vorschau, speichert nichts |
| `preview_customer_archive(session, id)` | `kunde_archivieren` | `require_customer()` – prüft, speichert nichts |

`kunde_anlegen` ist nicht vorbereitet: S-11 v0.1 kennt nur `name`, das Modell unterscheidet
Privat/Firma (Steckbrief D9).

## Abhängigkeiten zu anderen Features

Keine – F2 ruft keine anderen Features auf.

Andere erwarten von F2 (aus den noch nicht gemergten Branches von F3): `get_customer(session, id)`
und `list_customers(session)` mit `id` und `name`. Offen und noch nicht angeschlossen:

- **S-09** (gemeinsamer Werkzeugkatalog, `drafts`): Registrierung von `kunde_suchen`,
  `kunde_anlegen`, `kunde_aendern`, `kunde_archivieren` – Pflicht im Arbeitspaket, noch offen.
- **S-10** (Bestätigung von Entwürfen): wird nicht in F2 nachgebaut; nach Bestätigung wären
  `update_customer()` bzw. `archive_customer()` aufzurufen.
- **S-11** (Entwurf v0.1): Eingaben in `tools.py` vorbereitet; `kunde_anlegen` offen (D9).
- **F3:** Prüfung „Kunde hat Projekte“ beim Löschen, sobald F3 gemergt ist.
- **DSGVO:** Die Löschregel „nur archivierte“ ist vorläufig; die offenen Fragen stehen im
  Steckbrief unter „Datenschutz“.

## Begriffe

| Begriff | Im Code |
| --- | --- |
| Privatkunde / Firma | `customer_type` = `private` / `business` |
| Anzeigename | `name` |
| Archivieren | `archived = True` |
| Suchtext | `search_text` |
| Demo-Datensatz | `demo.DEMO_CUSTOMERS`, `load_demo_customers()` |
| Vorschau (prüfen ohne Speichern) | `check_customer_input()`, `check_customer_update()`, `preview_…()` |
