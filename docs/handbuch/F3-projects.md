# F3 – Projekte (Handbuch-Kapitel)

> Steckbrief: `docs/features/F3-projects.md` · Pate: Licheng Ou · Stand: 2026-11-23

## Dateien

| Datei unter backend/timbertalk/features/projects/ | Wofür |
| --- | --- |
| models.py | Projekttabelle, Status und validierte Werkzeug-Eingaben |
| service.py | S-03 lesen, Suche, Vorschau, bestätigte Änderungen |
| integration.py | Öffentliche Services von customers und drafts; fehlende Services melden |
| tools.py | Fünf Werkzeugdefinitionen und Registrierung beim vorhandenen S-09-Dekorator |
| api.py | HTTP-Routen und Registrierung beim Anwendungsstart |
| test_projects.py | Datenbank-, Service-, API- und Werkzeug-Beispieltests |

`frontend/features/projects/projects.js` enthält den Projektreiter und die exportierte
Kunden-Projektliste. Dynamische Daten gelangen nur über `textContent` in die Seite.
`updateActionButtons()` berechnet vorhandene Schaltflächen nach jedem Schreibvorgang
neu. Dadurch bleiben nach dem Neuladen während einer Bestätigung keine Projektaktionen
versehentlich deaktiviert. Während einer Anfrage werden weitere Schreibaktionen
gesperrt. Suchfehler bleiben sichtbar, fehlende Bestätigungsaktionen bleiben gesperrt.

## Endpunkte

| Methode und Adresse | Service-Funktion | Zweck |
| --- | --- | --- |
| GET /api/projects | list_projects | Aktive/archivierte Projekte; 10 pro Seite, offset |
| GET /api/projects/customer/{id} | list_customer_projects | Projekte eines Kunden |
| GET /api/projects/customers | customer_options | Kunden-Auswahl über Kunden-Service |
| GET /api/projects/readiness | integration.readiness | Vorhandensein gemeinsamer Services |
| POST /api/projects/tools | dispatch_tool | Aufruf des gemeinsamen call_tool, keine Direktmutation |

Lesende Antworten verwenden `status` und `daten`. Fachfehler enthalten `fehler.code`
und eine verständliche deutsche `meldung`. HTTP-Parameterfehler beantwortet FastAPI
mit 422. Die Bereitschaft prüft nur das Vorhandensein von Funktionen, nicht deren
korrekte Implementierung; sie ersetzt keinen Integrationstest.

## Tabellen

`projects`: id, name, customer_id, baustelle, status, start, dauer_tage, archived, version.
`version` beginnt bei 1 und steigt bei jeder bestätigten Änderung. Archivieren setzt
`archived=True`; es löscht weder Projekt noch Status. Alle S-03-Abfragen können auch
archivierte Projekte lesen. Die normale Suche zeigt nur aktive Projekte.

## Weg einer typischen Anfrage

1. Der Benutzer wählt einen bestehenden Kunden und gibt Projektdaten ein.
2. Der Reiter ruft getJson mit POST /api/projects/tools auf.
3. api.py delegiert an service.dispatch_tool und den gemeinsamen S-09-call_tool.
4. Der registrierte Projekthandler prüft Daten und Kunde und ruft create_draft.
5. Die Oberfläche zeigt die Zusammenfassung und Feldänderungen. Erst die von S-10
   bereitgestellte Bestätigungsaktion führt den Entwurf aus.
6. S-10 prüft Benutzerrechte und Einmaligkeit und ruft apply_confirmed_action auf.
   Dieser Hook validiert erneut und verwendet die im Entwurf gespeicherte Version.
7. S-10 schreibt sein Log und bestätigt die ganze Transaktion. Bei Fehlern Rollback.

Wichtig: Ein schreibender Werkzeughandler ist **nicht** der Apply-Hook. S-10 darf
nach Bestätigung nicht erneut den entwurferzeugenden Handler ausführen.

