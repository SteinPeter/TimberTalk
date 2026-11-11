/**
 * Beschreibung der Seiten – Daten, kein Code.
 *
 * Je Ressource stehen hier Pfad, Fähigkeiten, Tabellenspalten, Filter und
 * Formularfelder. `app.js` baut daraus Tabelle, Filterzeile und Formular.
 * Eine neue Seite ist damit ein Eintrag in dieser Datei.
 *
 * Feldtypen: text, textarea, int, decimal, date, time, bool, enum, ref, json.
 * `aufzaehlung` nennt die Werteliste der API (Name der Python-Klasse, aus
 * /openapi.json gelesen), `bezug` eine Nachschlageliste aus NACHSCHLAGEN.
 * `nurAnlegen` markiert Felder, die kein Update-Schema kennt.
 */

/**
 * Nachschlagelisten für Auswahlfelder.
 *
 * `wert` ist das Feld, das an die API geht. Nicht überall ist das eine UUID:
 * Einheit, Kostenart und Steuersatz werden in manchen Schemas über ihren Code
 * verwiesen – darum steht `wert` getrennt von der Anzeige.
 */
export const NACHSCHLAGEN = {
  kunden: { pfad: "/customers", wert: "id", anzeige: (k) => k.display_name },
  projekte: { pfad: "/projects", wert: "id", anzeige: (p) => `${p.number} · ${p.title}` },
  arbeitspakete: { pfad: "/work-packages", wert: "id", anzeige: (a) => a.title },
  kostenarten: { pfad: "/cost-types", wert: "id", anzeige: (k) => `${k.code} · ${k.name_de} (${k.kind})` },
  kostenarten_code: { pfad: "/cost-types", wert: "code", anzeige: (k) => `${k.code} · ${k.name_de}` },
  einheiten: { pfad: "/units", wert: "code", anzeige: (e) => `${e.code} · ${e.label_de}` },
  mitarbeiter: { pfad: "/employees", wert: "id", anzeige: (m) => `${m.display_name} (${m.role})` },
  artikel: { pfad: "/material-items", wert: "id", anzeige: (a) => `${a.name}${a.sku ? ` · ${a.sku}` : ""}` },
  steuersaetze: { pfad: "/tax-rates", wert: "code", anzeige: (s) => `${s.code} · ${s.percent} %` },
};

const SPALTE_VERSION = { key: "version", label: "V", art: "zahl" };

const FELD_ATTRIBUTE = {
  name: "attributes",
  label: "Zusatzfelder (JSON)",
  typ: "json",
  hinweis: "frei erweiterbar, siehe custom_field_definitions",
};

/* --------------------------------------------------------------- Stammdaten */

export const KUNDEN = {
  id: "kunden",
  label: "Kunden",
  pfad: "/customers",
  einzahl: "Kunde",
  caps: { anlegen: true, aendern: true, loeschen: true },
  spalten: [
    { key: "display_name", label: "Name" },
    { key: "customer_type", label: "Art" },
    { key: "zip", label: "PLZ" },
    { key: "city", label: "Ort" },
    { key: "email", label: "E-Mail" },
    { key: "phone", label: "Telefon" },
    { key: "is_construction_business", label: "Bauleistend" },
    SPALTE_VERSION,
  ],
  filter: [
    { name: "search", label: "Suche", typ: "text" },
    { name: "customer_type", label: "Art", typ: "enum", aufzaehlung: "CustomerType" },
  ],
  felder: [
    { name: "customer_type", label: "Art", typ: "enum", aufzaehlung: "CustomerType", pflicht: true },
    { name: "company_name", label: "Firma", typ: "text", hinweis: "bei Art business der Name" },
    { name: "first_name", label: "Vorname", typ: "text" },
    { name: "last_name", label: "Nachname", typ: "text" },
    { name: "display_name", label: "Anzeigename", typ: "text", hinweis: "leer = wird abgeleitet" },
    { name: "street", label: "Straße", typ: "text" },
    { name: "zip", label: "PLZ", typ: "text" },
    { name: "city", label: "Ort", typ: "text" },
    { name: "country", label: "Land", typ: "text", hinweis: "zwei Buchstaben, Vorgabe DE" },
    { name: "email", label: "E-Mail", typ: "text" },
    { name: "phone", label: "Telefon", typ: "text" },
    { name: "vat_id", label: "USt-IdNr.", typ: "text" },
    { name: "is_construction_business", label: "Bauleistender Betrieb", typ: "bool" },
    { name: "notes", label: "Notizen", typ: "textarea" },
    FELD_ATTRIBUTE,
  ],
};

