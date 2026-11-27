# F2 – Kunden

> **Status: als Arbeitsgrundlage freigegeben am 2026-11-25 – Feature noch nicht abgeschlossen.**
> Arbeitspaket AP-1.4, Frist 27.11.2026. Fertig: Backend, API (mit Anmeldung F10 und
> Änderungsprotokoll F11), Reiter mit Liste, Suche, Export, Formularen und Dialogen – Speichern
> über `sendJson()` aus `shared/api.js`, Demo-Datensatz (LD-09), Export-Prüfungen (LN-05),
> S-11-Vorbereitung ohne Registrierung.
> Offen: Registrierung und Bestätigung der KI-Werkzeuge (S-09/S-10), `kunde_anlegen` nach S-11
> (D9), DSGVO-Löschung (D3), Rechte für Kunden (D11), Demo-Daten in `timbertalk/demo.py` (D12).
>
> Drei Arten von Angaben werden hier auseinandergehalten:
> - **bestätigt** – Anforderungen aus AP-1.4 und die Freigabe dieses Steckbriefs;
> - **vorläufig** – S-11 im Entwurf Version 0.1 (aus dem Projektmanagementsystem, noch nicht
>   umgesetzt). Zu S-09 und S-10 liegen keine Texte vor, nur Verweise in anderen Branches;
> - **umgesetzt** – was es im Code gibt und was getestet ist.

## Ziel

Der Betrieb pflegt seine Kunden an einer Stelle: anlegen, suchen, bearbeiten, archivieren,
exportieren und löschen – über die Oberfläche und über KI-Werkzeuge. Andere Features lesen Kunden
nur über `customers.service`.

## Was der Zimmerer danach kann

Im Reiter „Kunden“ sieht er die Liste seiner Kunden und findet einen Kunden über das Suchfeld nach
Name, Ort, Postleitzahl, Telefon oder E-Mail. Er legt einen neuen Privat- oder Firmenkunden an,
ändert Adresse und Kontaktdaten und archiviert Kunden, mit denen er nicht mehr arbeitet; archivierte
Kunden blendet er bei Bedarf wieder ein und holt sie zurück. Die Kundenliste kann er als Datei für
Excel herunterladen. Einen Kunden ganz zu löschen geht nur nach einer Rückfrage. Später kann er
der KI sagen „Such mir den Kunden Mustermann“ oder „Leg einen neuen Kunden an“; was die KI ändern
will, bestätigt er vorher. Für Vorführungen gibt es eine erfundene Zimmerei mit zehn Kunden.

## Abnahme

Im Meeting wird genau das vorgeführt:

1. **Anlegen:** Ein Privatkunde (Vorname, Nachname, Adresse) und ein Firmenkunde (Firmenname,
   Adresse) werden angelegt und sind nach dem Neuladen noch da. Ohne Nachname (privat) bzw. ohne
   Firmenname (Firma) lehnt die API das Speichern ab.
2. **Suchen:** Die Suche findet Kunden nach Name, Ort, PLZ, Telefon und E-Mail, ohne Rücksicht auf
   Groß- und Kleinschreibung – auch bei Umlauten („müller“ findet „Müller“).
3. **Bearbeiten:** Adresse und Kontaktdaten eines Kunden werden geändert und bleiben gespeichert.
4. **Archivieren:** Ein archivierter Kunde verschwindet aus der Liste, erscheint mit „Archivierte
   zeigen“ und lässt sich wiederherstellen. Seine Daten bleiben unverändert.
5. **Exportieren (LN-05):** Die Kundenliste wird als CSV-Datei heruntergeladen und öffnet sich in
   Excel mit richtigen Umlauten. Sonderzeichen bleiben erhalten; Werte, die Excel als Formel lesen
   würde, sind entschärft. Spalten siehe „Export“.
6. **Löschen:** Nur ein archivierter Kunde lässt sich löschen; ein aktiver wird abgewiesen.
   **[OFFEN – D3]** DSGVO-Anforderungen, siehe „Datenschutz“.
7. **Service für andere Features (Erwartung von F3):** `get_customer(session, customer_id)` liefert
   einen Kunden mit mindestens `id` (ganze Zahl) und `name` oder `None` bei unbekannter Nummer;
   `list_customers(session)` liefert eine Liste solcher Kunden. Beides mit Test.
