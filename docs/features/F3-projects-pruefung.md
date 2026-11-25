# AP-1.5 – Prüfstand und Übergabe

Stand: 2026-11-23. Umfang: Projekt-Feature, keine abgeschlossene Gesamtintegration.

## Tatsächlich ausgeführte Prüfungen

| Prüfung | Ergebnis | Grenze |
| --- | --- | --- |
| `python -m ruff check .` im Backend | bestanden | Bestehende Ruff-Regeln |
| `python -m ruff format --check .` | 60 Dateien bereits formatiert | Python-Formatierung |
| `python -m pytest` | 46 bestanden, 2 Warnungen | Starlette/httpx-Abkündigung und lokales Cache-Schreibproblem |
| `python -m pytest -p no:cacheprovider` | 46 bestanden, 1 Warnung | Ohne Cacheproblem, nur bekannte Abkündigung |
| `node --check frontend/features/projects/projects.js` | bestanden | JavaScript-Syntax |
| Lokale Chrome-Browserprüfung | 15 bestanden | Echte Frontenddatei, simulierte Nachbarservices |
| Alter Stand mit derselben Bestätigungsprüfung | Fehler reproduziert | „Bearbeiten“ blieb deaktiviert; korrigierter Stand besteht |

Python 3.13.9 aus der installierten Nutzerumgebung; Imports zeigen auf den überarbeiteten
Arbeitsstand. Keine Projektabhängigkeiten geändert. Bestehende session/client-Fixtures
und ausdrücklich simulierte Nachbarservices. Keine produktiven Daten verändert.

## Die 15 Browserprüfungen

1. Bestätigen aktiviert Projektaktionen wieder.
2. Verwerfen aktiviert Aktionen wieder, ohne Projektänderung.
3. Bestätigungsfehler erlaubt Wiederholung; fehlender Verwerfen-Handler bleibt gesperrt.
4. Kundenpflicht verhindert Absenden; gültige Eingaben erzeugen den richtigen Werkzeugaufruf.
5. Bearbeiten und Archivieren rufen die vorgesehenen Werkzeuge auf.
6. Der unveränderte GET-Helfer erlaubt keine Erstellung.
7. Fehlende gemeinsame Dienste erlauben keine Erstellung.
8. Eine leere Kundenliste erlaubt keine Erstellung.
9. Suchfehler werden nicht durch die Bereitschaftsmeldung verdeckt.
10. Ohne Bestätigungsadapter keine Ausführung; Fokus bleibt erreichbar.
11. Die exportierte Kunden-Projektkomponente zeigt die übergebenen Daten.
12. Desktop, hell, 1440 × 1000: Layout, Fokus und Kontrast.
13. Desktop, dunkel, 1440 × 1000: Layout, Fokus und Kontrast.
14. 390 × 844: kein horizontales Überlaufen.
15. 800 × 1000 mit 200 % Basisschrift: kein horizontales Überlaufen.

Die Schrift wurde per CSS vergrößert, nicht über den Browser-Zoomregler.
Bildschirmleser wurden nicht vollständig getestet. Der Kundenreiter wurde nicht
implementiert: seine Projektkomponente wurde isoliert geprüft. Die Browserantworten
beweisen keine echte Speicherung oder abgeschlossene S-09/S-10-Integration.

## Oberflächenprüfung

Code und Browserbilder nach dem in CLAUDE.md festgelegten Gestaltungsstand geprüft.
Bewertung im geprüften Umfang: gut; die Bedienblockade ist behoben. Das Formular
folgt dem bestehenden TimberTalk-Aussehen und bleibt bewusst einfach.

| Bezug | Nachweis |
| --- | --- |
| `accessibility.md › Vision`, `color.md › Best practices` | Eingabetext-Kontrast 16,25:1 hell, 13,36:1 dunkel; aus berechneten CSS-Farben |
| `layout.md › Adaptability`, `typography.md › Ensuring legibility` | Schmale Ansicht und 200 % Basisschrift ohne Überbreite |
| `buttons.md › Best practices`, `feedback.md › Best practices` | Zustandsabhängige Sperre, sichtbare Rückmeldung, gedrückter Zustand |
| `entering-data.md › Best practices` | Native Pflichtfelder, Kundenauswahl, Fokusfolge Projektname → Kunde |
| `designing-for-macos.md › Best practices`, `references/cross-platform.md › Vocabulary` | Web-Tastaturbedienung, 3-px-Fokusring, CSS-Farbvariablen |

## Konkrete Übergaben

| Zuständigkeit | Benötigte Umsetzung |
| --- | --- |
| F2 / Kunden | `get_customer(session, id)`, abgestimmte Kundenliste; `renderCustomerProjects` im Kundenreiter aufrufen |
| S-09 / Anton | Registrierung, `list_tools`/`call_tool`, Schema-Prüfung und Handler-Signatur; alle fünf Beispiele über den echten Katalog prüfen |
| S-10 / Tingyu | Entwürfe speichern, bestätigen/verwerfen, Rechte/Einmaligkeit prüfen, Projektänderung und Log gemeinsam speichern; Versionsstand an Projekt-Hook übergeben |
| Gemeinsame Oberfläche / Peter oder Anton | POST-Patch koordinieren und `connectConfirmation` anschließen |
| F3 / Licheng | Adapter an endgültige Verträge anpassen; echte Integrationstests und Vorführung abschließen |

`readiness.ready` prüft nur, ob ausgewählte Funktionen vorhanden sind. Auch `true`
beweist keine korrekte Bestätigung oder Speicherung. Die vorgeschlagenen Übergaben
im Handbuch müssen mit den tatsächlichen Services abgeglichen werden.

## Gemeinsame Abnahme, weiterhin offen

- [ ] Mit echtem Kunden Projekt und Baustelle anlegen, Vorschau prüfen und bestätigen.
- [ ] Nach Neuladen bleiben Projekt und Kundenbezug erhalten; ohne/mit unbekanntem Kunden keine Speicherung.
- [ ] Suchen, ändern, alle fünf Status setzen und archivieren; im Archiv und über S-03 weiterhin lesbar.
- [ ] Kundenreiter zeigt zugehörige Projekte; Team B prüft beide S-03-Funktionen.
- [ ] Jedes Werkzeug über den echten S-09-Katalog mit seinem Beispiel aufrufen.
- [ ] Mit S-10 Abbruch, doppelte Bestätigung, fehlende Berechtigung und veraltete Daten prüfen.
- [ ] Baustellenpflicht, Kalenderdauer und zusätzliches Archiv-Werkzeug abstimmen.

Bis dahin: Draft-PR zur Durchsicht, keine vollständige Abnahme von LA-03/LA-04/LS-03.
