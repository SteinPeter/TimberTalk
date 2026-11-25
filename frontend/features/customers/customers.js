// Der Reiter "Kunden" (Feature F2): Kundenliste mit Suche, Kundendaten, CSV-Export und die
// Formulare und Dialoge zum Anlegen, Bearbeiten, Archivieren, Wiederherstellen und Löschen.
//
// Schreiben ist ausgeschaltet (WRITE_ENABLED = false). Abfragen laufen laut CLAUDE.md über
// getJson() aus shared/api.js, und das kann bisher nur GET: Methode und Inhalt würden still
// ignoriert. Formulare und Dialoge lassen sich öffnen und prüfen, gespeichert wird nichts
// (Steckbrief docs/features/F02-customers.md, D6). Alle Schreibaktionen laufen über sendChange();
// nach der Freigabe von shared/api.js wird nur WRITE_ENABLED umgestellt.
// Eigene CSS-Klassen kommen erst mit der Freigabe für style.css; bis dahin nur vorhandene Klassen
// (hint, empty, status) und Standard-Elemente des Browsers (<dialog>, <fieldset>).

import { API_BASE } from "../../config.js";
import { getJson } from "../../shared/api.js";

export const id = "customers";
export const title = "Kunden";

// Schreiben über die API. Erst auf true stellen, wenn getJson(path, options) Methode und Inhalt
// mitschickt – ein Test in test_customers.py prüft das.
const WRITE_ENABLED = false;

// Hinweis, solange WRITE_ENABLED aus ist – auf der Seite und in jedem Formular und Dialog.
const WRITE_DISABLED_NOTICE =
  "Speichern ist noch nicht freigeschaltet. Sie können alles öffnen und ausfüllen, " +
  "es wird aber nichts geändert.";

// Die Felder eines Kunden. `types`: bei welcher Kundenart das Feld vorkommt (fehlt es, bei beiden).
// `required`: bei welcher Kundenart es Pflicht ist. `max`: Höchstlänge wie im Backend (models.py).
const FIELDS = [
  { key: "company_name", label: "Firma", types: ["business"], required: ["business"], max: 200 },
  { key: "first_name", label: "Vorname", types: ["private"], max: 200 },
  { key: "last_name", label: "Nachname", types: ["private"], required: ["private"], max: 200 },
  { key: "street", label: "Straße", max: 200 },
  { key: "zip", label: "PLZ", max: 20 },
  { key: "city", label: "Ort", max: 200 },
  { key: "phone", label: "Telefon", max: 50 },
  { key: "email", label: "E-Mail", max: 200 },
  { key: "note", label: "Notiz", max: 2000, multiline: true },
];

const TYPE_LABELS = { private: "Privatkunde", business: "Firma" };

// Die Schreibaktionen: Methode und Adresse je Aktion.
const ACTIONS = {
  create: { method: "POST", path: () => "/api/customers" },
  update: { method: "PATCH", path: (customerId) => `/api/customers/${customerId}` },
  archive: { method: "POST", path: (customerId) => `/api/customers/${customerId}/archive` },
  restore: { method: "POST", path: (customerId) => `/api/customers/${customerId}/restore` },
  delete: { method: "DELETE", path: (customerId) => `/api/customers/${customerId}` },
};

// Wartezeit nach dem letzten Tastendruck, bevor gesucht wird (in Millisekunden).
const SEARCH_DELAY = 250;

// --- Prüfen (auch für Browser-Prüfungen exportiert) -------------------------------------------

// Gehört das Feld zur Kundenart?
function belongsTo(field, type) {
  return !field.types || field.types.includes(type);
}

// Prüft die Eingaben eines Formulars. Gibt {Feldname: Meldung} zurück; leer heißt: alles gut.
// Dieselben Regeln wie im Backend: Pflicht ist Nachname (privat) bzw. Firmenname (Firma).
export function validateCustomer(type, values) {
  const errors = {};
  if (!TYPE_LABELS[type]) {
    errors.customer_type = "Bitte wählen Sie Privatkunde oder Firma.";
    return errors;
  }
  for (const field of FIELDS) {
    if (!belongsTo(field, type)) {
      continue;
    }
    const value = (values[field.key] ?? "").trim();
    if (field.required?.includes(type) && !value) {
      const what = field.key === "company_name" ? "den Firmennamen" : "den Nachnamen";
      errors[field.key] = `Bitte geben Sie ${what} an.`;
    } else if (value.length > field.max) {
      errors[field.key] = `Höchstens ${field.max} Zeichen (jetzt ${value.length}).`;
    }
  }
  return errors;
}