8. **KI-Werkzeuge (S-11, S-09, S-10):** Die Werkzeuge sind Teil des Arbeitspakets. In diesem Stand
   vorgeführt: Die Eingaben aus S-11 werden in `tools.py` auf die Service-Funktionen übersetzt und
   ohne Speichern geprüft (Tests). **[OFFEN – D1/D2/D9]** Registrierung im gemeinsamen Katalog,
   Bestätigung über S-10 und `kunde_anlegen`.
9. **Demo-Datensatz (LD-09):** Ein Befehl lädt zehn erfundene Kunden einer erfundenen Zimmerei in
   eine eigene Datei – nie in die echte Datenbank. Zweimal geladen ergibt dieselben Daten.
10. **Testdaten:** Alle Tests und Demo-Daten verwenden nur erfundene Personen, Firmen und Adressen.
11. **Oberfläche:** Punkte 1–6 auch im Reiter „Kunden“. Suchen, Ansehen und Export
    funktionieren. Die Formulare (Anlegen, Bearbeiten, Privat/Firma) und die Dialoge (Archivieren,
    Wiederherstellen, Löschen mit Häkchen) speichern über `sendJson()` (`WRITE_ENABLED = true`).
    Eine Erfolgsmeldung erscheint nur, wenn die Antwort die Änderung bestätigt; lehnt der Server
    ab, steht seine deutsche Meldung im Dialog („Nicht gespeichert: …“).
12. **Anmeldung und Protokoll:** Ohne Anmeldung antwortet jeder Kunden-Endpunkt (auch der Export)
    mit 401. Jede erfolgreiche Änderung steht im Änderungsprotokoll unter „Kunden“ mit ihrem Namen
    (`summary`, z. B. „Kunde anlegen“).
13. `uv run pytest`, `uv run ruff check .` und `uv run ruff format --check .` sind grün; die
    Oberfläche ist mit dem Skill `apple-design` durchgesehen.

## Demo-Datensatz (LD-09)

Erfundene Zimmerei „Zimmerei Musterholz“ mit zehn Kunden in `backend/timbertalk/features/customers/demo.py`:
fünf Privatkunden, fünf Firmen, sechs Orte, davon zwei Kunden archiviert. Erkennbar erfunden: PLZ mit
`00`, Telefon mit `0000`, E-Mail nur unter `example.com`/`.org`/`.net`. Keine Bankdaten.

Laden (im Ordner `backend/`), immer in eine **eigene** Datei:

```bash
uv run python -m timbertalk.features.customers.demo data/demo.db
```

Vorführen mit dieser Datei:

```bash
# PowerShell
$env:TIMBERTALK_DATABASE_URL = "sqlite:///data/demo.db"; uv run timbertalk
# Bash
TIMBERTALK_DATABASE_URL=sqlite:///data/demo.db uv run timbertalk
```

Schutz: Der Befehl verweigert die echte Datenbank `data/timbertalk.db`, Dateien ohne `.db` und jede
Datenbank, in der schon Kunden stehen. `*.db` ist in `.gitignore`. Neu laden: Datei löschen, Befehl
wiederholen.

Suchfälle für die Vorführung:

| Suche | Ergebnis |
| --- | --- |
| `mustermann` | zwei Kunden mit gleichem Nachnamen |
| `ÜBERSEE` | Umlaut und Großschreibung |
| `özdemir` | Doppelname mit Bindestrich |
| `00101` | drei Kunden mit derselben PLZ (privat und Firma) |
| `beispielhausen wohnbau` | zwei Wörter müssen beide passen |
| `platzhalter` | archiviert: nur mit „Archivierte zeigen“ |

Ein Kunde heißt `=Formel Testbau GmbH (erfunden)` und hat die Telefonnummer `+0000 600100`: Im
Export zeigt er die Entschärfung von Formeln.

## Export (LN-05)

CSV, Semikolon, UTF-8 mit BOM, Zeilenende `\r\n`. Spalten in dieser Reihenfolge: Kundennummer, Art,
Name, Firma, Vorname, Nachname, Straße, PLZ, Ort, Telefon, E-Mail, Notiz, Archiviert. Nicht
exportiert: der interne Suchtext und die Zeitpunkte `created_at`/`updated_at`.

