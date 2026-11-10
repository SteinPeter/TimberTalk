# Auftrag für Claude Code: Backend Block 1 – Datenmodell und Datenbank

> **So nutzt du diese Datei:** Lege sie unter `core/docs/auftrag-block1-datenmodell.md` ab und die `CLAUDE.md` in `core/`.
> Starte Claude Code in `core/`, wechsle in den Plan-Modus und schreibe:
> „Lies docs/auftrag-block1-datenmodell.md und CLAUDE.md. Erstelle einen Umsetzungsplan, stelle offene Fragen,
> und setze danach Schritt für Schritt um. Nach jedem Schritt: Tests grün, Commit, kurze Zusammenfassung.“

---

## 1. Ziel

Baue das Fundament des TimberTalk-Backends: Datenmodell, Datenbank, Migrationen, Service-Schicht und eine dünne
REST-API zum Ausprobieren. Danach lassen sich Kunden, Projekte, Arbeitspakete und Buchungen (Stunden, Material,
Fahrten und beliebige weitere Kostenarten) per API anlegen, bestätigen und nachverfolgen.

Zwei Eigenschaften sind wichtiger als Funktionsumfang:

1. **Erweiterbar:** Neue Kostenfaktoren (z. B. Kranmiete, Entsorgung, Gerüst, Zuschläge) und neue Zusatzfelder
   müssen ohne Umbau hinzukommen, möglichst als Daten statt als Code.
2. **MCP-fähig:** Die gesamte Logik liegt in Services, die unabhängig von FastAPI aufrufbar sind. Ein späterer
   MCP-Server soll nur ein dünner Adapter auf dieselben Services sein. Der MCP-Server selbst ist **nicht** Teil
   dieses Auftrags.

## 2. Nicht Teil dieses Auftrags

KI-Agent, Spracherkennung, Modell-Gateway, Rechnungserstellung und E-Rechnung, Routenberechnung, MCP-Server,
Frontend, echte Benutzeranmeldung. Wo diese Teile später andocken, sollen Datenmodell und Services aber schon
passen (siehe Abschnitt 6).

## 3. Technik

- Python 3.12, `uv`, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2, pydantic-settings, pytest, ruff, mypy
- SQLite als Standard-DB (Datei im Datenverzeichnis), Postgres muss ebenfalls funktionieren
- Auth vorerst nur als Platzhalter: fester API-Key aus `.env`, Akteur wird aus Header `X-Actor` gelesen.
  Die Service-Schicht arbeitet trotzdem schon mit einem echten `ServiceContext` (Akteur-ID, Akteur-Typ
  `user | agent | system`, Quelle, Korrelations-ID).

## 4. Projektstruktur

```
core/
├── CLAUDE.md
├── pyproject.toml
├── alembic.ini
├── .env.example
├── migrations/
├── docs/
│   ├── auftrag-block1-datenmodell.md
│   ├── datenmodell.md          # ER-Diagramm (Mermaid) + Erklärung, wird in diesem Auftrag erstellt
│   └── ki-nutzung.md
├── src/timbertalk_core/
│   ├── config.py
│   ├── context.py              # ServiceContext
│   ├── errors.py               # fachliche Fehler (NotFound, Conflict, InvalidState, ValidationFailed)
│   ├── db/
│   │   ├── base.py             # DeclarativeBase, Naming-Convention für Constraints
│   │   ├── mixins.py           # IdMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, AttributesMixin
│   │   ├── types.py            # Money, Quantity, UUID-Hilfen
│   │   └── session.py          # Engine, Session-Factory, SQLite-Pragmas
│   ├── operations.py           # Registry: @operation(...) markiert Service-Funktionen (für späteres MCP)
│   ├── domain/
│   │   ├── company/            # Firmendaten, Einstellungen, Steuersätze
│   │   ├── reference/          # Einheiten, Kostenarten, Zusatzfeld-Definitionen
│   │   ├── people/             # Mitarbeiter (optional mit Benutzer-Verknüpfung)
│   │   ├── customers/
│   │   ├── projects/           # Projekte, Arbeitspakete, Abhängigkeiten
│   │   ├── catalog/            # Materialkatalog, Preise mit Gültigkeit
│   │   ├── bookings/           # einheitliche Buchungen + Details pro Art
│   │   ├── attachments/        # Metadaten zu Dateien (Fotos, Belege)
│   │   ├── audit/              # Audit-Log
│   │   └── usage/              # KI-Verbrauch und Modellpreise
│   ├── api/
│   │   ├── app.py
│   │   ├── deps.py             # Session, ServiceContext aus Request
│   │   ├── errors.py           # Fehler → HTTP (Problem-JSON)
│   │   └── routers/            # ein Router pro Domäne, nur Adapter
│   └── scripts/
│       └── seed.py             # Beispieldaten einer Zimmerei
└── tests/
```