export const EINHEITEN = {
  id: "einheiten",
  label: "Einheiten",
  pfad: "/units",
  einzahl: "Einheit",
  caps: { anlegen: true, aendern: true, loeschen: true },
  spalten: [
    { key: "code", label: "Code" },
    { key: "label_de", label: "Bezeichnung" },
    { key: "decimals", label: "Nachkomma", art: "zahl" },
    { key: "active", label: "Aktiv" },
    { key: "sort_order", label: "Sortierung", art: "zahl" },
    SPALTE_VERSION,
  ],
  filter: [{ name: "active_only", label: "nur aktive", typ: "bool", vorgabe: true }],
  felder: [
    { name: "code", label: "Code", typ: "text", pflicht: true, nurAnlegen: true },
    { name: "label_de", label: "Bezeichnung", typ: "text", pflicht: true },
    { name: "decimals", label: "Nachkommastellen", typ: "int", hinweis: "0 bis 6" },
    { name: "active", label: "Aktiv", typ: "bool", vorgabe: true },
    { name: "sort_order", label: "Sortierung", typ: "int" },
  ],
};

export const MITARBEITER = {
  id: "mitarbeiter",
  label: "Mitarbeiter",
  pfad: "/employees",
  einzahl: "Mitarbeiter",
  caps: { anlegen: true, aendern: true, loeschen: true },
  spalten: [
    { key: "display_name", label: "Name" },
    { key: "role", label: "Rolle" },
    { key: "default_cost_type_code", label: "Kostenart" },
    { key: "email", label: "E-Mail" },
    { key: "phone", label: "Telefon" },
    { key: "active", label: "Aktiv" },
    SPALTE_VERSION,
  ],
  filter: [
    { name: "role", label: "Rolle", typ: "enum", aufzaehlung: "EmployeeRole" },
    { name: "active_only", label: "nur aktive", typ: "bool", vorgabe: true },
  ],
  felder: [
    { name: "first_name", label: "Vorname", typ: "text", pflicht: true },
    { name: "last_name", label: "Nachname", typ: "text", pflicht: true },
    { name: "role", label: "Rolle", typ: "enum", aufzaehlung: "EmployeeRole", pflicht: true },
    { name: "default_cost_type_code", label: "Vorgabe-Kostenart", typ: "ref", bezug: "kostenarten_code" },
    { name: "email", label: "E-Mail", typ: "text" },
    { name: "phone", label: "Telefon", typ: "text" },
    { name: "user_id", label: "Benutzer-ID", typ: "text", hinweis: "UUID, für die spätere Anmeldung" },
    { name: "active", label: "Aktiv", typ: "bool", vorgabe: true },
    FELD_ATTRIBUTE,
  ],
};

export const KOSTENARTEN = {
  id: "kostenarten",
  label: "Kostenarten",
  pfad: "/cost-types",
  einzahl: "Kostenart",
  hinweis:
    "Eine neue Kostenart ist ein Datensatz, kein Code. Die Art (kind) bestimmt, " +
    "welche Detailfelder eine Buchung bekommt.",
  caps: { anlegen: true, aendern: true, loeschen: true },
  spalten: [
    { key: "code", label: "Code" },
    { key: "name_de", label: "Bezeichnung" },
    { key: "kind", label: "Art" },
    { key: "default_unit_code", label: "Einheit" },
    { key: "default_unit_price", label: "Vorgabepreis", art: "zahl" },
    { key: "tax_rate_code", label: "Steuer" },
    { key: "labor_share", label: "Lohnanteil" },
    { key: "active", label: "Aktiv" },
    SPALTE_VERSION,
  ],
  filter: [
    { name: "kind", label: "Art", typ: "enum", aufzaehlung: "CostTypeKind" },
    { name: "active_only", label: "nur aktive", typ: "bool", vorgabe: true },
  ],
  felder: [
    { name: "code", label: "Code", typ: "text", pflicht: true, nurAnlegen: true },
    { name: "name_de", label: "Bezeichnung", typ: "text", pflicht: true },
    { name: "kind", label: "Art", typ: "enum", aufzaehlung: "CostTypeKind", pflicht: true },
    { name: "default_unit_code", label: "Einheit", typ: "ref", bezug: "einheiten", pflicht: true },
    { name: "default_unit_price", label: "Vorgabepreis", typ: "decimal" },
    { name: "tax_rate_code", label: "Steuersatz", typ: "ref", bezug: "steuersaetze" },
    { name: "labor_share", label: "Lohnanteil (§ 35a)", typ: "bool" },
    { name: "active", label: "Aktiv", typ: "bool", vorgabe: true },
    { name: "sort_order", label: "Sortierung", typ: "int" },
    FELD_ATTRIBUTE,
  ],
};