Werte, die mit `=`, `+`, `-`, `@`, Tabulator oder Wagenrücklauf beginnen, bekommen ein `'` davor
(Schutz vor Formel-Injection). Folge: Eine Telefonnummer `+49 …` erscheint als `'+49 …`.
Semikolon, Anführungszeichen und Zeilenumbrüche in Werten bleiben dank CSV-Quoting erhalten.

## Datenschutz (DSGVO) – offen

Umgesetzt ist nur die vorläufige Regel: endgültig löschen nur nach Archivieren; der Kunde ist danach
aus Datenbank, Liste und Export entfernt. **Nicht geklärt und nicht umgesetzt:**

1. **Löschen auf Verlangen (Art. 17 DSGVO)** gegen **Aufbewahrungspflichten** (z. B. § 257 HGB,
   § 147 AO für Rechnungen und Geschäftsbriefe): Darf ein Kunde mit Rechnungen gelöscht werden,
   oder werden seine Daten stattdessen anonymisiert?
2. **Kunden mit Projekten:** Löschen sperren, anonymisieren oder mit den Projekten löschen?
   (Prüfung über `projects.service`, sobald F3 in `main` ist.)
3. **Auskunft (Art. 15) und Datenübertragbarkeit (Art. 20):** Export für einen einzelnen Kunden?
4. **Nachweis:** Wird eine Löschung protokolliert (wer, wann), ohne die gelöschten Daten zu behalten?
5. **Datensicherungen:** Wie lange bleiben gelöschte Kunden in Sicherungen (Feature `backup`)?
6. **Berechtigung:** Wer darf löschen und exportieren (Feature `accounts`, siehe D11)?
7. **Exportdateien:** Sie enthalten personenbezogene Daten; Hinweis zum Umgang in der Oberfläche?
8. **Änderungsprotokoll (F11):** Die gemeinsame Middleware schreibt bei jeder Änderung die
   gesendeten Angaben (Name, Adresse, Telefon, E-Mail, Notiz) gekürzt in das Protokoll. Nach dem
   Löschen eines Kunden stehen sie dort weiter. Wie lange bleibt das Protokoll, und reicht für
   Kunden „wer, wann, welcher Kunde“ ohne Inhalte? Zu klären mit F11 – nicht in F2 änderbar.

Die Löschregel wird erst geändert, wenn diese Punkte fachlich entschieden sind.

## KI-Werkzeuge nach S-11 (vorläufig: Entwurf Version 0.1)

S-11 v0.1 listet für Kunden vier Werkzeuge. Was davon in F2 umgesetzt ist:

| Werkzeug (S-11 v0.1) | Art | Eingabe (S-11 v0.1) | In F2 umgesetzt (`tools.py`, getestet) | Offen |
| --- | --- | --- | --- | --- |
| `kunde_suchen` | lesen | `text: str` | `search_customers(session, text)` | Registrierung (D1), Antwortformat |
| `kunde_anlegen` | entwurf | `name: str`, optional `strasse`, `plz`, `ort`, `telefon`, `email` | Feldübersetzung `S11_FIELDS` für die optionalen Felder | `name` passt nicht zum Modell (D9); Registrierung, Bestätigung (D1, D2) |
| `kunde_aendern` | entwurf | `kunde_id: int`, `felder: dict` | `changes_from_s11()`, `preview_customer_change()` – Vorschau ohne Speichern | erlaubte Schlüssel in `felder` (D10); Registrierung, Bestätigung |
| `kunde_archivieren` | entwurf | `kunde_id: int` | `preview_customer_archive()` – Vorschau ohne Speichern | Registrierung, Bestätigung |

Nach der Bestätigung durch S-10 wären `service.update_customer()` bzw. `service.archive_customer()`
aufzurufen – wie S-10 das tut, ist nicht festgelegt. F2 baut **keinen** eigenen Werkzeugkatalog,
**keine** Entwurfstabelle und **keine** Bestätigung.

Aufrufe nach S-11 v0.1 (erfundene Daten; die äußere Form `werkzeug`/`args` ist nicht festgelegt):

```json
{"werkzeug": "kunde_suchen", "args": {"text": "Mustermann"}}
```

```json
{"werkzeug": "kunde_anlegen", "args": {"name": "Beispiel Wohnbau GmbH", "ort": "Beispielhausen", "email": "info@wohnbau.example.com"}}
```

```json
{"werkzeug": "kunde_aendern", "args": {"kunde_id": 1, "felder": {"ort": "Beispielhausen", "plz": "00303"}}}
```

