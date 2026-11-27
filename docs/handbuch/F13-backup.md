# F13 – Einstellungen exportieren und importieren (Handbuch-Kapitel)

> **Steckbrief:** `docs/features/F13-backup.md` · **Pate:** <offen> · **Stand:** 2026-11-27

## Dateien

| Datei | Wofür |
| --- | --- |
| `backend/timbertalk/features/backup/models.py` | Keine Tabellen. Das Dateiformat: `SettingsFile` (mit `format`, `version`), `MaterialOut`, `ResourceOut`; die Antwort `ImportResult`. |
| `backend/timbertalk/features/backup/service.py` | `export_settings()` und `import_settings()`. |
| `backend/timbertalk/features/backup/api.py` | Endpunkte unter `/api/backup`. |
| `backend/timbertalk/features/backup/test_backup.py` | Export vollständig, Hin und Zurück in eine leere Datenbank, Import ergänzt nur und ist wiederholbar, falsche Datei, Recht. |
| `frontend/features/settings/sections/backup.js` | Abschnitt „Export und Import“: „Alles exportieren“ und „Importieren …“. |

## Endpunkte

| Methode und Adresse | Recht | Service-Funktion | Was sie tut |
| --- | --- | --- | --- |
| `GET /api/backup/settings` | `finance.edit` | `export_settings()` | Alle Einstellungen als ein JSON-Objekt. |
| `POST /api/backup/settings` | `finance.edit` | `import_settings()` | Übernimmt eine exportierte Datei; Antwort: was neu oder geändert ist. Im Änderungsprotokoll: „Einstellungen importieren“. |

## Tabellen

Keine eigenen. Die Daten liegen in den Tabellen von `materials` (Firma, Stundensätze, Material,
Preise) und `planning` (Fahrzeuge und Maschinen).

## Weg einer typischen Anfrage

1. „Importieren …“ öffnet die Dateiauswahl; `backup.js` liest die Datei mit `file.text()` und
   `JSON.parse()` und fragt mit `window.confirm()`, ob übernommen werden soll.
2. `sendJson("POST", "/api/backup/settings", data)`; FastAPI prüft das Format mit `SettingsFile`.
3. `import_settings()` prüft `format` und `version`, speichert die Firmendaten
   (`materials.save_company()`), die Stundensätze (`save_hourly_rate()`, gleicher Name = ändern),
   legt fehlende Materialien an (gleich = gleicher Name und gleiche Einheit) und trägt nur Preise
   mit einem neuen Gültig-ab-Datum ein. Fahrzeuge und Maschinen werden am Namen erkannt, fehlende
   angelegt, Art und „im Einsatz“ angeglichen, der Kilometersatz gesetzt.
4. Die Antwort `ImportResult` zählt, was neu ist; `backup.js` zeigt es als Satz.

Geld steht in der Datei als Text („0.55“), damit nichts gerundet wird; gelesen wird es als `Decimal`.

## Abhängigkeiten zu anderen Features

- F5 `materials`: `get_company()`, `save_company()`, `list_hourly_rates()`, `save_hourly_rate()`,
  `list_materials()`, `list_prices()`, `create_material()`, `add_price()`.
- F8 `planning`: `list_resources()`, `create_resource()`, `update_resource()`, `set_vehicle_rate()`.

## Begriffe

| Fachbegriff | Im Code |
| --- | --- |
| Einstellungs-Datei | `SettingsFile` (`format = "timbertalk-einstellungen"`) |