// Prüft, ob die Antwort der API wirklich zur Aktion passt. Nur dann gilt sie als gespeichert.
// Schützt davor, dass eine Abfrage still als GET läuft und trotzdem „Gespeichert“ erscheint.
export function confirmsChange(action, sent, result) {
  if (action === "delete") {
    return result === null; // 204 ohne Inhalt
  }
  if (!result || typeof result !== "object" || Array.isArray(result) || !result.id) {
    return false;
  }
  if (action === "archive") {
    return result.archived === true;
  }
  if (action === "restore") {
    return result.archived === false;
  }
  // Anlegen und Bearbeiten: Jeder gesendete Wert muss so zurückkommen.
  return Object.entries(sent).every(([key, value]) => result[key] === value);
}

// Deutsche Meldung zu einem Fehler aus getJson(). Nutzt error.status, sonst „Antwort 409“.
export function errorMessage(error) {
  if (error?.writeDisabled) {
    return `Nicht gespeichert. ${WRITE_DISABLED_NOTICE}`;
  }
  if (error?.unconfirmed) {
    return "Nicht gespeichert: Die Antwort des Servers bestätigt die Änderung nicht.";
  }
  const status = error?.status ?? Number(/Antwort (\d+)/.exec(error?.message ?? "")?.[1]);
  const texts = {
    404: "Diesen Kunden gibt es nicht mehr. Bitte schließen Sie den Dialog und suchen Sie neu.",
    409: "Nur archivierte Kunden lassen sich endgültig löschen. Bitte erst archivieren.",
    422: "Die Angaben wurden abgelehnt. Bitte prüfen Sie die Pflichtfelder.",
  };
  const base = texts[status] ?? "Die Änderung konnte nicht gespeichert werden.";
  // Kommt eine deutsche Meldung vom Server mit (nach Erweiterung von getJson), steht sie dahinter.
  const detail = error?.message && !/^Antwort \d+$/.test(error.message) ? ` (${error.message})` : "";
  return base + detail;
}

// --- Schreiben: der einzige Weg zur API für Änderungen ----------------------------------------

// Schickt eine Änderung an die API und gibt die bestätigte Antwort zurück. Wirft einen Fehler,
// wenn Schreiben ausgeschaltet ist oder die Antwort die Änderung nicht bestätigt.
async function sendChange(action, customerId, body) {
  if (!WRITE_ENABLED) {
    throw Object.assign(new Error("Schreiben ausgeschaltet"), { writeDisabled: true });
  }
  const { method, path } = ACTIONS[action];
  const options = { method };
  if (body) {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(body);
  }
  const result = await getJson(path(customerId), options);
  if (!confirmsChange(action, body ?? {}, result)) {
    throw Object.assign(new Error("Nicht bestätigt"), { unconfirmed: true });
  }
  return result;
}

// --- Reiter aufbauen --------------------------------------------------------------------------