## 5. Datenmodell

Alle Tabellen haben zusätzlich: `id` (UUID), `created_at`, `updated_at`, `deleted_at`, `version`.
Tabellen mit `attributes` (JSON) erlauben Zusatzfelder laut `custom_field_definitions`.

### 5.1 Stamm- und Referenzdaten

| Tabelle | Wichtige Felder | Zweck |
| --- | --- | --- |
| `company` | name, street, zip, city, country, tax_number, vat_id, iban, bic, phone, email, home_lat, home_lon | Firmendaten (genau ein Datensatz); Standort für spätere Fahrtkosten |
| `settings` | key (unique), value (JSON) | Frei erweiterbare Einstellungen, z. B. Standard-Stundensatz, Zahlungsziel |
| `tax_rates` | code, percent (Quantity), valid_from, valid_to, label | Steuersätze mit Gültigkeit (19 %, 7 %, 0 %) |
| `units` | code (unique, z. B. `h`, `km`, `m3`, `lfm`, `m2`, `stk`, `kg`, `pausch`), label_de, decimals | Einheiten mit Anzeige-Genauigkeit |
| `cost_types` | code (unique), name_de, kind, default_unit_code, default_unit_price (Money, nullable), tax_rate_code, labor_share (bool, für § 35a), active, sort_order, attributes | **Kostenarten als Daten.** Neue Faktoren = neuer Datensatz |
| `custom_field_definitions` | entity_type, key, label_de, data_type (`text \| int \| decimal \| date \| bool \| enum`), unit_code, required, enum_values (JSON), active | Beschreibt erlaubte Zusatzfelder in `attributes` |

`cost_types.kind` ist eine feste, kleine Liste, die das Verhalten bestimmt:
`labor` (Arbeitszeit), `material`, `travel` (Fahrt), `equipment` (Geräte, Kran, Gerüst), `other` (Pauschalen,
Entsorgung …). Zuschläge in Prozent sind ausdrücklich **später**, das Modell soll sie aber nicht verbauen.

### 5.2 Personen, Kunden, Projekte

| Tabelle | Wichtige Felder | Zweck |
| --- | --- | --- |
| `employees` | first_name, last_name, role (`owner \| master \| journeyman \| apprentice \| office`), default_cost_type_code, active, attributes | Wer arbeitet; Login-Benutzer kommen später, Verknüpfung über `user_id` (nullable) vorbereiten |
| `customers` | customer_type (`private \| business`), display_name, company_name, first_name, last_name, street, zip, city, country, email, phone, vat_id, is_construction_business (bool, für § 13b), notes, attributes | Kunden; Privat/Gewerbe steuert später Rechnungsregeln |
| `projects` | customer_id, number (lesbar, z. B. `2026-014`), title, status (`inquiry \| planned \| active \| done \| cancelled`), site_street, site_zip, site_city, site_lat, site_lon, planned_start, planned_end, description, attributes | Auftrag/Baustelle |
| `work_packages` | project_id, title, status, planned_start, planned_end, planned_hours (Quantity), sort_order, cad_ref (nullable, Platzhalter für Modul B), attributes | Arbeitspakete für Gantt |
| `work_package_dependencies` | predecessor_id, successor_id, type (`finish_to_start`) | Abhängigkeiten für Gantt |

### 5.3 Material und Preise

| Tabelle | Wichtige Felder | Zweck |
| --- | --- | --- |
| `material_items` | sku (optional), name, category (`timber \| fasteners \| insulation \| membrane \| other`), wood_species, grade, width_mm, height_mm, length_mm, unit_code, cost_type_code, active, attributes | Materialkatalog |
| `prices` | target_type (`material_item \| cost_type`), target_id, unit_price (Money), currency, valid_from, valid_to (nullable), source (`manual \| import \| supplier`), note | Preise mit Gültigkeitszeitraum; Holzpreise ändern sich häufig |

Service-Funktion `get_price(target, on_date)` liefert den gültigen Preis. Überlappende Gültigkeiten für dasselbe Ziel
sind ein Fehler.

### 5.4 Buchungen (Kern der Erweiterbarkeit)

**Eine** Tabelle für alle Kostenfaktoren statt getrennter Tabellen für Stunden, Material und Fahrten:

| Feld | Bedeutung |
| --- | --- |
| `project_id`, `work_package_id` (nullable) | Zuordnung |
| `cost_type_id` | Kostenart; bestimmt über `kind`, welche Details gelten |
| `booking_date` | Leistungstag |
| `quantity` (Quantity), `unit_code` | Menge und Einheit |
| `unit_price` (Money, nullable) | Nur gesetzt, wenn abweichend vom Preis; sonst später über `get_price` |
| `employee_id` (nullable) | Pflicht bei `labor` |
| `material_item_id` (nullable) | Optional bei `material` |
| `description` | Freitext |
| `details` (JSON) | Art-spezifische Felder, validiert über Pydantic-Schema je `kind` |
| `status` | `draft \| confirmed \| locked \| cancelled` |
| `source`, `source_ref` | `manual \| agent \| voice \| import \| cad` und Verweis (z. B. Transkript-ID) |
| `confirmed_by`, `confirmed_at` | Wer hat bestätigt |
| `attributes` | Zusatzfelder |

Details-Schemas je `kind` (in `bookings/details.py`, registriert in einer Registry, damit neue Arten nur ein
Schema + Registrierung brauchen):

- `labor`: `start_time`, `end_time` (optional), `break_minutes`
- `travel`: `from_label`, `to_label`, `distance_method` (`manual \| route`), `round_trip` (bool), `vehicle`
- `material`: `delivery_note_ref` (optional)
- `equipment`: `equipment_name`, `hours_or_days`
- `other`: keine Pflichtfelder

Regeln im Service:

- Einträge mit `source` ≠ `manual` starten immer als `draft`.
- `confirm_booking` nur durch Akteur-Typ `user`.
- `locked` und `cancelled` sind unveränderbar; `locked` wird erst von der späteren Rechnung gesetzt.
- Einheit muss zur Kostenart passen, sonst Fehler.

### 5.5 Anhänge, Audit, KI-Verbrauch

| Tabelle | Wichtige Felder | Zweck |
| --- | --- | --- |
| `attachments` | entity_type, entity_id, file_path (relativ zum Datenverzeichnis), mime_type, size_bytes, sha256, kind (`photo \| delivery_note \| invoice_in \| cad \| other`), captured_at, lat, lon | Nur Metadaten; Dateien liegen im Dateisystem |
| `audit_events` | occurred_at, actor_type, actor_id, action (`create \| update \| delete \| confirm \| cancel \| …`), entity_type, entity_id, changes (JSON: Feld → alt/neu), source, correlation_id | Änderungsprotokoll; nur anhängen, nie ändern |
| `model_prices` | provider, model, input_per_mtok (Money), output_per_mtok (Money), currency, valid_from | Preise je Million Tokens, ohne Code-Änderung pflegbar |
| `llm_usage` | occurred_at, provider, model, module (`a \| b`), feature, actor_id, project_id (nullable), input_tokens, output_tokens, cost (Money), request_id, success | Grundlage für die Kostenübersicht auf Handy, PC und im Verwaltungs-Tool |

Das Audit-Log wird zentral erzeugt: über einen Helfer in der Service-Basis oder SQLAlchemy-Events, die
`ServiceContext` kennen. Kein Service schreibt Audit-Einträge von Hand.

## 6. Vorbereitung für später (nur Struktur, keine Umsetzung)

- **MCP:** Jede öffentliche Service-Funktion wird mit `@operation(name="booking.create", read_only=False,
  summary_de="…")` registriert. `operations.py` kann alle Operationen mit Eingabe- und Ausgabe-Schema auflisten.
  Ein Test prüft, dass jede registrierte Operation Docstring und Pydantic-Schemas hat.
- **Synchronisation (native App):** `updated_at` und `version` überall, Soft Delete statt Löschen.
  Ein Service `list_changes(entity_type, since)` reicht vorerst als Funktion ohne Endpunkt.
- **Rechnung (Block 3):** Buchungen bekommen später ein `invoice_id`. Rechnungspositionen werden dann als
  Schnappschuss mit Preis und Steuersatz kopiert, nicht verlinkt.
- **CAD (Modul B):** `work_packages.cad_ref` und `bookings.source = cad` sind die Andockpunkte.

## 7. Umsetzungsschritte

Jeder Schritt endet mit grünen Tests, ruff, mypy und einem Commit (`feat(core): …`).