```json
{"werkzeug": "kunde_archivieren", "args": {"kunde_id": 1}}
```

**Abweichungen zwischen S-11 v0.1 und F2:**

- `kunde_anlegen` hat nur `name`; F2 unterscheidet Privat/Firma und Vor-/Nachname/Firmenname (D9).
- `kunde_anzeigen` und ein Export-Werkzeug gibt es in S-11 nicht. F2 schlägt sie nicht mehr vor.
- `kunde_suchen` findet in F2 nur aktive Kunden; archivierte über ein Werkzeug: nicht vorgesehen.
- `mitarbeiter_suchen` und `mitarbeiter_anlegen` (ebenfalls S-11) gehören nicht zu F2, sondern zum
  Feature `employees`.
- Löschen hat in S-11 kein Werkzeug – passt zu D3.

## Datenmodell

Tabelle `customer`, Primärschlüssel eine **ganze Zahl** (nicht uuid wie in Block 1), weil F3 eine
ganze Zahl als `customer_id` erwartet.

| Feld | Bedeutung |
| --- | --- |
| `id` | Kundennummer, vergibt die Datenbank |
| `customer_type` | `private` oder `business` |
| `name` | Anzeigename, bildet der Service (Firmenname bzw. „Vorname Nachname“) |
| `company_name`, `first_name`, `last_name` | Name je nach Kundenart |
| `street`, `zip`, `city` | Adresse |
| `phone`, `email` | Kontakt |
| `note` | freie Notiz |
| `search_text` | kleingeschriebener Suchtext, bildet der Service |
| `archived` | archiviert ja/nein |
| `created_at`, `updated_at` | Zeitpunkte |

Bewusst **nicht** enthalten: IBAN oder andere Bankdaten, USt-IdNr., Kennzeichen für § 13b UStG,
Zusatzfelder. Sie kommen nur mit bestätigter fachlicher Anforderung. Geldbeträge gibt es hier nicht.

## Offene Fragen im Überblick

Stand 2026-11-27, angepasst an `main`. Details in der Tabelle darunter.

- **Berechtigungen (D11):** Heute darf jede angemeldete Person Kunden sehen, anlegen, ändern,
  archivieren, löschen und exportieren. Welche Rollen was dürfen, ist nicht entschieden; ein Recht
  braucht eine Zeile in der gemeinsamen Datei `features/accounts/permissions.py`.
- **S-09 (D1):** Werkzeugkatalog fehlt; `kunde_suchen`, `kunde_aendern`, `kunde_archivieren` sind
  in `tools.py` nur vorbereitet, nicht registriert.
- **S-10 (D2):** Bestätigung von Entwürfen fehlt; F2 baut sie nicht nach.
- **S-11 (D9, D10):** `kunde_anlegen` kennt nur `name` (D9); erlaubte Schlüssel in `felder` (D10).
- **DSGVO (D3):** Löschen gegen Aufbewahrungspflichten, Kunden mit Projekten, Auskunft, Nachweis,
  Sicherungen, Exportdateien und Kundendaten im Änderungsprotokoll – siehe „Datenschutz“.
- **Demo-Daten (D12):** `customers/demo.py` bleibt; die gemeinsame `timbertalk/demo.py` ist
  unverändert.

## Offene Entscheidungen

