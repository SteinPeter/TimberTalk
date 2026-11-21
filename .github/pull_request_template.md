<!-- Diese Vorlage füllt sich beim Öffnen eines Pull Requests von selbst.
     Vier Fragen, kurz beantwortet – das ist die Grundlage für die Durchsicht im Meeting. -->

## Was kann man jetzt?

<Ein bis drei Sätze ohne Fachsprache: was nach diesem Pull Request möglich ist.
Dazu der Steckbrief: docs/features/F<nr>-<name>.md>

## Wie probiere ich es aus?

```bash
cd backend
uv sync
uv run timbertalk
```

<Was danach zu sehen oder zu tun ist.>

## Welche Dateien sind neu?

| Datei | Wofür |
| --- | --- |
| | |

## Was ist neu zu verstehen?

<Technik, Begriff oder Regel, die hier zum ersten Mal vorkommt – oder „nichts Neues“.>

## Vor der Durchsicht geprüft

- [ ] `uv run ruff check .` und `uv run ruff format --check .` sind grün
- [ ] `uv run pytest` ist grün
- [ ] Steckbrief vorhanden und die Abnahmepunkte stimmen
- [ ] Handbuch beschreibt den neuen Stand: Kapitel `docs/handbuch/<feature>.md` (Feature) oder `docs/handbuch.md` (Grundgerüst)
- [ ] Oberfläche geändert? Mit dem Skill `apple-design` durchgesehen, Seiten unter „Was ist neu zu verstehen?“ genannt
- [ ] KI-Nutzung als eigene Datei `docs/ki-nutzung/<datum>-<thema>.md` eingetragen