/* ---------------------------------------------------- Projekte und Pakete */

export const PROJEKTE = {
  id: "projekte",
  label: "Projekte",
  pfad: "/projects",
  einzahl: "Projekt",
  hinweis: "Eine Zeile anklicken, um ihre Arbeitspakete zu sehen.",
  caps: { anlegen: true, aendern: true, loeschen: true },
  spalten: [
    { key: "number", label: "Nummer" },
    { key: "title", label: "Titel" },
    { key: "customer_id", label: "Kunde", art: "bezug", bezug: "kunden" },
    { key: "status", label: "Status", art: "status" },
    { key: "planned_start", label: "Beginn" },
    { key: "planned_end", label: "Ende" },
    { key: "site_city", label: "Baustelle" },
    SPALTE_VERSION,
  ],
  filter: [
    { name: "customer_id", label: "Kunde", typ: "ref", bezug: "kunden" },
    { name: "status", label: "Status", typ: "enum", aufzaehlung: "ProjectStatus" },
  ],
  felder: [
    { name: "customer_id", label: "Kunde", typ: "ref", bezug: "kunden", pflicht: true },
    { name: "title", label: "Titel", typ: "text", pflicht: true },
    { name: "number", label: "Nummer", typ: "text", hinweis: "leer = der Service vergibt JJJJ-NNN" },
    { name: "status", label: "Status", typ: "enum", aufzaehlung: "ProjectStatus" },
    { name: "planned_start", label: "Geplanter Beginn", typ: "date" },
    { name: "planned_end", label: "Geplantes Ende", typ: "date" },
    { name: "site_street", label: "Baustelle: Straße", typ: "text" },
    { name: "site_zip", label: "Baustelle: PLZ", typ: "text" },
    { name: "site_city", label: "Baustelle: Ort", typ: "text" },
    { name: "site_lat", label: "Breitengrad", typ: "decimal" },
    { name: "site_lon", label: "Längengrad", typ: "decimal" },
    { name: "description", label: "Beschreibung", typ: "textarea" },
    FELD_ATTRIBUTE,
  ],
};

export const ARBEITSPAKETE = {
  id: "arbeitspakete",
  label: "Arbeitspakete",
  pfad: "/work-packages",
  einzahl: "Arbeitspaket",
  caps: { anlegen: true, aendern: true, loeschen: true },
  spalten: [
    { key: "sort_order", label: "#", art: "zahl" },
    { key: "title", label: "Titel" },
    { key: "status", label: "Status", art: "status" },
    { key: "planned_start", label: "Beginn" },
    { key: "planned_end", label: "Ende" },
    { key: "planned_hours", label: "Geplante Stunden", art: "zahl" },
    { key: "cad_ref", label: "CAD-Verweis" },
    SPALTE_VERSION,
  ],
  filter: [
    { name: "project_id", label: "Projekt", typ: "ref", bezug: "projekte" },
    { name: "status", label: "Status", typ: "enum", aufzaehlung: "WorkPackageStatus" },
  ],
  felder: [
    { name: "project_id", label: "Projekt", typ: "ref", bezug: "projekte", pflicht: true, nurAnlegen: true },
    { name: "title", label: "Titel", typ: "text", pflicht: true },
    { name: "status", label: "Status", typ: "enum", aufzaehlung: "WorkPackageStatus" },
    { name: "planned_start", label: "Geplanter Beginn", typ: "date" },
    { name: "planned_end", label: "Geplantes Ende", typ: "date" },
    { name: "planned_hours", label: "Geplante Stunden", typ: "decimal" },
    { name: "sort_order", label: "Sortierung", typ: "int" },
    { name: "cad_ref", label: "CAD-Verweis", typ: "text" },
    { name: "description", label: "Beschreibung", typ: "textarea" },
    FELD_ATTRIBUTE,
  ],
};

/* ---------------------------------------------------------------- Buchungen */