| Nr. | Frage | Vorgehen bis zur Klärung |
| --- | --- | --- |
| D1 | **S-09:** Dekorator, Felder und Aufrufkonvention des gemeinsamen Werkzeugkatalogs (AP-0.5, `drafts`) – existiert noch nicht. | Übersetzung und Prüfung in `tools.py`; nichts registriert, kein eigener Katalog. |
| D2 | **S-10:** Wer bestätigt schreibende Werkzeuge, welchen Hook ruft S-10 auf, wie wird der Versionsstand geprüft? | Nicht bauen. `check_customer_input()` und `check_customer_update()` prüfen ohne zu schreiben (Vorschau). |
| D3 | **Löschen/DSGVO:** siehe „Datenschutz“. | Nur archivierte Kunden löschbar. |
| D4 | ~~S-11 als Exportformat~~ – erledigt: S-11 beschreibt KI-Werkzeuge, kein Exportformat. | Export nach Abschnitt „Export“ (LN-05). |
| D5 | **Export vs. Backup:** Gehört der Export zu F2 oder zum Feature `backup`? | F2 exportiert nur die Kundenliste. |
| D6 | ~~`shared/api.js` kann nur GET~~ – erledigt: `main` bietet `sendJson(method, path, body)`. | `sendChange()` ruft `sendJson()`; `WRITE_ENABLED = true`, im Browser mit Anmeldung geprüft. Fehlertexte kommen als Text in `detail`. |
| D7 | **Pflichtfelder:** Reichen Nachname bzw. Firmenname? | Ja, sonst alles freiwillig. |
| D8 | **Archivierte Kunden in Projekten:** Darf F3 einem archivierten Kunden ein Projekt geben? | `get_customer` liefert auch archivierte Kunden mit `archived`; F3 entscheidet. |
| D9 | **`kunde_anlegen` in S-11 v0.1 hat nur `name`.** S-11 um Kundenart und Vor-/Nachname bzw. Firmenname ergänzen, oder `name` in F2 einer Kundenart zuordnen? | Nicht umgesetzt; Vorschlag an S-11: optionale Felder `kundenart`, `vorname`, `nachname`, `firmenname`. |
| D10 | **`felder` in `kunde_aendern`:** Welche Schlüssel sind erlaubt, darf `name` geändert werden? | Erlaubt sind `strasse`, `plz`, `ort`, `telefon`, `email`; `name` wird abgewiesen (Code `offen`). |
| D11 | **Rechte (F10):** Wer darf Kunden sehen, anlegen, ändern, archivieren, löschen und exportieren? `permissions.py` hat noch kein Kundenrecht. | Jede angemeldete Person darf alles. Ein Recht (z. B. `customers.edit`, `customers.delete`) braucht eine Zeile in der gemeinsamen Datei `permissions.py` – erst nach Abstimmung. |
| D12 | **Demo-Daten (CLAUDE.md):** Features ergänzen den Beispielbetrieb in `backend/timbertalk/demo.py`. F2 hat eigene Demo-Daten in `customers/demo.py` (LD-09). | Unverändert gelassen; `timbertalk/demo.py` ist eine gemeinsame Datei. Nach Freigabe: Kunden aus `DEMO_CUSTOMERS` über `customers.service` in `seed()` anlegen. |

## Nicht dabei

- **Projekte eines Kunden im Kundenreiter:** gehört zu F3, ist noch nicht in `main`.
- **Eigener Werkzeugkatalog, eigene Entwurfstabelle, eigene Bestätigung:** wären inkompatibel zu
  S-09/S-10 (AP-0.5, `drafts`). Die Werkzeuge selbst bleiben Teil von AP-1.4.
- **Mitarbeiter-Werkzeuge aus S-11:** Feature `employees`.
- **Bankdaten, USt-IdNr., § 13b, Zusatzfelder:** ohne bestätigte Anforderung nicht.
- **Import von Kunden, Dubletten-Erkennung, Migrationen.**

## Neues Konzept fürs Team

- **Archivieren statt Löschen:** Ein Kunde wird über `archived` ausgeblendet, nicht entfernt, damit
  Projekte und Rechnungen ihren Bezug behalten.
- **Suche mit Umlauten:** SQLite vergleicht bei `LIKE` nur ASCII-Buchstaben ohne Rücksicht auf
  Groß-/Kleinschreibung. Der Service speichert deshalb `search_text` mit `casefold()`.
- **CSV-Export mit Formel-Schutz:** Die API antwortet mit einer Datei statt mit JSON.
- **Prüfen ohne Speichern:** `check_customer_input()` und `check_customer_update()` melden Fehler,
  ohne etwas zu schreiben – die Grundlage für eine spätere Vorschau in S-10.
- **Demo-Daten in eigener Datei:** `python -m …customers.demo <datei.db>`; die echte Datenbank wird
  verweigert.
- **Erfolg nur mit Nachweis:** Im Reiter laufen alle Schreibaktionen über `sendChange()` und damit
  über `sendJson()`. Eine Erfolgsmeldung gibt es nur, wenn die Antwort der API die Änderung
  bestätigt (`confirmsChange`). So erscheint nie „Gespeichert“, wenn etwas schiefging.

## Reiter

`customers` („Kunden“): `frontend/features/customers/customers.js` – schon in `frontend/reiter.js`
eingetragen, keine Änderung dort.

## Pate

Noch mit Peter/Anton zu klären.
