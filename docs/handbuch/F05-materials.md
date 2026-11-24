# F5 – Material, Fahrten und Preise (Handbuch-Kapitel)

> **Steckbrief:** `docs/features/F05-materials.md` · **Pate:** Tingyu Li · **Stand:** 2026-11-21

## Dateien

| Datei | Wofür |
| --- | --- |
| `backend/timbertalk/features/materials/models.py` | Die Tabellen, der Spaltentyp `DecimalText` und die Antwort- und Eingabeklassen (ohne Tabelle). |
| `backend/timbertalk/features/materials/service.py` | Die Logik: Materialstamm, Preise, Stammdaten, Buchen, Entwürfe, Kosten. |
| `backend/timbertalk/features/materials/api.py` | Die Endpunkte unter `/api/materials`. |
| `backend/timbertalk/features/materials/tools.py` | Die vier Werkzeuge nach S-09/S-14 mit einem kleinen eigenen Katalog (`TOOLS`) und `call_tool()`. |
| `backend/timbertalk/features/materials/test_materials.py` | Tests für Service, Endpunkte und Werkzeuge. |
| `frontend/features/bookings/sections/materials.js` | Abschnitt „Material und Fahrten“ im Reiter „Buchungen“ (`id` `materials`). |
| `frontend/features/bookings/materials-helpers.js` | Kleine Helfer: Elemente bauen, Daten senden (`sendJson`), Zahlen und Daten anzeigen. Auch die Abschnitte in „Einstellungen“ benutzen sie. Sie liegt bewusst nicht in `sections/`, dort dürfen nur Abschnitte liegen. |
| `frontend/features/settings/sections/materials-master.js` | Abschnitt „Materialstamm“ im Reiter „Einstellungen“. |
| `frontend/features/settings/sections/materials-company.js` | Abschnitt „Firma und Bank“ im Reiter „Einstellungen“: Firma, Logo, Bank, Fahrtkosten, Umsatzsteuer und Stundensätze. |

In gemeinsamen Dateien geändert (mit Peter oder Anton abzustimmen):

| Datei | Änderung |
| --- | --- |
| `frontend/features/bookings/sections.js` | Eine `import`-Zeile und ein Eintrag in `SECTIONS` für den Abschnitt `materials`. `bookings.js` bleibt unverändert (F0e). |
| `frontend/features/settings/sections.js` | Zwei `import`-Zeilen und zwei Einträge in `SECTIONS` für `materials-company` und `materials-master`. `settings.js` bleibt unverändert (F0e). |
| `frontend/style.css` | Ein Block am Ende mit Klassen `materials-…` (Formulare, Tabellen, Kostenkasten). Keine neuen Farben. |

## Endpunkte

| Methode und Adresse | Service-Funktion | Was sie tut |
| --- | --- | --- |
| `GET /api/materials/items?kategorie=&on_date=` | `list_materials()` | Materialliste mit dem Preis des Tages (heute, wenn `on_date` fehlt). |
| `POST /api/materials/items` | `create_material()` | Legt ein Material an. |
| `GET /api/materials/items/{id}/prices` | `list_prices()` | Alle Preise eines Materials, der neueste zuerst. |
| `POST /api/materials/items/{id}/prices` | `add_price()` | Trägt einen Preis mit Gültigkeitsdatum ein. |
| `GET /api/materials/company` | `get_company()` | Stammdaten der Abrechnung. |
| `PUT /api/materials/company` | `save_company()` | Speichert sie. |
| `GET /api/materials/hourly-rates` | `list_hourly_rates()` | Alle Stundensätze. |
| `PUT /api/materials/hourly-rates` | `save_hourly_rate()` | Legt einen Stundensatz an; gleicher Name ändert den Satz. |
| `DELETE /api/materials/hourly-rates/{id}` | `delete_hourly_rate()` | Löscht einen Stundensatz. |
| `GET /api/materials/bookings?project_id=` | `list_bookings()` | Buchungen eines Projekts mit Beschreibung, Betrag und Status. |
| `POST /api/materials/bookings/material` | `book_material()` | Bucht Material, zählt sofort zu den Kosten. |
| `POST /api/materials/bookings/travel` | `book_travel()` | Bucht eine Fahrt (km), zählt sofort zu den Kosten. |
| `GET /api/materials/projects/{id}/costs` | `project_costs()` | Kosten eines Projekts: Stunden, Material, Fahrten, Summe (netto). |