## Abhängigkeiten und exakte Übergabepunkte

Alle Aufrufe zu anderen Features stehen in integration.py. S-03-Funktionsnamen sind
vorgegeben; unten genannte Session-Platzierung und Ergänzungen müssen mit den
noch leeren Nachbarservices abgeglichen werden.

### F2 / Kunden

- `customers.service.get_customer(session, customer_id)` → Objekt mit id/name oder None.
- Vorschlag: `customers.service.list_customers(session)` → Liste dieser Objekte.
- Der F2-Reiter importiert `renderCustomerProjects` aus `../projects/projects.js`
  und ruft `await renderCustomerProjects(container, customer.id)` in seiner Ansicht auf.
  Diese Änderung bleibt beim F2-Verantwortlichen; sein Ordner wurde nicht geändert.

### S-09 / Katalog

- `drafts.service.werkzeug(**metadata)` ist der Dekorator gemäß S-09.
- Der Router-Lifespan ruft `register_available_tools()` auf. Ohne Dekorator bleibt
  die Anwendung startbar, aber es findet keine vorgetäuschte Registrierung statt.
- Handler-Konvention dieses Vorschlags: `(session, args, quelle='ki', originaltext=None)`.
- Vorschlag für den zentralen Aufruf: `call_tool(session, name, args, quelle, originaltext)`.
- Der Katalog injiziert die Session. Sie gehört **nicht** ins Modell-JSON-Schema.
- `schema_aus` beschreibt laut S-09 nur `daten`; bei Schreibaktionen gibt es stattdessen
  eine äußere `entwurf_id`. Ein leeres Objektschema für `daten` ist dort beabsichtigt.
- Die Beispiele in tools.EXAMPLES sind die maßgebliche Testeingabe. Die Testdaten
  enthalten Kunde 4 (Berger) und Projekt 12 (Carport, Potsdam, angefragt).
- Suche erwartet genau dieses Projekt unter `daten.treffer`; Schreibbeispiele erwarten
  `status=ok` und eine Entwurfs-ID. Die Testdouble-ID ist 7; echte IDs nicht hart prüfen.

### S-10 / Entwurf

- `create_draft(session, name, args, quelle, originaltext)` → entwurf_id,
  zusammenfassung, aenderungen und braucht_ausdrueckliche_bestaetigung.
- Für diese fünf Werkzeuge muss S-10 vor Speichern des Entwurfs
  `projects.service.prepare_action(session, name, args)` aufrufen und
  `expected_version` zusammen mit den ursprünglichen Argumenten speichern.
- Nach Benutzerbestätigung: `apply_confirmed_action(session, name, args,
  expected_version=gespeicherter_wert)`. Kein Commit im Projekt-Hook.
- S-10 übernimmt Autorisierung, atomaren Commit samt log_change, doppelte Bestätigung,
  Verwerfen und Fehlermeldung `veraltet`. Ohne diese Umsetzung keine End-to-End-Abnahme.
- Die bestätigende UI wird angebunden mit `connectConfirmation({confirm, reject})`.
  Beide asynchronen Funktionen bekommen die Entwurfs-ID. confirm liefert `{status:'ok'}`
  oder den S-10-Fehler, reject liefert `{status:'verworfen'}`. Der gemeinsame Client
  kennt den angemeldeten Benutzer. Keine frei erfundene Benutzer-ID im Projekt-Reiter.
- Ohne diese Bindung bleiben Bestätigen/Verwerfen deaktiviert und die UI erklärt,
  dass noch nichts gespeichert wurde. Es gibt keinen unsicheren Ersatzweg.

### Gemeinsamer HTTP-Helfer

