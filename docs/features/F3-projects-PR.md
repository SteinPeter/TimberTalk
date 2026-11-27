# Draft-PR für AP-1.5

Titel: projects: AP-1.5 Projektverwaltung vorbereiten und Bedienzustände korrigieren

Die folgenden Abschnitte entsprechen der Repository-Vorlage. Nach Übernahme auf
einen neueren main-Stand Prüfungen erneut ausführen und Ergebnisse aktualisieren.

## Was kann man jetzt?

Das Projektmodul enthält Kundenbezug, Baustelle, fünf Status, Suche und Archivierung.
Der Projektreiter bietet die Formulare; nach Bestätigen oder Verwerfen werden seine
Aktionen wieder bedienbar. Im Grundgerüst fehlen noch gemeinsame Kunden-, Werkzeug-
und Entwurfsdienste, deshalb bleiben echte Schreibvorgänge bis zur Integration gesperrt.

Steckbrief: `docs/features/F3-projects.md`.
Prüfbericht: `docs/features/F3-projects-pruefung.md`.

## Wie probiere ich es aus?

```bash
cd backend
uv sync
uv run timbertalk
```

Den Reiter „Projekte“ und `/api/projects/readiness` öffnen. Bei fehlenden Diensten
ist die Sperre der Schreibaktionen zu erwarten. Isolierte Backend-Tests:
`uv run pytest`. Die vollständige Vorführung benötigt F2, S-09, S-10 und den
gemeinsamen POST-Helfer. Konkrete Übergaben stehen im Prüfbericht.

## Welche Dateien sind neu?

Geändert oder ergänzt werden ausschließlich die folgenden Feature-Dateien:

| Datei/Ordner | Wofür |
| --- | --- |
| `backend/timbertalk/features/projects/` | Projektmodell, Services, API, Werkzeuge, Adapter und Tests |
| `frontend/features/projects/projects.js` | Projektansicht, Formulare und Kunden-Projektkomponente |
| `docs/features/F3-projects.md` | Umfang und offene Abnahme |
| `docs/handbuch/F3-projects.md` | Umsetzung und Schnittstellen |
| `docs/features/F3-projects-pruefung.md` | Prüfergebnisse und Teamübergaben |
| `docs/features/F3-projects-shared-api.patch` | Vorschlag für HTTP-Helfer, nicht angewendet |
| `docs/ki-nutzung/2026-11-23-projekte-ap15*.md` | Offenlegung von Erstellung und Nacharbeit |

## Was ist neu zu verstehen?

S-10 besitzt Rechteprüfung, Einmaligkeit, Protokoll und Transaktion. Der Projekt-Hook
prüft den Versionsstand. Kundendaten kommen nur aus dem Kunden-Service. Aktuelle
Werkzeug- und Browserprüfungen ersetzen fehlende Services ausdrücklich durch
Testdoubles und beweisen keine abgeschlossene Integration.

Gestaltungsquellen aus dem in CLAUDE.md festgelegten Stand:
`accessibility.md › Vision`, `layout.md › Adaptability`,
`typography.md › Ensuring legibility`, `color.md › Best practices`,
`designing-for-macos.md › Best practices`, `buttons.md › Best practices`,
`entering-data.md › Best practices`, `feedback.md › Best practices`,
`references/cross-platform.md › Vocabulary`.

## Vor der Durchsicht geprüft

- [x] Ruff und Formatprüfung erfolgreich.
- [x] 46 Backend-Tests erfolgreich; bestehende Starlette/httpx-Warnung dokumentiert.
- [x] Steckbrief vorhanden, ausstehende Abnahmepunkte ausdrücklich offen.
- [x] Handbuch-Kapitel aktualisiert.
- [x] Code und Browserbilder geprüft; 15 isolierte Browserprüfungen erfolgreich.
- [x] KI-Nutzung und Nacharbeit dokumentiert.

## Noch vor der vollständigen Abnahme

- [ ] Kundenservices und Projektanzeige im Kundenreiter integrieren.
- [ ] Echten S-09-Katalog anschließen und Beispiele über `call_tool` prüfen.
- [ ] S-10-Bestätigung, Verwerfen, Rechte, Log, Einmaligkeit und Version gemeinsam testen.
- [ ] Gemeinsamen POST-Helfer koordinieren und anwenden.
- [ ] Vollständigen Ablauf mit echten Daten einschließlich Neuladen vorführen.
- [ ] Baustellenpflicht, Kalenderdauer und Archiv-Werkzeug abstimmen.

Status: Draft, keine abgeschlossene Abnahme von LA-03/LA-04/LS-03.
Review und Merge durch Peter oder Anton.