// Baut den Reiter auf: Kopf mit Suche, Export und „Neuer Kunde“, darunter die Liste.
export async function render(panel) {
  // Nur fester Text aus dieser Datei – Daten aus der API kommen später mit textContent.
  panel.innerHTML = `
    <h1>Kunden</h1>
    <p class="hint">Kunden suchen, ansehen und pflegen.</p>

    <p>
      <label>Suchen
        <input type="search" name="q" autocomplete="off" size="34"
          placeholder="Name, Ort, PLZ, Telefon oder E-Mail">
      </label>
      <label><input type="checkbox" name="archived"> Archivierte zeigen</label>
    </p>
    <p>
      <button type="button" data-role="new">Neuer Kunde</button>
      <a data-role="export" download="kunden.csv">Als CSV exportieren</a>
    </p>
    <p class="hint" data-role="write-notice"></p>

    <p data-role="feedback" role="status" aria-live="polite"></p>
    <p data-role="count" aria-live="polite"></p>
    <div data-role="list"></div>
  `;

  const search = panel.querySelector('input[name="q"]');
  const archived = panel.querySelector('input[name="archived"]');
  const exportLink = panel.querySelector('[data-role="export"]');
  const feedback = panel.querySelector('[data-role="feedback"]');
  const count = panel.querySelector('[data-role="count"]');
  const list = panel.querySelector('[data-role="list"]');
  panel.querySelector('[data-role="write-notice"]').textContent = WRITE_ENABLED
    ? ""
    : WRITE_DISABLED_NOTICE;

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
        showList(list, count, customers, search.value.trim() !== "", openAction);
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

  // Öffnet Formular oder Dialog. Nach einer bestätigten Änderung: Meldung und Liste neu laden.
  function openAction(action, customer) {
    feedback.textContent = "";
    const done = (text) => {
      feedback.textContent = text;
      load();
    };
    if (action === "create" || action === "update") {
      openCustomerForm(panel, customer, done);
    } else {
      openConfirmDialog(panel, action, customer, done);
    }
  }

  panel.querySelector('[data-role="new"]').addEventListener("click", () => openAction("create"));

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

// --- Liste ------------------------------------------------------------------------------------

// Zeigt die Kunden als Liste. Ein Klick auf den Namen klappt die Kundendaten auf.
function showList(list, count, customers, searching, openAction) {
  if (customers.length === 0) {
    count.textContent = "";
    list.replaceChildren(
      message(searching ? "Kein Kunde passt zu dieser Suche." : "Noch keine Kunden vorhanden."),
    );
    return;
  }
  count.textContent = customers.length === 1 ? "1 Kunde" : `${customers.length} Kunden`;
  list.replaceChildren(...customers.map((customer) => customerEntry(customer, openAction)));
}

// Ein Kunde: Zeile mit Name und Ort, aufgeklappt seine Daten und die Aktionen.
function customerEntry(customer, openAction) {
  const entry = document.createElement("details");
  const summary = document.createElement("summary");
  const parts = [customer.name, customer.city].filter(Boolean);
  summary.textContent = parts.join(" · ") + (customer.archived ? " (archiviert)" : "");
  entry.append(summary, customerDetails(customer), customerActions(customer, openAction));
  return entry;
}

// Die Kundendaten als Begriffsliste – nur Felder, die zur Kundenart gehören und gefüllt sind.
function customerDetails(customer) {
  const details = document.createElement("dl");
  details.className = "status";
  addRow(details, "Kundennummer", String(customer.id));
  addRow(details, "Art", TYPE_LABELS[customer.customer_type] ?? customer.customer_type);
  for (const field of FIELDS) {
    if (belongsTo(field, customer.customer_type) && customer[field.key]) {
      addRow(details, field.label, customer[field.key]);
    }
  }
  addRow(details, "Status", customer.archived ? "archiviert" : "aktiv");
  addRow(details, "Zuletzt geändert", formatDate(customer.updated_at));
  return details;
}

// Die Aktionen zu einem Kunden. Löschen gibt es nach der vorläufigen Regel nur für archivierte.
function customerActions(customer, openAction) {
  const actions = document.createElement("p");
  const choices = customer.archived
    ? [
        ["update", "Bearbeiten …"],
        ["restore", "Wiederherstellen …"],
        ["delete", "Endgültig löschen …"],
      ]
    : [
        ["update", "Bearbeiten …"],
        ["archive", "Archivieren …"],
      ];
  for (const [action, label] of choices) {
    actions.append(button(label, () => openAction(action, customer)), " ");
  }
  return actions;
}

// --- Formular: Anlegen und Bearbeiten ---------------------------------------------------------

// Öffnet das Formular als Dialog. customer fehlt beim Anlegen.
function openCustomerForm(panel, customer, done) {
  const editing = Boolean(customer);
  const dialog = document.createElement("dialog");
  dialog.setAttribute("aria-labelledby", "customers-form-title");
  const form = document.createElement("form");
  form.noValidate = true; // eigene, deutsche Meldungen statt der Browser-Meldungen

  const heading = document.createElement("h2");
  heading.id = "customers-form-title";
  heading.textContent = editing ? `${customer.name} bearbeiten` : "Neuer Kunde";
  form.append(heading);
  if (!WRITE_ENABLED) {
    form.append(paragraph(WRITE_DISABLED_NOTICE, "hint"));
  }

  // Kundenart als Auswahl statt Texteingabe.
  const typeBox = document.createElement("fieldset");
  const legend = document.createElement("legend");
  legend.textContent = "Kundenart";
  typeBox.append(legend);
  let type = customer?.customer_type ?? "private";
  for (const [value, label] of Object.entries(TYPE_LABELS)) {
    const option = document.createElement("label");
    const radio = document.createElement("input");
    radio.type = "radio";
    radio.name = "customer_type";
    radio.value = value;
    radio.checked = value === type;
    radio.addEventListener("change", () => {
      type = value;
      update();
    });
    option.append(radio, ` ${label} `);
    typeBox.append(option);
  }
  form.append(typeBox);

  // Ein Eingabefeld je Feld, mit Beschriftung und Platz für die Meldung darunter.
  // Meldungen erscheinen erst, wenn jemand in das Feld getippt oder „Speichern“ versucht hat –
  // nicht schon beim Öffnen (entering-data.md). Der Knopf ist trotzdem von Anfang an gesperrt.
  const touched = new Set();
  let attempted = false;
  const inputs = {};
  const rows = {};
  const notes = {};
  for (const field of FIELDS) {
    const row = document.createElement("p");
    const label = document.createElement("label");
    const input = document.createElement(field.multiline ? "textarea" : "input");
    input.id = `customers-field-${field.key}`;
    input.name = field.key;
    input.maxLength = field.max;
    if (!field.multiline) {
      input.type = field.key === "email" ? "email" : field.key === "phone" ? "tel" : "text";
      input.size = 34;
    } else {
      input.rows = 3;
      input.cols = 34;
    }
    input.value = customer?.[field.key] ?? "";
    label.htmlFor = input.id;
    const note = document.createElement("span");
    note.id = `${input.id}-note`;
    note.setAttribute("aria-live", "polite");
    input.setAttribute("aria-describedby", note.id);
    input.addEventListener("input", () => {
      touched.add(field.key);
      update();
    });
    // Meldung in eigener Zeile unter dem Feld, damit sie auch schmal nicht mitten im Satz umbricht.
    row.append(label, document.createElement("br"), input, document.createElement("br"), note);
    form.append(row);
    inputs[field.key] = input;
    rows[field.key] = row;
    notes[field.key] = { label, note, field };
  }

  const error = paragraph("", "");
  error.setAttribute("role", "alert");
  const save = button(editing ? "Änderungen speichern" : "Kunde anlegen");
  save.type = "submit";
  const cancel = button("Abbrechen", () => dialog.close());
  form.append(error, buttonRow(cancel, save));
  dialog.append(form);

  // Felder zur Kundenart zeigen, Pflichtfelder markieren, Eingaben sofort prüfen. Solange etwas
  // fehlt, ist der Knopf zum Speichern gesperrt (entering-data.md).
  function update() {
    const errors = validateCustomer(type, currentValues());
    for (const { label, note, field } of Object.values(notes)) {
      const visible = belongsTo(field, type);
      rows[field.key].hidden = !visible;
      label.textContent = field.label + (field.required?.includes(type) ? " (Pflicht)" : "");
      const shown = visible && (attempted || touched.has(field.key));
      const text = shown ? (errors[field.key] ?? "") : "";
      note.textContent = text;
      inputs[field.key].setAttribute("aria-invalid", String(Boolean(text)));
    }
    save.disabled = Object.keys(errors).length > 0;
  }

  // Die Werte der sichtbaren Felder, ohne Leerzeichen am Rand.
  function currentValues() {
    const values = {};
    for (const field of FIELDS) {
      if (belongsTo(field, type)) {
        values[field.key] = inputs[field.key].value.trim();
      }
    }
    return values;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (Object.keys(validateCustomer(type, currentValues())).length > 0) {
      attempted = true;
      update();
      return;
    }
    const body = { customer_type: type, ...currentValues() };
    await submit(dialog, [save, cancel], error, async () => {
      const result = await sendChange(editing ? "update" : "create", customer?.id, body);
      done(`„${result.name}“ wurde gespeichert.`);
    });
  });

  showDialog(panel, dialog);
  update();
  inputs[type === "business" ? "company_name" : "first_name"].focus();
}