export const BUCHUNGEN = {
  id: "buchungen",
  label: "Buchungen",
  pfad: "/bookings",
  einzahl: "Buchung",
  caps: { anlegen: true, aendern: true, loeschen: true },
  spalten: [
    { key: "booking_date", label: "Datum" },
    { key: "project_id", label: "Projekt", art: "bezug", bezug: "projekte" },
    { key: "cost_type_code", label: "Kostenart" },
    { key: "cost_type_kind", label: "Art" },
    { key: "quantity", label: "Menge", art: "zahl" },
    { key: "unit_code", label: "Einheit" },
    { key: "effective_unit_price", label: "Preis/Einheit", art: "zahl" },
    { key: "amount", label: "Betrag", art: "zahl" },
    { key: "price_origin", label: "Preisherkunft" },
    { key: "employee_id", label: "Mitarbeiter", art: "bezug", bezug: "mitarbeiter" },
    { key: "status", label: "Status", art: "status" },
    { key: "source", label: "Quelle" },
    SPALTE_VERSION,
  ],
  filter: [
    { name: "project_id", label: "Projekt", typ: "ref", bezug: "projekte" },
    { name: "work_package_id", label: "Arbeitspaket", typ: "ref", bezug: "arbeitspakete" },
    { name: "employee_id", label: "Mitarbeiter", typ: "ref", bezug: "mitarbeiter" },
    { name: "cost_type_id", label: "Kostenart", typ: "ref", bezug: "kostenarten" },
    { name: "status", label: "Status", typ: "enum", aufzaehlung: "BookingStatus" },
    { name: "date_from", label: "von", typ: "date" },
    { name: "date_to", label: "bis", typ: "date" },
  ],
  felder: [
    { name: "project_id", label: "Projekt", typ: "ref", bezug: "projekte", pflicht: true, nurAnlegen: true },
    { name: "cost_type_id", label: "Kostenart", typ: "ref", bezug: "kostenarten", pflicht: true, nurAnlegen: true },
    { name: "work_package_id", label: "Arbeitspaket", typ: "ref", bezug: "arbeitspakete" },
    {
      name: "booking_date",
      label: "Buchungsdatum",
      typ: "date",
      pflicht: true,
      vorgabe: () => new Date().toISOString().slice(0, 10),
    },
    { name: "quantity", label: "Menge", typ: "decimal", pflicht: true },
    { name: "unit_code", label: "Einheit", typ: "ref", bezug: "einheiten", hinweis: "muss zur Kostenart passen" },
    { name: "unit_price", label: "Abweichender Preis", typ: "decimal", hinweis: "leer = Preisliste gilt" },
    { name: "employee_id", label: "Mitarbeiter", typ: "ref", bezug: "mitarbeiter" },
    { name: "material_item_id", label: "Artikel", typ: "ref", bezug: "artikel" },
    { name: "description", label: "Beschreibung", typ: "textarea" },
    { name: "source", label: "Quelle", typ: "enum", aufzaehlung: "Source", nurAnlegen: true },
    { name: "source_ref", label: "Herkunftsverweis", typ: "text" },
    FELD_ATTRIBUTE,
  ],
};

/* ------------------------------------------------------- Material und Preise */

export const MATERIAL = {
  id: "material",
  label: "Material",
  pfad: "/material-items",
  einzahl: "Artikel",
  caps: { anlegen: true, aendern: true, loeschen: true },
  spalten: [
    { key: "name", label: "Bezeichnung" },
    { key: "sku", label: "Artikelnummer" },
    { key: "category", label: "Kategorie" },
    { key: "wood_species", label: "Holzart" },
    { key: "grade", label: "Güte" },
    { key: "width_mm", label: "Breite mm", art: "zahl" },
    { key: "height_mm", label: "Höhe mm", art: "zahl" },
    { key: "length_mm", label: "Länge mm", art: "zahl" },
    { key: "unit_code", label: "Einheit" },
    { key: "cost_type_code", label: "Kostenart" },
    { key: "active", label: "Aktiv" },
    SPALTE_VERSION,
  ],
  filter: [
    { name: "search", label: "Suche", typ: "text" },
    { name: "category", label: "Kategorie", typ: "enum", aufzaehlung: "MaterialCategory" },
    { name: "active_only", label: "nur aktive", typ: "bool", vorgabe: true },
  ],
  felder: [
    { name: "name", label: "Bezeichnung", typ: "text", pflicht: true },
    { name: "category", label: "Kategorie", typ: "enum", aufzaehlung: "MaterialCategory", pflicht: true },
    { name: "unit_code", label: "Einheit", typ: "ref", bezug: "einheiten", pflicht: true },
    { name: "cost_type_code", label: "Kostenart", typ: "ref", bezug: "kostenarten_code", pflicht: true },
    { name: "sku", label: "Artikelnummer", typ: "text" },
    { name: "wood_species", label: "Holzart", typ: "text" },
    { name: "grade", label: "Güte", typ: "text" },
    { name: "width_mm", label: "Breite (mm)", typ: "int" },
    { name: "height_mm", label: "Höhe (mm)", typ: "int" },
    { name: "length_mm", label: "Länge (mm)", typ: "int" },
    { name: "notes", label: "Notizen", typ: "textarea" },
    { name: "active", label: "Aktiv", typ: "bool", vorgabe: true },
    FELD_ATTRIBUTE,
  ],
};