Meldet der Service einen Fehler, antwortet die API mit einem deutschen Text: `LookupError` → 404
(„gibt es nicht“), `ValueError` → 422 („Angabe passt nicht“). Dafür gibt es die Hilfsfunktion
`_run()` in `api.py`.

Nur für andere Features und die KI, ohne eigenen Endpunkt: `list_materials()` (S-04),
`book_material_draft()` (S-05), `book_travel_draft()`, `confirm_draft()` in `service.py` und die
Werkzeuge in `tools.py`.

## Tabellen

Alle Namen beginnen mit `materials_`. Geld und Mengen sind `DecimalText` (Text in der Datenbank,
`Decimal` in Python).

| Tabelle | Spalten (wichtigste) | Verweist auf |
| --- | --- | --- |
| `materials_item` | `name`, `category`, `unit` | – |
| `materials_price` | `material_id`, `unit_price`, `valid_from` | `materials_item` |
| `materials_company` | `company_name`, `address`, `logo`, `bank_name`, `iban`, `bic`, `travel_rate_per_km`, `vat_rate` – genau eine Zeile (`id` = 1) | – |
| `materials_hourly_rate` | `name`, `rate` | – |
| `materials_booking` | `project_id`, `kind` (`material` oder `travel`), `booking_date`, `status` (`draft` oder `confirmed`), `draft_id`, `material_id`, `design_id`, `quantity`, `unit`, `unit_price` | `materials_item` (nur bei Material) |

- `project_id` ist nur eine Zahl, ohne Verweis: Die Projekte liegen in F3.
- Bei einer Fahrt ist `quantity` die Strecke in km, `unit` ist `km` und `unit_price` der Satz je km.
- `unit_price` der Buchung ist der Preis vom Buchungstag, in der Buchung festgehalten.
- Das Logo steht als `data:image/…`-Text in `materials_company.logo` (höchstens 500 000 Zeichen).
- Alle Zahlen, die in die Tabellen kommen (Menge, km, Preis, Stundensatz, Fahrtsatz), prüft
  `_require_amount()` in `service.py`: Sie müssen endlich sein (kein `Infinity`, kein `NaN`) und
  zwischen 0 und `MAX_AMOUNT` (1 000 000) liegen. Sonst ließen sich die Kosten eines Projekts
  nicht mehr berechnen. Menge und km müssen zusätzlich größer als 0 sein. Die Projektnummer prüft
  `_require_project()` bei jedem Zugriff auf ein Projekt: eine ganze Zahl ab 1.

## Weg einer typischen Anfrage

Material buchen im Reiter „Buchungen“:

1. Der Zimmerer gibt die Projektnummer ein, wählt ein Material, ein Datum und eine Menge und
   klickt „Material buchen“. `sections/materials.js` macht aus „2,5“ den Text „2.5“.
2. `sendJson()` in `materials-helpers.js` schickt `POST /api/materials/bookings/material`.
3. `book_material()` in `api.py` ruft `service.book_material()` auf (über `_run()`).
4. Der Service prüft Projektnummer, Menge und Material, holt mit `current_price()` den Preis, der am
   Buchungstag gilt, und speichert eine `Booking`-Zeile mit `status = "confirmed"`.
5. Die Antwort geht zurück. Der Reiter lädt `GET …/projects/12/costs` und `GET …/bookings` neu und
   zeigt Kosten und Liste. Fehler (z. B. „Für … gibt es am … keinen Preis“) erscheinen als Meldung
   unter dem Formular.