Der vorhandene getJson nimmt ausschließlich einen Pfad entgegen. Deshalb liegt in
`docs/features/F3-projects-shared-api.patch` die minimale Erweiterung um `options`.
Erst nach der vorgesehenen Abstimmung anwenden. Alte getJson-Aufrufe bleiben gültig.
Der Projektreiter erwartet die Zweiparameter-Signatur und deaktiviert Schreibaktionen,
solange noch der unveränderte GET-Helfer vorhanden ist. Kein Schreiben über GET.

## Suche und Grenzen

Text wird mit casefold in Projektname, Kundenname und Baustelle gesucht. Alle
Suchwörter müssen vorkommen. Prozent/Unterstrich werden wörtlich behandelt.
Die Implementierung priorisiert Verständlichkeit; sie liest Kandidaten und Kundennamen
im Service. Bei großen Datenbeständen muss ein abgestimmter Batch-Suchservice folgen.
Keine direkte Abfrage von Kundentabellen zur Beschleunigung.

## Prüfungen

`uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest` im backend-Ordner.
Die Tests benutzen die bestehenden session/client-Fixtures. Nachbarservices werden
mit monkeypatch ersetzt; diese Tests beweisen nicht, dass die gemeinsamen Services
schon existieren. Die echte S-09/S-10-Integration und Kundenansicht separat abnehmen.

Am 2026-11-23 im überarbeiteten Arbeitsstand tatsächlich ausgeführt:

- `python -m ruff check .`: erfolgreich.
- `python -m ruff format --check .`: 60 Dateien bereits formatiert.
- `python -m pytest`: 46 bestanden, mit Starlette/httpx-Abkündigung und lokaler
  Warnung zum nicht beschreibbaren Pytest-Cache.
- Mit `python -m pytest -p no:cacheprovider`: erneut 46 bestanden, ausschließlich
  die bekannte Starlette/httpx-Warnung. Keine Abhängigkeiten geändert.
- `node --check frontend/features/projects/projects.js` im Projektstamm: erfolgreich.
- 15 lokale Chrome-Browserprüfungen erfolgreich; Nachbarservices ausschließlich
  im Prüfaufbau simuliert. Kein Nachweis der echten Gesamtintegration.

Die bereits installierte Python-Umgebung des Nutzers wurde verwendet; der Import
von timbertalk zeigte auf den überarbeiteten Arbeitsstand.
Einzelheiten: `docs/features/F3-projects-pruefung.md`.

## Oberfläche und Gestaltungsprüfung

Herangezogen: apple-design, Commit 91e15664896f6f27e75dcf1414d1226cb95fa167;
cross-platform.md, accessibility.md, layout.md, typography.md, color.md,
designing-for-macos.md, entering-data.md, buttons.md, lists-and-tables.md, search-fields.md.
Angewandt: Beschriftungen, native Eingaben, sichtbarer Fokus, 44px Mindesthöhe,
Status als Text, flexible einspaltige Formulare, bestehende Hell-/Dunkel-Farbvariablen.
Nacharbeit: Code und Browserbilder bei 1440 px Breite (hell/dunkel), 390 px Breite
sowie 800 px mit 200 % Basisschrift durchgesehen. Keine horizontale Überbreite in
diesen Ansichten. Fokusfolge Projektname → Kunde und sichtbarer 3-px-Fokusring geprüft.
Eingabetext-Kontrast: 16,25:1 hell, 13,36:1 dunkel. Ergänzend herangezogen:
`feedback.md › Best practices`. Die 200-%-Prüfung betrifft Schriftvergrößerung,
nicht den Browser-Zoomregler. Vollständige Screenreader-Prüfung und die Oberfläche
mit echten Nachbarservices bleiben offen. Prüfaufbau ausschließlich mit Testdaten.

## Begriffe

Draft/Entwurf: geprüfter Änderungsvorschlag ohne Geschäftsdatenänderung.
Version: Schutz vor Überschreiben zwischen Vorschau und Bestätigung.
Archiv: ausgeblendete, weiterhin lesbare Projekte. Kein sechster Geschäftsstatus.
