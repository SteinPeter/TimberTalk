# F<nr> – <Name des Features> (Handbuch-Kapitel)

<!-- Kopieren nach docs/handbuch/F<nr>-<name>.md, z. B. F03-kunden.md.
     Jedes fachliche Feature hat genau ein solches Kapitel. Es beschreibt, WIE der Code das
     Feature umsetzt – was es können soll, steht im Steckbrief unter docs/features/.
     Das allgemeine Handbuch docs/handbuch.md wird dafür nicht geändert. -->

> **Steckbrief:** `docs/features/F<nr>-<name>.md` · **Pate:** <Name> · **Stand:** <Datum>

## Dateien

| Datei | Wofür |
| --- | --- |
| `backend/timbertalk/features/<name>/models.py` | <Tabellen> |
| `backend/timbertalk/features/<name>/service.py` | <Logik> |
| `backend/timbertalk/features/<name>/api.py` | <Endpunkte> |
| `backend/timbertalk/features/<name>/test_<name>.py` | <was geprüft wird> |
| `frontend/features/<id>/<id>.js` | <was der Reiter zeigt> |

## Endpunkte

| Methode und Adresse | Service-Funktion | Was sie tut |
| --- | --- | --- |
| `GET /api/<name>` | `list_<...>()` | <…> |

## Tabellen

| Tabelle | Spalten (wichtigste) | Verweist auf |
| --- | --- | --- |
| `<tabelle>` | <…> | <andere Tabelle oder –> |

## Weg einer typischen Anfrage

<Ein Beispiel Schritt für Schritt: Reiter → getJson → api.py → service.py → Tabelle → zurück.>

## Abhängigkeiten zu anderen Features

<Welche Service-Funktionen anderer Features hier aufgerufen werden – oder „keine“.
Andere Features werden nur über ihre service.py benutzt, nie über ihre Tabellen.>

## Begriffe

<Neue Fachbegriffe dieses Features und ihr Name im Code – oder „keine“.>
