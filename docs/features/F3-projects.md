# F3 – Projekte / AP-1.5

## Ziel

Jeder Auftrag hat ein Projekt mit Kunde, Baustelle und Status.
Verantwortlich: Licheng Ou; Schnittstellen S-03, S-09, S-10, S-12.

## Was der Zimmerer danach kann

Nach Anschluss der gemeinsamen Services sucht er im Reiter Projekte nach Projekt,
Kunde und Baustelle, filtert den Status
und öffnet das Archiv. Er legt Projekte an und bereitet Änderungen oder eine
Archivierung zur Bestätigung vor. Kunden werden aus dem Kunden-Service ausgewählt.
Ein Entwurf verändert noch keine Projektdaten.
Im vorliegenden Grundgerüst fehlen diese gemeinsamen Services noch. Schreibaktionen
bleiben deshalb gesperrt; die vollständige Abnahme ist weiterhin offen.

## Abnahme

Die folgenden Punkte sind die Ziel-Abnahme, **noch nicht abgehakt**:

1. Vorhandenen Kunden auswählen, Projekt mit Baustelle anlegen, Vorschau prüfen,
   bestätigen; nach Neuladen erhalten. Ohne Kunde keine Speicherung.
2. Projekt nach Name, Kunde oder Baustelle suchen, ändern und nach Bestätigung
   archivieren. Archiv erhält Datensatz, Kundenbezug und Geschäftsstatus.
3. Alle fünf Status setzen: angefragt, geplant, in_arbeit, abgeschlossen, abgerechnet.
   Die Oberfläche zeigt „In Arbeit“, der Vertrag verwendet `in_arbeit`.
4. Kundenreiter zeigt die zugehörigen Projekte über `renderCustomerProjects`.
5. Team B liest `get_project(session, id)` und `get_customer(session, id)`;
   unbekannte ID liefert `None`.
6. S-09 listet alle fünf Werkzeuge. Jedes dokumentierte Beispiel wird gegen den
   echten Katalog ausgeführt und sein Ergebnis geprüft.
7. Entwurf verwerfen verändert nichts; doppelte Bestätigung führt nicht zweimal aus;
   veraltete oder nicht berechtigte Bestätigung wird von S-10 abgewiesen.
8. ruff und pytest bestehen, Oberfläche wird im Browser geprüft.

## Aktueller Stand und Abhängigkeiten

Der gelieferte Ausgangsstand enthält ausschließlich leere Fachmodule.
`customers.service` und `drafts.service` besitzen noch keine Funktionen.
Es wurden keine anderen Feature-Ordner verändert und keine Ersatz-Kundentabelle,
kein zweiter Katalog und keine lokale Bestätigungsdatenbank angelegt.

| Anforderung | Implementiert im Projekt-Feature | Noch für End-to-End-Abnahme nötig |
| --- | --- | --- |
| Projektmodell und S-03 | Project, get_project, delegiertes get_customer | Reales Customer-Modell und Kunden-Service |
| Anlegen/Ändern/Archivieren | Validierung, Vorschau, transaktionaler Apply-Hook, UI | S-10 Bestätigung, Rechte, Log und Einmaligkeit |
| Status | Enum, Eingabeprüfung, Apply-Hook, UI | S-10 wie oben |
| Kundenliste zeigt Projekte | GET customer/{id}, renderCustomerProjects | F2 bindet die Komponente in seinen Reiter ein |
| S-09 | Metadaten, Schema, Beispiele, Start-Registrierungsadapter | Katalog und vereinbarte Handler-Konvention |
| Tests | 46 Backend-Tests bestanden; 15 Browserprüfungen mit simulierten Nachbarservices | Echte Integration mit Kunden, Katalog und Bestätigung |

## Nacharbeit am 2026-11-23

Projektaktionen werden nach Bestätigen und Verwerfen wieder freigegeben. Eine
fehlgeschlagene Bestätigung bleibt wiederholbar; fehlende Bestätigungsaktionen bleiben
gesperrt. Suchfehler werden nicht mehr durch einen allgemeinen Hinweis verdeckt.
Ladezustände, Tastaturfokus und deaktivierte Schaltflächen sind verbessert.
Ruff, Formatprüfung, 46 Backend-Tests und 15 Browserprüfungen sind erfolgreich.
Prüfumfang und Grenzen: `docs/features/F3-projects-pruefung.md`.
Diese Ergebnisse ersetzen keine echte Integration oder Abnahme von LA-03/LA-04/LS-03.

## Abzustimmende Details

- `projekt_archivieren` ergänzt S-12, weil AP-1.5 Archivierung und ein Werkzeug für
  jede Aktion verlangt. Keine Löschung, keine Wiederherstellung in diesem Paket.
- `baustelle_ort` bleibt entsprechend S-12 optional; S-03 heißt das Feld `baustelle`.
- Neue Projekte beginnen mit `angefragt`; alle fünf Status sind frei setzbar,
  weil keine Übergangsregeln spezifiziert sind.
- Dauer bedeutet hier Kalendertage einschließlich Starttag. Der Vertrag definiert
  die Kalender-/Arbeitstagsfrage nicht; vor Abnahme mit dem Team abgleichen.
- `projekt_aendern` erlaubt Name, Kunde, Baustelle, Beginn und Dauer. Statusänderung
  und Archivierung nutzen eigene Werkzeuge. Leere Änderungen werden abgelehnt.
- Ein Projekt benötigt beim Vorbereiten **und** beim Bestätigen einen bestehenden
  Kunden. Der Kunden-Service entscheidet später, ob archivierte Kunden nutzbar sind.
- Kunden-Tabellenname und Löschregeln fehlen. Deshalb keine geratene Foreign-Key-
  Referenz; DB erzwingt positive, nicht leere Kunden-ID, Service die Existenz.
- S-10 speichert den Versionsstand, ruft den Apply-Hook in seiner Transaktion auf
  und schreibt das Änderungsprotokoll atomar. Diese Hooks sind ein Integrationsvorschlag.
- S-09 muss fehlende Pflichtangaben als `rueckfrage` zulassen, statt sie vorher
  pauschal als Schemafehler abzuweisen.

## Nicht dabei

Keine Umsetzung fremder Features, kein direkter Schreib-Endpunkt ohne Bestätigung,
kein Login-Ersatz, keine neuen Bibliotheken. Keine Änderung an öffentlichen
Grundgerüst-Dateien. Die kleine GET/POST-Erweiterung ist als separate Patchdatei beigefügt.
Keine Migration bestehender Fremdtabellen: Im gelieferten main existiert noch keine
Projekttabelle. `create_all` legt unsere neue Tabelle an; spätere Schemaänderungen
benötigen eine abgestimmte Migration und dürfen nicht mit create_all kaschiert werden.

## Neues Konzept fürs Team

Optimistische Versionsprüfung: Eine Änderung gilt nur für genau den angezeigten
Versionsstand. Kunden bleiben im Kunden-Feature; nur dessen öffentliche Services
werden aufgerufen. Tests ersetzen fehlende Nachbarservices sichtbar und ausschließlich
innerhalb der Tests, niemals zur Laufzeit.

## Reiter

`frontend/features/projects/projects.js`; schon in `frontend/reiter.js` registriert.

## Pate

Licheng Ou. Für die fehlenden gemeinsamen Verträge: Kunden-Team, Tingyu Li (S-10),
Anton Meyer-Erlach (S-09). Merge durch Peter oder Anton.
