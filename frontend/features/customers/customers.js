// Der Reiter "Kunden" (Feature F2): Kundenliste mit Suche, Kundendaten und CSV-Export.
//
// Stand: nur lesen. Anlegen, Bearbeiten, Archivieren, Wiederherstellen und Löschen brauchen
// Abfragen mit POST, PATCH und DELETE. Die laufen laut CLAUDE.md über getJson() aus
// shared/api.js, und das kann bisher nur GET. Bis die gemeinsame Datei erweitert ist, sind
// diese Knöpfe sichtbar, aber gesperrt (Steckbrief docs/features/F02-customers.md, D6).
// Eigene CSS-Klassen kommen erst mit der Freigabe für style.css; bis dahin nur vorhandene
// Klassen (hint, empty, status) und Standard-Elemente des Browsers.

import { API_BASE } from "../../config.js";
import { getJson } from "../../shared/api.js";

export const id = "customers";
export const title = "Kunden";

// Die Felder eines Kunden mit deutscher Beschriftung. `types` sagt, bei welcher Kundenart das
// Feld vorkommt (fehlt es, bei beiden). Die Anzeige nutzt diese Liste; das Formular zum Anlegen
// und Bearbeiten baut später auf derselben Liste auf.
const FIELDS = [
  { key: "company_name", label: "Firma", types: ["business"] },
  { key: "first_name", label: "Vorname", types: ["private"] },
  { key: "last_name", label: "Nachname", types: ["private"] },
  { key: "street", label: "Straße" },
  { key: "zip", label: "PLZ" },
  { key: "city", label: "Ort" },
  { key: "phone", label: "Telefon" },
  { key: "email", label: "E-Mail" },
  { key: "note", label: "Notiz" },
];

const TYPE_LABELS = { private: "Privatkunde", business: "Firma" };

// Was am gesperrten Knopf steht. Für den Zimmerer ohne Technik; der Grund (shared/api.js) steht
// oben im Kommentar und im Steckbrief.
const LOCKED_REASON = "Kommt in einem nächsten Schritt.";

// Wartezeit nach dem letzten Tastendruck, bevor gesucht wird (in Millisekunden).
const SEARCH_DELAY = 250;

// Baut den Reiter auf: Kopf mit Suche und Export, darunter die Liste.
export async function render(panel) {
  // Nur fester Text aus dieser Datei – Daten aus der API kommen später mit textContent.
  panel.innerHTML = `
    <h1>Kunden</h1>
    <p class="hint">Kunden suchen und ihre Daten ansehen.</p>

    <p>
      <label>Suchen
        <input type="search" name="q" autocomplete="off" size="34"
          placeholder="Name, Ort, PLZ, Telefon oder E-Mail">
      </label>
      <label><input type="checkbox" name="archived"> Archivierte zeigen</label>
    </p>
    <p>
      <button type="button" disabled>Neuer Kunde</button>
      <a data-role="export" download="kunden.csv">Als CSV exportieren</a>
    </p>
    <p class="hint">
      Anlegen, Bearbeiten, Archivieren und Löschen sind hier noch nicht möglich. ${LOCKED_REASON}
    </p>

    <p data-role="count" aria-live="polite"></p>
    <div data-role="list"></div>
  `;

  const search = panel.querySelector('input[name="q"]');
  const archived = panel.querySelector('input[name="archived"]');
  const exportLink = panel.querySelector('[data-role="export"]');
  const count = panel.querySelector('[data-role="count"]');
  const list = panel.querySelector('[data-role="list"]');
  panel.querySelector("button[disabled]").title = LOCKED_REASON;

  // Jede Suche bekommt eine Nummer. Kommt eine ältere Antwort zu spät, wird sie verworfen,
  // damit nicht die Treffer für einen halb getippten Suchtext stehen bleiben.
  let latest = 0;

  async function load() {
    const number = ++latest;
    const params = new URLSearchParams();
    if (search.value.trim()) {
      params.set("q", search.value.trim());
    }
    if (archived.checked) {
      params.set("include_archived", "true");
    }
    exportLink.href = exportUrl(archived.checked);
    count.textContent = "Kunden werden geladen …";

    try {
      const customers = await getJson(`/api/customers?${params}`);
      if (number === latest) {
        showList(list, count, customers, search.value.trim() !== "");
      }
    } catch (error) {
      if (number === latest) {
        count.textContent = "";
        list.replaceChildren(
          message(`Die Kunden konnten nicht geladen werden (${error.message}).`),
        );
      }
    }
  }

  // Suchen schon beim Tippen, aber erst nach einer kurzen Pause.
  let timer;
  search.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(load, SEARCH_DELAY);
  });
  archived.addEventListener("change", load);

  await load();
}