// --- Dialoge: Archivieren, Wiederherstellen, Löschen ------------------------------------------

const CONFIRM_TEXTS = {
  archive: {
    title: (name) => `„${name}“ archivieren?`,
    text: "Der Kunde verschwindet aus der Liste. Über „Archivierte zeigen“ lässt er sich jederzeit wiederherstellen.",
    button: "Archivieren",
    done: (name) => `„${name}“ wurde archiviert.`,
  },
  restore: {
    title: (name) => `„${name}“ wiederherstellen?`,
    text: "Der Kunde erscheint wieder in der Kundenliste.",
    button: "Wiederherstellen",
    done: (name) => `„${name}“ wurde wiederhergestellt.`,
  },
  delete: {
    title: (name) => `„${name}“ endgültig löschen?`,
    text: "Alle Daten dieses Kunden werden aus der Datenbank entfernt. Das lässt sich nicht rückgängig machen.",
    button: "Endgültig löschen",
    confirm: "Ja, ich möchte diesen Kunden endgültig löschen.",
    done: (name) => `„${name}“ wurde endgültig gelöscht.`,
  },
};

// Fragt vor Archivieren, Wiederherstellen oder Löschen nach. Löschen braucht zusätzlich ein Häkchen.
function openConfirmDialog(panel, action, customer, done) {
  const texts = CONFIRM_TEXTS[action];
  const dialog = document.createElement("dialog");
  dialog.setAttribute("role", "alertdialog");
  dialog.setAttribute("aria-labelledby", "customers-confirm-title");

  const heading = document.createElement("h2");
  heading.id = "customers-confirm-title";
  heading.textContent = texts.title(customer.name);
  dialog.append(heading, paragraph(texts.text, ""));
  if (!WRITE_ENABLED) {
    dialog.append(paragraph(WRITE_DISABLED_NOTICE, "hint"));
  }

  const cancel = button("Abbrechen", () => dialog.close());
  const confirm = button(texts.button);
  if (texts.confirm) {
    // Ausdrückliche Bestätigung: Ohne Häkchen bleibt der Knopf gesperrt.
    const label = document.createElement("label");
    const check = document.createElement("input");
    check.type = "checkbox";
    check.name = "confirm";
    confirm.disabled = true;
    check.addEventListener("change", () => {
      confirm.disabled = !check.checked;
    });
    label.append(check, ` ${texts.confirm}`);
    const row = document.createElement("p");
    row.append(label);
    dialog.append(row);
  }

  const error = paragraph("", "");
  error.setAttribute("role", "alert");
  confirm.addEventListener("click", () =>
    submit(dialog, [confirm, cancel], error, async () => {
      await sendChange(action, customer.id);
      done(texts.done(customer.name));
    }),
  );
  dialog.append(error, buttonRow(cancel, confirm));

  showDialog(panel, dialog);
  cancel.focus(); // Abbrechen ist vorgewählt, nicht die Aktion (alerts.md)
}