1. **Gerüst:** `pyproject.toml`, Ordner, `config.py`, `.env.example`, ruff/mypy/pytest-Konfiguration, leere App mit `/health`.
2. **DB-Grundlage:** `base.py` mit Naming-Convention, Mixins, `Money`/`Quantity`-Typen, Session mit SQLite-Pragmas,
   Alembic eingerichtet. Tests: Decimal-Rundreise ohne Verlust auf SQLite (z. B. `Decimal("489.5000")`, `Decimal("0.30")`).
3. **ServiceContext, Fehler, Audit, Operation-Registry:** zentrale Bausteine inklusive Tests.
4. **Referenzdaten:** company, settings, tax_rates, units, cost_types, custom_field_definitions + Validierung von `attributes`.
5. **Personen, Kunden, Projekte, Arbeitspakete** inklusive Abhängigkeiten (Zyklen verhindern).
6. **Katalog und Preise** inklusive `get_price` und Prüfung auf überlappende Gültigkeit.
7. **Buchungen** mit Details-Registry, Statusübergängen und Regeln aus 5.4.
8. **Anhänge, model_prices, llm_usage** inklusive Service `record_usage` (berechnet Kosten aus `model_prices`)
   und `usage_summary(period, group_by)`.
9. **REST-API:** ein Router pro Domäne (Liste mit Filter und Paging, Lesen, Anlegen, Ändern, Soft Delete;
   bei Buchungen zusätzlich `confirm` und `cancel`). Fehler als Problem-JSON. OpenAPI muss vollständig sein.
10. **Seed und Doku:** `seed.py` mit einer Beispiel-Zimmerei (siehe 8), `docs/datenmodell.md` mit Mermaid-ER-Diagramm
    und kurzer Erklärung, wie man eine neue Kostenart und ein neues Zusatzfeld hinzufügt.

## 8. Beispieldaten für `seed.py`

- Betrieb: „Zimmerei Muster GmbH“, Berlin
- Einheiten: h, km, m3, lfm, m2, stk, kg, pausch
- Kostenarten: Lohn Meister, Lohn Geselle, Lohn Azubi (labor, h, labor_share = true); Fahrtkosten (travel, km);
  Holz (material, m3); Verbindungsmittel (material, stk); Dämmung (material, m2); Kran (equipment, h);
  Entsorgung (other, pausch)
- Material: KVH Fichte C24 60×200 und 80×240, BSH GL24h 100×280, Dachlatte 30×50 mit Preisen und `valid_from`
- Zwei Kunden (privat und gewerblich), zwei Projekte (Dachgaube, Carport), Arbeitspakete mit Abhängigkeit
- Ein paar Buchungen in allen Status
- Alle Preise sind Platzhalter und so gekennzeichnet.

## 9. Abnahmekriterien

- [ ] `uv run alembic upgrade head` erzeugt die DB auf SQLite fehlerfrei; Downgrade und erneutes Upgrade funktionieren.
- [ ] Optional: dieselben Migrationen laufen gegen Postgres (Test-Job über Umgebungsvariable).
- [ ] Geldbeträge und Mengen gehen auf SQLite ohne Rundungsfehler hin und zurück.
- [ ] Eine neue Kostenart (z. B. „Gerüst“, equipment, Tag) lässt sich nur über API bzw. Seed anlegen und sofort buchen,
      ohne Code-Änderung.
- [ ] Ein neues Zusatzfeld (z. B. `customers.attributes.referral_source`) lässt sich über `custom_field_definitions`
      anlegen und wird validiert.
- [ ] Buchungen aus `source=agent` sind `draft`; Bestätigung durch `actor_type=agent` wird abgelehnt.
- [ ] `locked`-Buchungen lassen sich nicht ändern.
- [ ] Jede schreibende Operation erzeugt genau einen Audit-Eintrag mit Änderungen.
- [ ] `get_price` liefert für ein Datum den richtigen Preis; überlappende Preise werden abgelehnt.
- [ ] `operations.py` listet alle Service-Operationen mit Schemas; kein Router enthält DB-Zugriffe.
- [ ] Testabdeckung der Service-Schicht mindestens 80 %.
- [ ] `docs/datenmodell.md` erklärt das Modell und die Erweiterungswege.

## 10. Arbeitsweise

- Zuerst Plan vorlegen und offene Fragen stellen, dann umsetzen.
- Kleine Commits pro Schritt. Keine Funktionen außerhalb dieses Auftrags vorziehen.
- Bei Unklarheit im Fachlichen (Steuer, Zimmerei-Begriffe) nicht raten, sondern als Frage im Plan notieren.
- Am Ende: kurze Zusammenfassung, was fertig ist, was offen ist, und Vorschläge für Block 2.