// Adresse der CSV-Datei. Der Browser lädt sie über den Link herunter – das ist keine Abfrage
// mit fetch, deshalb geht sie nicht über getJson().
function exportUrl(includeArchived) {
  const query = includeArchived ? "?include_archived=true" : "";
  return `${API_BASE}/api/customers/export.csv${query}`;
}

// Zeigt die Kunden als Liste. Ein Klick auf den Namen klappt die Kundendaten auf.
function showList(list, count, customers, searching) {
  if (customers.length === 0) {
    count.textContent = "";
    list.replaceChildren(
      message(
        searching
          ? "Kein Kunde passt zu dieser Suche."
          : "Noch keine Kunden vorhanden.",
      ),
    );
    return;
  }
  count.textContent = customers.length === 1 ? "1 Kunde" : `${customers.length} Kunden`;
  list.replaceChildren(...customers.map(customerEntry));
}

// Ein Kunde: Zeile mit Name und Ort, aufgeklappt seine Daten und die Aktionen.
function customerEntry(customer) {
  const entry = document.createElement("details");
  const summary = document.createElement("summary");
  const parts = [customer.name, customer.city].filter(Boolean);
  summary.textContent = parts.join(" · ") + (customer.archived ? " (archiviert)" : "");
  entry.append(summary, customerDetails(customer), customerActions(customer));
  return entry;
}

// Die Kundendaten als Begriffsliste – nur Felder, die zur Kundenart gehören und gefüllt sind.
function customerDetails(customer) {
  const details = document.createElement("dl");
  details.className = "status";
  addRow(details, "Kundennummer", String(customer.id));
  addRow(details, "Art", TYPE_LABELS[customer.customer_type] ?? customer.customer_type);
  for (const field of FIELDS) {
    const belongs = !field.types || field.types.includes(customer.customer_type);
    if (belongs && customer[field.key]) {
      addRow(details, field.label, customer[field.key]);
    }
  }
  addRow(details, "Status", customer.archived ? "archiviert" : "aktiv");
  addRow(details, "Zuletzt geändert", formatDate(customer.updated_at));
  return details;
}

// Die Aktionen zu einem Kunden – vorerst gesperrt (siehe Kopf der Datei).
// Löschen gibt es nach der vorläufigen Regel nur für archivierte Kunden.
function customerActions(customer) {
  const actions = document.createElement("p");
  const labels = customer.archived
    ? ["Bearbeiten", "Wiederherstellen", "Endgültig löschen …"]
    : ["Bearbeiten", "Archivieren"];
  for (const label of labels) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.disabled = true;
    button.title = LOCKED_REASON;
    actions.append(button, " ");
  }
  return actions;
}

function addRow(list, label, value) {
  const term = document.createElement("dt");
  term.textContent = label;
  const description = document.createElement("dd");
  description.textContent = value;
  list.append(term, description);
}

function message(text) {
  const paragraph = document.createElement("p");
  paragraph.className = "empty";
  paragraph.textContent = text;
  return paragraph;
}

// Zeitpunkt aus der API (UTC ohne Zeitzone) als deutsches Datum mit Uhrzeit.
function formatDate(value) {
  const date = new Date(value.endsWith("Z") ? value : `${value}Z`);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString("de-DE", { dateStyle: "medium", timeStyle: "short" });
}