// --- Gemeinsame Hilfen für Formular und Dialoge -----------------------------------------------

// Führt eine Schreibaktion aus: Knöpfe sperren, bei Erfolg schließen, bei Fehler Meldung zeigen.
// Eine Erfolgsmeldung kommt nur aus `work` – und die erst nach einer bestätigten Antwort.
async function submit(dialog, buttons, error, work) {
  const before = buttons.map((item) => item.disabled);
  for (const item of buttons) {
    item.disabled = true;
  }
  error.textContent = "";
  try {
    await work();
    dialog.close();
  } catch (problem) {
    error.textContent = errorMessage(problem);
    buttons.forEach((item, index) => {
      item.disabled = before[index];
    });
  }
}

// Zeigt einen Dialog vor der Seite. Esc oder „Abbrechen“ schließt ihn; danach wird er entfernt.
function showDialog(panel, dialog) {
  dialog.addEventListener("close", () => dialog.remove());
  panel.append(dialog);
  dialog.showModal();
}

function button(label, onClick) {
  const element = document.createElement("button");
  element.type = "button";
  element.textContent = label;
  if (onClick) {
    element.addEventListener("click", onClick);
  }
  return element;
}

// Abbrechen links, die Aktion rechts (alerts.md › Place buttons where people expect).
function buttonRow(cancel, action) {
  const row = document.createElement("p");
  row.append(cancel, " ", action);
  return row;
}

function paragraph(text, className) {
  const element = document.createElement("p");
  if (className) {
    element.className = className;
  }
  element.textContent = text;
  return element;
}

function addRow(list, label, value) {
  const term = document.createElement("dt");
  term.textContent = label;
  const description = document.createElement("dd");
  description.textContent = value;
  list.append(term, description);
}

function message(text) {
  return paragraph(text, "empty");
}

// Zeitpunkt aus der API (UTC ohne Zeitzone) als deutsches Datum mit Uhrzeit.
function formatDate(value) {
  const date = new Date(value.endsWith("Z") ? value : `${value}Z`);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString("de-DE", { dateStyle: "medium", timeStyle: "short" });
}