export const PREISE = {
  id: "preise",
  label: "Preise",
  pfad: "/prices",
  einzahl: "Preis",
  hinweis:
    "Ein Preis gilt ab valid_from, offen oder bis valid_to. Überlappen sich zwei " +
    "Zeiträume für dasselbe Ziel, antwortet die API mit 409.",
  caps: { anlegen: true, aendern: true, loeschen: true },
  spalten: [
    { key: "target_type", label: "Zielart" },
    { key: "target_id", label: "Ziel", art: "kennung" },
    { key: "unit_price", label: "Preis", art: "zahl" },
    { key: "currency", label: "Währung" },
    { key: "valid_from", label: "gültig ab" },
    { key: "valid_to", label: "gültig bis" },
    { key: "source", label: "Herkunft" },
    { key: "note", label: "Notiz" },
    SPALTE_VERSION,
  ],
  filter: [
    { name: "target_type", label: "Zielart", typ: "enum", aufzaehlung: "PriceTargetType" },
    { name: "target_id", label: "Ziel (UUID)", typ: "text" },
  ],
  felder: [
    { name: "target_type", label: "Zielart", typ: "enum", aufzaehlung: "PriceTargetType", pflicht: true, nurAnlegen: true },
    // Das Auswahlfeld hängt an der Zielart; die Seite tauscht es beim Wechsel aus.
    { name: "target_id", label: "Ziel", typ: "ref", bezug: "kostenarten", pflicht: true, nurAnlegen: true },
    { name: "unit_price", label: "Preis je Einheit", typ: "decimal", pflicht: true },
    { name: "currency", label: "Währung", typ: "text", hinweis: "drei Buchstaben, Vorgabe EUR" },
    { name: "valid_from", label: "gültig ab", typ: "date", pflicht: true },
    { name: "valid_to", label: "gültig bis", typ: "date", hinweis: "leer = offen" },
    { name: "source", label: "Herkunft", typ: "enum", aufzaehlung: "PriceSource" },
    { name: "note", label: "Notiz", typ: "text" },
  ],
};

/* -------------------------------------------------------------- KI-Verbrauch */

export const MODELLPREISE = {
  id: "modellpreise",
  label: "Modellpreise",
  pfad: "/model-prices",
  einzahl: "Modellpreis",
  hinweis: "Die API kennt kein Ändern: ein neuer Preis gilt ab seinem valid_from.",
  caps: { anlegen: true, aendern: false, loeschen: true },
  spalten: [
    { key: "provider", label: "Anbieter" },
    { key: "model", label: "Modell" },
    { key: "input_per_mtok", label: "Eingabe / Mio.", art: "zahl" },
    { key: "output_per_mtok", label: "Ausgabe / Mio.", art: "zahl" },
    { key: "currency", label: "Währung" },
    { key: "valid_from", label: "gültig ab" },
    { key: "note", label: "Notiz" },
    SPALTE_VERSION,
  ],
  filter: [
    { name: "provider", label: "Anbieter", typ: "text" },
    { name: "model", label: "Modell", typ: "text" },
  ],
  felder: [
    { name: "provider", label: "Anbieter", typ: "text", pflicht: true },
    { name: "model", label: "Modell", typ: "text", pflicht: true },
    { name: "input_per_mtok", label: "Eingabe je Mio. Token", typ: "decimal", pflicht: true },
    { name: "output_per_mtok", label: "Ausgabe je Mio. Token", typ: "decimal", pflicht: true },
    { name: "currency", label: "Währung", typ: "text" },
    { name: "valid_from", label: "gültig ab", typ: "date", pflicht: true },
    { name: "note", label: "Notiz", typ: "text" },
  ],
};