Dieselbe Buchung durch die KI: `call_tool(session, "material_buchen", args)` in `tools.py` ruft
`service.book_material_draft()`. Die Buchung bekommt `status = "draft"` und eine `draft_id`; sie
zählt erst nach `confirm_draft()` zu den Kosten.

## Werkzeuge (S-09, S-14)

`tools.py` hat den Dekorator `@werkzeug(name, beschreibung, art, schema_ein, schema_aus, beispiel,
modul)` mit den Feldern aus S-09 und den Katalog `TOOLS`. Ein doppelter Name bricht beim Import mit
`RuntimeError` ab. `beispiel` besteht aus `args` (Beispielaufruf) und `ergebnis` (dokumentiertes
Ergebnis).

| Werkzeug | Art | Service-Funktion |
| --- | --- | --- |
| `material_suchen` | lesen | `search_materials()` |
| `material_buchen` | entwurf | `book_material_draft()` |
| `fahrt_buchen` | entwurf | `book_travel_draft()` |
| `projekt_kosten` | lesen | `project_costs()` |

`call_tool(session, name, args)` ist die kleine Fassung des `call_tool` aus S-09: unbekanntes
Werkzeug → `fehler` „unbekannt“, fehlende Pflichtangabe → `rueckfrage`, unpassende Angabe →
`fehler` „ungueltig“. Das gilt auch für einen falschen Typ (z. B. `projekt_id` als Text), ein
unbekanntes Argument und eine Zahl, mit der man nicht rechnen kann: `call_tool` fängt neben
`ValueError` und `LookupError` auch `TypeError` und `ArithmeticError` ab und verwirft dabei, was
halb geschrieben war (`session.rollback()`). Es stürzt nie ab. Geld wird als Dezimal-Text („450.00“), Datum als `JJJJ-MM-TT` übergeben.

Der Test ruft jedes Werkzeug mit seinem `beispiel` auf einer Datenbank mit festen Beispieldaten
(`seed_example_data()` in `test_materials.py`: Material 1 „Konstruktionsvollholz C24“ zu 450 Euro
je m³, Fahrtsatz 0,50 Euro je km, zwei bestätigte Buchungen auf Projekt 12) auf und prüft, dass
`ergebnis` im tatsächlichen Ergebnis enthalten ist.

Der Katalog wird noch nirgends geladen, denn die KI und der gemeinsame Baustein (AP-0.5) gibt es
noch nicht. Sobald `@werkzeug` aus dem Kern da ist, wird nur der Dekorator in `tools.py` getauscht.

## Abhängigkeiten zu anderen Features

Keine. Dieses Feature ruft kein anderes Feature auf.

Andere rufen dieses auf:

- Team B (S-04, S-05): `list_materials()` und `book_material_draft()`.
- F7 (Entwurf, Bestätigung): `confirm_draft()`; die `draft_id` ist bis dahin die Nummer des Entwurfs.
- F9 (Rechnung): `get_company()`, `list_hourly_rates()` und `project_costs()`.
- `hours` (Stunden) und F3 (Projekte): Sobald deren Services da sind, kommen die Stundenkosten in
  `project_costs()` und die Prüfung der Projektnummer in `_require_project()` dazu.

## Begriffe

| Begriff | Im Code |
| --- | --- |
| Materialstamm | `MaterialItem` |
| Preis, gültig ab | `MaterialPrice` (`unit_price`, `valid_from`) |
| Stammdaten der Abrechnung | `Company` |
| Stundensatz | `HourlyRate` |
| Buchung (Material oder Fahrt) | `Booking` mit `kind` |
| Entwurf | `Booking` mit `status = "draft"` und `draft_id` |
| Projektkosten | `ProjectCosts` (`hours`, `material`, `travel`, `total_net`) |
| Werkzeug | `Tool` in `tools.py` |
