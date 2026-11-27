# KI-Nutzung – Nacharbeit AP-1.5

| Datum | Modell/Werkzeug | Aufgabe |
| --- | --- | --- |
| 2026-11-23 | OpenAI Codex (ChatGPT) | Projektansicht korrigiert; Ruff, Formatprüfung und Backend-Tests ausgeführt; Browserprüfung mit simulierten Nachbarservices; Dokumentation und Draft-PR-Text aktualisiert |

Grundlage ist die vom Nutzer lokal getestete Projektfassung. Produktiv geändert
wurde nur `frontend/features/projects/projects.js`; dazu wurden die eigenen
Feature-Dokumente aktualisiert oder ergänzt. Gemeinsame Dateien und fremde
Feature-Ordner bleiben unverändert. Keine Projektabhängigkeit wurde ergänzt.

Der alte Fehler wurde im Browser reproduziert: Nach Bestätigung blieb „Bearbeiten“
deaktiviert. Dieselbe Prüfung besteht mit der korrigierten Datei. Insgesamt bestehen
15 lokale Browserprüfungen mit Chrome und bereits vorhandenen Prüfwerkzeugen außerhalb
des Repositorys. Kunden, Entwürfe, Bestätigung und der vorgeschlagene POST-Helfer
werden nur im Prüfaufbau simuliert, nicht in produktiven Dateien.

Ruff und Formatprüfung bestehen; 46 Backend-Tests bestehen. Der reguläre Pytest-Lauf
meldete eine bekannte Starlette/httpx-Abkündigung und ein lokales Cacheproblem.
Mit deaktiviertem Cache bestanden erneut 46 Tests, nur mit der Abkündigungswarnung.
Details: `docs/features/F3-projects-pruefung.md`.

Ergebnis ist ein aktualisierter Arbeitsstand und ein vorbereiteter Draft-PR-Text.
Kein Push, keine Veröffentlichung oder Nachricht an Teammitglieder und kein Merge
wurden durchgeführt. Echte Integration bleibt offen.