export const VERBRAUCH = {
  id: "verbrauch",
  label: "KI-Aufrufe",
  pfad: "/usage",
  einzahl: "KI-Aufruf",
  hinweis:
    "Protokollierte Aufrufe sind fortschreibend: die API kennt weder Ändern noch " +
    "Löschen. Die Kosten rechnet der Service aus den Modellpreisen.",
  caps: { anlegen: true, aendern: false, loeschen: false },
  spalten: [
    { key: "occurred_at", label: "Zeitpunkt" },
    { key: "provider", label: "Anbieter" },
    { key: "model", label: "Modell" },
    { key: "module", label: "Modul" },
    { key: "feature", label: "Funktion" },
    { key: "input_tokens", label: "Eingabe", art: "zahl" },
    { key: "output_tokens", label: "Ausgabe", art: "zahl" },
    { key: "cost", label: "Kosten", art: "zahl" },
    { key: "currency", label: "Währung" },
    { key: "project_id", label: "Projekt", art: "bezug", bezug: "projekte" },
    { key: "success", label: "Erfolg" },
  ],
  filter: [
    { name: "module", label: "Modul", typ: "enum", aufzaehlung: "UsageModule" },
    { name: "model", label: "Modell", typ: "text" },
    { name: "project_id", label: "Projekt", typ: "ref", bezug: "projekte" },
  ],
  felder: [
    { name: "provider", label: "Anbieter", typ: "text", pflicht: true },
    { name: "model", label: "Modell", typ: "text", pflicht: true },
    { name: "module", label: "Modul", typ: "enum", aufzaehlung: "UsageModule", pflicht: true },
    { name: "feature", label: "Funktion", typ: "text", pflicht: true },
    { name: "input_tokens", label: "Eingabe-Token", typ: "int" },
    { name: "output_tokens", label: "Ausgabe-Token", typ: "int" },
    { name: "project_id", label: "Projekt", typ: "ref", bezug: "projekte" },
    { name: "actor_id", label: "Akteur (UUID)", typ: "text" },
    { name: "request_id", label: "Anfrage-Kennung", typ: "text" },
    { name: "success", label: "Erfolgreich", typ: "bool", vorgabe: true },
    {
      name: "occurred_at",
      label: "Zeitpunkt",
      typ: "text",
      hinweis: "ISO-8601 mit Zeitzone, z. B. 2026-11-11T09:30:00Z; leer = jetzt",
    },
  ],
};

/* ------------------------------------------------------- Änderungsprotokoll */

export const PROTOKOLL = {
  id: "protokoll",
  label: "Änderungsprotokoll",
  pfad: "/audit-events",
  einzahl: "Protokolleintrag",
  hinweis:
    "Nur lesend – das ist der Zweck. Jede schreibende Operation der Service-Schicht " +
    "erzeugt hier einen Eintrag.",
  caps: { anlegen: false, aendern: false, loeschen: false },
  spalten: [
    { key: "occurred_at", label: "Zeitpunkt" },
    { key: "action", label: "Vorgang" },
    { key: "entity_type", label: "Entität" },
    { key: "entity_id", label: "Kennung", art: "kennung" },
    { key: "actor_type", label: "Akteur-Art" },
    { key: "actor_id", label: "Akteur", art: "kennung" },
    { key: "source", label: "Quelle" },
    { key: "correlation_id", label: "Korrelation", art: "kennung" },
    { key: "changes", label: "Änderungen", art: "json" },
  ],
  filter: [
    { name: "entity_type", label: "Entität", typ: "text", platzhalter: "booking, customer …" },
    { name: "entity_id", label: "Kennung (UUID)", typ: "text" },
    { name: "action", label: "Vorgang", typ: "text", platzhalter: "create, update, confirm …" },
    { name: "actor_id", label: "Akteur (UUID)", typ: "text" },
    { name: "correlation_id", label: "Korrelations-ID", typ: "text" },
    { name: "date_from", label: "von", typ: "date" },
    { name: "date_to", label: "bis", typ: "date" },
  ],
  felder: [],
};

/** Alle Ressourcen, die über ihre Kennung erreichbar sein müssen. */
export const RESSOURCEN = {
  kunden: KUNDEN,
  einheiten: EINHEITEN,
  mitarbeiter: MITARBEITER,
  kostenarten: KOSTENARTEN,
  projekte: PROJEKTE,
  arbeitspakete: ARBEITSPAKETE,
  buchungen: BUCHUNGEN,
  material: MATERIAL,
  preise: PREISE,
  modellpreise: MODELLPREISE,
  verbrauch: VERBRAUCH,
  protokoll: PROTOKOLL,
};
