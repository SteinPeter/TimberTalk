// Der Reiter „Projekte“ (Feature F3): Projekte zu einem Kunden anlegen, suchen, ändern,
// Status setzen, archivieren und je Kunde anzeigen.
// Alle Daten aus der API kommen ausschließlich über textContent in die Seite, nie über innerHTML.

import { API_BASE } from "../../config.js";
import { getJson } from "../../shared/api.js";

export const id = "projects";
export const title = "Projekte";

const STATUS_OPTIONS = [
  { value: "angefragt", label: "Angefragt" },
  { value: "geplant", label: "Geplant" },
  { value: "in_arbeit", label: "In Arbeit" },
  { value: "abgeschlossen", label: "Abgeschlossen" },
  { value: "abgerechnet", label: "Abgerechnet" },
];

const STATUS_LABEL = Object.fromEntries(STATUS_OPTIONS.map((item) => [item.value, item.label]));

// Dieselbe Obergrenze wie MAX_DURATION_DAYS in service.py.
const MAX_DURATION_DAYS = 3650;

// --- Kleine DOM- und API-Helfer ------------------------------------------------

function ensureStylesheet() {
  if (document.getElementById("projects-stylesheet")) {
    return;
  }
  const link = document.createElement("link");
  link.id = "projects-stylesheet";
  link.rel = "stylesheet";
  link.href = "./features/projects/projects.css";
  document.head.append(link);
}

function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "class") {
      node.className = value;
    } else if (key.startsWith("on")) {
      node.addEventListener(key.slice(2), value);
    } else if (["value", "disabled", "checked", "hidden", "textContent"].includes(key)) {
      node[key] = value;
    } else if (value !== undefined && value !== null) {
      node.setAttribute(key, String(value));
    }
  }
  node.append(...children);
  return node;
}

function field(labelText, input, hint) {
  const label = el("label", { class: "projects-field" }, el("span", {}, labelText), input);
  if (hint) {
    label.append(el("small", { class: "projects-hint" }, hint));
  }
  return label;
}

async function sendJson(method, path, body) {
  const options = { method };
  if (body !== undefined) {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(body);
  }
  const response = await fetch(`${API_BASE}${path}`, options);
  if (!response.ok) {
    let message = `Antwort ${response.status}`;
    try {
      const data = await response.json();
      if (typeof data.detail === "string") {
        message = data.detail;
      } else if (Array.isArray(data.detail)) {
        message = "Bitte die Eingaben prüfen.";
      }
    } catch {
      // Keine lesbare Fehlermeldung: es bleibt beim Statuscode.
    }
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}

function formatDate(iso) {
  return iso ? iso.split("-").reverse().join(".") : "";
}

function formatRange(project) {
  if (project.start_date && project.end_date) {
    return `${formatDate(project.start_date)} – ${formatDate(project.end_date)}`;
  }
  if (project.start_date) {
    return `ab ${formatDate(project.start_date)}`;
  }
  if (project.end_date) {
    return `bis ${formatDate(project.end_date)}`;
  }
  if (project.duration_days) {
    return `${project.duration_days} ${project.duration_days === 1 ? "Tag" : "Tage"}`;
  }
  return "–";
}

const DAY_IN_MS = 24 * 60 * 60 * 1000;

// Ende = Beginn + Dauer - 1 Tag, wie in service.py. Gerechnet wird in UTC, damit die
// Zeitumstellung keinen Tag verschiebt.
function addDays(iso, days) {
  const date = new Date(Date.parse(`${iso}T00:00:00Z`) + days * DAY_IN_MS);
  return Number.isNaN(date.getTime()) ? "" : date.toISOString().slice(0, 10);
}

function daysBetween(startIso, endIso) {
  return (Date.parse(`${endIso}T00:00:00Z`) - Date.parse(`${startIso}T00:00:00Z`)) / DAY_IN_MS;
}

// fetch() meldet einen nicht erreichbaren Server als TypeError mit englischem Text.
function errorText(error) {
  return error instanceof TypeError ? "Der Server ist nicht erreichbar." : error.message;
}

function makeMessageBox() {
  const box = el("p", { class: "projects-message", role: "status", hidden: true });
  box.show = (text, isError = false) => {
    box.textContent = isError ? `Das hat nicht geklappt: ${text}` : text;
    box.dataset.kind = isError ? "error" : "ok";
    box.hidden = false;
  };
  box.clear = () => {
    box.hidden = true;
  };
  return box;
}

function makeFact(label, value) {
  return el("div", { class: "projects-fact" }, el("dt", {}, label), el("dd", {}, value));
}

// --- Reiter aufbauen -----------------------------------------------------------

export function render(panel) {
  ensureStylesheet();

  let customerSource = "fallback";
  let customers = [];
  let projects = [];
  let customerGroups = [];
  let editingProject = null; // das Projekt im Formular, null beim Anlegen
  let nameTyped = false; // hat der Mensch den Kundennamen selbst eingetippt?
  let saving = false;
  let viewMode = "list"; // "list" oder "customers"
  let searchTimer = null;
  // Zähler der Anfragen: Eine verspätete Antwort darf eine neuere nicht überschreiben.
  let listRequest = 0;
  let overviewRequest = 0;

  const message = makeMessageBox();
  const formMessage = makeMessageBox();

  // --- Kopfleiste ---
  const newButton = el("button", { type: "button", class: "projects-button" }, "Neues Projekt");
  const header = el("div", { class: "projects-header" }, el("h1", {}, "Projekte"), newButton);

  // --- Formular zum Anlegen und Bearbeiten ---
  const formTitle = el("h2", {}, "Neues Projekt anlegen");
  const customerSelect = el("select", {
    id: "projects-customer-select",
    name: "customer_id",
    required: "",
  });
  const customerDatalist = el("datalist", { id: "projects-known-customers" });
  const customerIdInput = el("input", {
    id: "projects-customer-id",
    name: "customer_id_fallback",
    type: "number",
    min: "1",
    step: "1",
    inputmode: "numeric",
    list: "projects-known-customers",
    placeholder: "z. B. 4",
  });
  const customerNameInput = el("input", {
    id: "projects-customer-name",
    name: "customer_name",
    type: "text",
    placeholder: "z. B. Familie Berger",
    autocomplete: "off",
  });
  const customerSelectWrap = field("Kunde (Pflichtfeld)", customerSelect);
  const customerFallbackWrap = el(
    "div",
    { class: "projects-grid" },
    field(
      "Kundennummer (Pflichtfeld)",
      customerIdInput,
      "Ohne Kunde lässt sich kein Projekt speichern. Sobald Kunden angelegt sind, erscheinen sie als Auswahl.",
    ),
    field(
      "Kundenname (optional)",
      customerNameInput,
      "Wird aus den Kundendaten übernommen, sobald vorhanden.",
    ),
  );

  const nameInput = el("input", {
    id: "projects-name",
    name: "name",
    type: "text",
    required: "",
    placeholder: "z. B. Carport oder Dachstuhl",
  });
  const siteInput = el("input", {
    id: "projects-site",
    name: "baustelle",
    type: "text",
    placeholder: "z. B. Hauptstr. 12, Potsdam",
  });
  const statusSelect = el(
    "select",
    { id: "projects-status", name: "status" },
    ...STATUS_OPTIONS.map((opt) => el("option", { value: opt.value }, opt.label)),
  );
  const startInput = el("input", { id: "projects-start", name: "start_date", type: "date" });
  const durationInput = el("input", {
    id: "projects-duration",
    name: "duration_days",
    type: "number",
    min: "1",
    max: String(MAX_DURATION_DAYS),
    step: "1",
    inputmode: "numeric",
    placeholder: "z. B. 4",
  });
  const endInput = el("input", { id: "projects-end", name: "end_date", type: "date" });
  const notesInput = el("textarea", {
    id: "projects-notes",
    name: "notes",
    placeholder: "Kurze Hinweise zur Baustelle oder zum Ablauf",
  });

  const saveButton = el(
    "button",
    { type: "submit", class: "projects-button", disabled: true },
    "Projekt anlegen",
  );
  const cancelButton = el(
    "button",
    { type: "button", class: "projects-button-quiet" },
    "Abbrechen",
  );

  const form = el(
    "form",
    { class: "projects-form", hidden: true, novalidate: "" },
    formTitle,
    customerDatalist,
    customerSelectWrap,
    customerFallbackWrap,
    el(
      "div",
      { class: "projects-grid projects-grid-spaced" },
      field("Projektname (Pflichtfeld)", nameInput),
      field("Baustelle / Ort", siteInput),
      field("Status", statusSelect),
    ),
    el(
      "div",
      { class: "projects-grid projects-grid-spaced" },
      field("Geplanter Start", startInput),
      field("Dauer in Tagen", durationInput, "Beginn, Dauer und Ende passen sich an."),
      field("Geplantes Ende", endInput),
    ),
    el("div", { class: "projects-grid-spaced" }, field("Notiz", notesInput)),
    el("div", { class: "projects-actions" }, saveButton, cancelButton),
    formMessage,
  );

  // --- Suche und Filter ---
  const searchInput = el("input", {
    id: "projects-search",
    name: "search",
    type: "search",
    placeholder: "Nach Projekt, Kunde oder Baustelle suchen",
    autocomplete: "off",
  });
  const statusFilter = el(
    "select",
    { id: "projects-filter-status", name: "filter_status" },
    el("option", { value: "" }, "Alle Status"),
    ...STATUS_OPTIONS.map((opt) => el("option", { value: opt.value }, opt.label)),
  );
  const customerFilter = el(
    "select",
    { id: "projects-filter-customer", name: "filter_customer" },
    el("option", { value: "" }, "Alle Kunden"),
  );

  const toolbar = el(
    "div",
    { class: "projects-toolbar" },
    field("Suchen", searchInput),
    field("Status", statusFilter),
    field("Kunde", customerFilter),
  );

  // --- Ansicht umschalten & Archiv-Filter ---
  // Eine Tab-Ansicht, kein Segment-Schalter (apple-design: segmented-controls.md).
  const makeViewTab = (name, label) =>
    el(
      "button",
      {
        type: "button",
        role: "tab",
        id: `projects-tab-${name}`,
        class: "projects-tab",
        "aria-controls": `projects-panel-${name}`,
      },
      label,
    );
  const listViewBtn = makeViewTab("list", "Alle Projekte");
  const customerViewBtn = makeViewTab("customers", "Nach Kunde");
  const archivedToggle = el("input", {
    id: "projects-filter-archived",
    name: "include_archived",
    type: "checkbox",
  });
  const viewBar = el(
    "div",
    { class: "projects-view-bar" },
    el(
      "div",
      { class: "projects-tabs", role: "tablist", "aria-label": "Ansicht" },
      listViewBtn,
      customerViewBtn,
    ),
    el("label", { class: "projects-checkbox" }, archivedToggle, "Archivierte anzeigen"),
  );

  // --- Ausgabebereiche ---
  const makeViewPanel = (name) =>
    el("div", {
      id: `projects-panel-${name}`,
      role: "tabpanel",
      "aria-labelledby": `projects-tab-${name}`,
    });
  const listArea = makeViewPanel("list");
  const customerArea = makeViewPanel("customers");

  const root = el(
    "div",
    { class: "projects-root" },
    header,
    message,
    form,
    toolbar,
    viewBar,
    listArea,
    customerArea,
  );
  panel.replaceChildren(root);

  // --- Hilfsfunktionen für Formular und Anzeige ---

  function selectedCustomerId() {
    const raw = customerSource === "customers" ? customerSelect.value : customerIdInput.value;
    const parsed = Number.parseInt(raw, 10);
    return Number.isInteger(parsed) && parsed >= 1 ? parsed : null;
  }

  function updateSaveButton() {
    const hasCustomer = selectedCustomerId() !== null;
    const hasName = nameInput.value.trim().length > 0;
    saveButton.disabled = saving || !(hasCustomer && hasName);
  }

  function durationValue() {
    const days = Number(durationInput.value);
    return Number.isInteger(days) && days >= 1 && days <= MAX_DURATION_DAYS ? days : null;
  }

  // Neuer Beginn oder neue Dauer: das Ende rückt nach.
  function syncEndDate() {
    const days = durationValue();
    if (startInput.value && days !== null) {
      endInput.value = addDays(startInput.value, days - 1);
    }
  }

  // Neues Ende: die Dauer rückt nach.
  function syncDuration() {
    if (!startInput.value || !endInput.value || !durationInput.value) {
      return;
    }
    const days = daysBetween(startInput.value, endInput.value) + 1;
    if (days >= 1 && days <= MAX_DURATION_DAYS) {
      durationInput.value = String(days);
    }
  }

  // Eine Meldung zu unfertigen Eingaben, sonst null. Ohne diese Prüfung kämen sie als leer
  // an, und ein gespeicherter Wert würde stillschweigend gelöscht.
  function inputProblem() {
    if (startInput.validity.badInput || endInput.validity.badInput) {
      return "Bitte das Datum vollständig eingeben.";
    }
    if (durationInput.validity.badInput || (durationInput.value && durationValue() === null)) {
      return `Die Dauer muss eine ganze Zahl zwischen 1 und ${MAX_DURATION_DAYS} Tagen sein.`;
    }
    return null;
  }

  // Prüft den Zeitraum schon beim Ausfüllen, nicht erst beim Speichern.
  function checkSchedule() {
    let problem = inputProblem();
    if (!problem && startInput.value && endInput.value && endInput.value < startInput.value) {
      problem = "Das Enddatum darf nicht vor dem Startdatum liegen.";
    }
    if (problem) {
      formMessage.show(problem, true);
    } else {
      formMessage.clear();
    }
  }

  // Die Kunden der Auswahl. Der Kunde des bearbeiteten Projekts gehört immer dazu, auch wenn
  // er nicht (mehr) in der Kundenliste steht – sonst ließe sich das Projekt nicht speichern.
  function customerChoices() {
    if (!editingProject || customers.some((c) => c.id === editingProject.customer_id)) {
      return customers;
    }
    const own = { id: editingProject.customer_id, name: editingProject.customer_name };
    return [...customers, own];
  }

  function syncCustomerInputs() {
    const useSelect = customerSource === "customers";
    customerSelectWrap.hidden = !useSelect;
    customerFallbackWrap.hidden = useSelect;

    const currentSelect = customerSelect.value;
    customerSelect.replaceChildren(
      el("option", { value: "" }, "Bitte Kunde wählen …"),
      ...customerChoices().map((c) =>
        el("option", { value: String(c.id) }, `${c.name} (#${c.id})`),
      ),
    );
    if (currentSelect) {
      customerSelect.value = currentSelect;
    }

    customerDatalist.replaceChildren(
      ...customers.map((c) => el("option", { value: String(c.id) }, c.name)),
    );

    const currentFilter = customerFilter.value;
    customerFilter.replaceChildren(
      el("option", { value: "" }, "Alle Kunden"),
      ...customers.map((c) => el("option", { value: String(c.id) }, c.name)),
    );
    if (currentFilter) {
      customerFilter.value = currentFilter;
    }
  }

  function openForm(project = null) {
    formMessage.clear();
    editingProject = project;
    nameTyped = false;
    syncCustomerInputs();
    formTitle.textContent = project ? `Projekt #${project.id} bearbeiten` : "Neues Projekt anlegen";
    saveButton.textContent = project ? "Änderungen speichern" : "Projekt anlegen";

    if (project) {
      customerSelect.value = String(project.customer_id);
      customerIdInput.value = String(project.customer_id);
      customerNameInput.value = project.customer_name || "";
      nameInput.value = project.name;
      siteInput.value = project.baustelle || "";
      statusSelect.value = project.status;
      startInput.value = project.start_date || "";
      durationInput.value = project.duration_days ? String(project.duration_days) : "";
      endInput.value = project.end_date || "";
      notesInput.value = project.notes || "";
    } else {
      customerSelect.value = "";
      customerIdInput.value = "";
      customerNameInput.value = "";
      nameInput.value = "";
      siteInput.value = "";
      statusSelect.value = "angefragt";
      startInput.value = "";
      durationInput.value = "";
      endInput.value = "";
      notesInput.value = "";
    }
    form.hidden = false;
    updateSaveButton();
    (customerSource === "customers" ? customerSelect : customerIdInput).focus();
  }

  function closeForm() {
    form.hidden = true;
    editingProject = null;
    formMessage.clear();
    newButton.focus();
  }

  function renderProjectList() {
    if (projects.length === 0) {
      let text = "Noch keine Projekte angelegt. Mit „Neues Projekt“ legen Sie den ersten an.";
      if (searchInput.value.trim() || statusFilter.value || customerFilter.value) {
        text = "Zu Ihrer Suche wurden keine Projekte gefunden.";
      } else if (!archivedToggle.checked) {
        text =
          "Keine aktiven Projekte. Mit „Neues Projekt“ legen Sie eines an; " +
          "archivierte sehen Sie über „Archivierte anzeigen“.";
      }
      listArea.replaceChildren(el("p", { class: "empty" }, text));
      return;
    }

    const list = el("ul", { class: "projects-list" });
    for (const project of projects) {
      const statusChoice = el(
        "select",
        {
          id: `projects-status-${project.id}`,
          name: `status_${project.id}`,
          class: "projects-status-select",
          "aria-label": `Status für ${project.name}`,
          onchange: async (event) => {
            message.clear();
            try {
              await sendJson("PATCH", `/api/projects/${project.id}/status`, {
                status: event.target.value,
              });
              message.show(
                `Status von „${project.name}“ auf „${STATUS_LABEL[event.target.value]}“ gesetzt.`,
              );
              await reloadAll();
              // Die Liste ist neu aufgebaut: Wer mit der Tastatur arbeitet, bleibt am Feld.
              document.getElementById(`projects-status-${project.id}`)?.focus();
            } catch (error) {
              message.show(errorText(error), true);
              event.target.value = project.status;
            }
          },
        },
        ...STATUS_OPTIONS.map((opt) => el("option", { value: opt.value }, opt.label)),
      );
      statusChoice.value = project.status;

      const editBtn = el(
        "button",
        {
          type: "button",
          class: "projects-button-quiet",
          "aria-label": `Bearbeiten: ${project.name}`,
          onclick: () => openForm(project),
        },
        "Bearbeiten",
      );
      const archiveBtn = el(
        "button",
        {
          type: "button",
          class: "projects-button-quiet",
          "aria-label": `${project.archived ? "Wiederherstellen" : "Archivieren"}: ${project.name}`,
          onclick: async () => {
            message.clear();
            const nextArchived = !project.archived;
            try {
              await sendJson("POST", `/api/projects/${project.id}/archive`, {
                archived: nextArchived,
              });
              message.show(
                nextArchived
                  ? `Projekt „${project.name}“ archiviert.`
                  : `Projekt „${project.name}“ wiederhergestellt.`,
              );
              await reloadAll();
            } catch (error) {
              message.show(errorText(error), true);
            }
          },
        },
        project.archived ? "Wiederherstellen" : "Archivieren",
      );

      const titleWrap = el(
        "div",
        { class: "projects-title-wrap" },
        el("span", { class: "projects-name" }, project.name),
      );
      if (project.archived) {
        titleWrap.append(el("span", { class: "projects-badge" }, "Archiviert"));
      }

      const facts = el(
        "dl",
        { class: "projects-facts" },
        makeFact("Kunde:", `${project.customer_name} (#${project.customer_id})`),
        makeFact("Baustelle:", project.baustelle || "–"),
        makeFact("Zeitraum:", formatRange(project)),
      );

      const item = el(
        "li",
        { class: "projects-item" },
        el("div", { class: "projects-item-head" }, titleWrap, statusChoice),
        facts,
      );
      if (project.notes) {
        item.append(el("p", { class: "projects-meta" }, project.notes));
      }
      item.append(el("div", { class: "projects-row-actions" }, editBtn, archiveBtn));
      list.append(item);
    }

    listArea.replaceChildren(list);
  }

  function renderCustomerGroups() {
    if (customerGroups.length === 0) {
      customerArea.replaceChildren(
        el("p", { class: "empty" }, "Noch keine Kunden mit Projekten vorhanden."),
      );
      return;
    }

    const cards = customerGroups.map((group) => {
      const heading = el("h2", {}, `${group.customer.name} (Kunde #${group.customer.id})`);
      if (group.projects.length === 0) {
        return el(
          "article",
          { class: "projects-group-card" },
          heading,
          el("p", { class: "projects-hint" }, "Noch keine Projekte bei diesem Kunden."),
        );
      }

      const items = el(
        "ul",
        { class: "projects-group-items" },
        ...group.projects.map((project) => {
          const titleWrap = el(
            "div",
            { class: "projects-title-wrap" },
            el("span", { class: "projects-name" }, project.name),
          );
          if (project.archived) {
            titleWrap.append(el("span", { class: "projects-badge" }, "Archiviert"));
          }
          const left = el(
            "div",
            {},
            titleWrap,
            el(
              "span",
              { class: "projects-meta" },
              `${project.baustelle || "Ohne Baustelle"} · ${formatRange(project)}`,
            ),
          );
          const right = el(
            "div",
            { class: "projects-row-actions" },
            el("span", { class: "projects-badge" }, STATUS_LABEL[project.status] ?? project.status),
            el(
              "button",
              {
                type: "button",
                class: "projects-button-quiet",
                "aria-label": `Bearbeiten: ${project.name}`,
                onclick: () => openForm(project),
              },
              "Bearbeiten",
            ),
          );
          return el("li", {}, left, right);
        }),
      );
      return el("article", { class: "projects-group-card" }, heading, items);
    });

    customerArea.replaceChildren(el("div", { class: "projects-group-list" }, ...cards));
  }

  function updateViewVisibility() {
    const isList = viewMode === "list";
    listArea.hidden = !isList;
    customerArea.hidden = isList;
    toolbar.hidden = !isList;
    for (const [tab, selected] of [
      [listViewBtn, isList],
      [customerViewBtn, !isList],
    ]) {
      tab.setAttribute("aria-selected", String(selected));
      tab.tabIndex = selected ? 0 : -1;
    }
  }

  function showView(mode) {
    viewMode = mode;
    updateViewVisibility();
  }

  // Wie bei jeder Tab-Ansicht: Pfeiltasten, Pos1 und Ende wechseln die Ansicht.
  function onTabKey(event) {
    const target = {
      ArrowLeft: viewMode === "list" ? "customers" : "list",
      ArrowRight: viewMode === "list" ? "customers" : "list",
      Home: "list",
      End: "customers",
    }[event.key];
    if (target) {
      event.preventDefault();
      showView(target);
      (target === "list" ? listViewBtn : customerViewBtn).focus();
    }
  }

  function buildProjectsQuery() {
    const params = new URLSearchParams();
    if (searchInput.value.trim()) {
      params.set("text", searchInput.value.trim());
    }
    if (statusFilter.value) {
      params.set("status", statusFilter.value);
    }
    if (customerFilter.value) {
      params.set("customer_id", customerFilter.value);
    }
    if (archivedToggle.checked) {
      params.set("include_archived", "true");
    }
    const query = params.toString();
    return query ? `/api/projects?${query}` : "/api/projects";
  }

  // Nach erfolgreichem Laden verschwindet eine alte Fehlermeldung.
  function clearLoadError() {
    if (message.dataset.kind === "error") {
      message.clear();
    }
  }

  async function reloadProjectsOnly() {
    const request = ++listRequest;
    try {
      const result = await getJson(buildProjectsQuery());
      if (request !== listRequest) {
        return;
      }
      projects = result;
      clearLoadError();
      renderProjectList();
    } catch (error) {
      message.show(errorText(error), true);
    }
  }

  async function reloadAll() {
    const request = ++overviewRequest;
    const ownListRequest = ++listRequest;
    const archiveParam = archivedToggle.checked ? "?include_archived=true" : "";
    try {
      const [customerResp, projectResp, groupResp] = await Promise.all([
        getJson("/api/projects/customers"),
        getJson(buildProjectsQuery()),
        getJson(`/api/projects/by-customer${archiveParam}`),
      ]);
      if (request !== overviewRequest) {
        return;
      }
      customerSource = customerResp.source;
      customers = customerResp.customers;
      customerGroups = groupResp;
      if (ownListRequest === listRequest) {
        projects = projectResp;
      }
      clearLoadError();
      syncCustomerInputs();
      renderProjectList();
      renderCustomerGroups();
      updateSaveButton();
    } catch (error) {
      message.show(errorText(error), true);
    }
  }

  // --- Ereignisse ---

  newButton.addEventListener("click", () => openForm(null));
  cancelButton.addEventListener("click", closeForm);

  customerSelect.addEventListener("change", updateSaveButton);
  customerIdInput.addEventListener("input", () => {
    // Der Name folgt der Nummer, solange er nicht selbst eingetippt wurde. Sonst bliebe beim
    // Wechsel der Nummer der Name des vorigen Kunden stehen.
    if (!nameTyped) {
      const cid = selectedCustomerId();
      customerNameInput.value = customers.find((c) => c.id === cid)?.name ?? "";
    }
    updateSaveButton();
  });
  customerNameInput.addEventListener("input", () => {
    nameTyped = customerNameInput.value.trim().length > 0;
  });
  nameInput.addEventListener("input", updateSaveButton);
  startInput.addEventListener("input", syncEndDate);
  durationInput.addEventListener("input", syncEndDate);
  endInput.addEventListener("change", syncDuration);
  for (const input of [startInput, durationInput, endInput]) {
    input.addEventListener("change", checkSchedule);
  }

  // app.js baut jeden Reiter nur einmal auf. Damit Einträge von anderen Geräten (LS-03) und
  // neue Kunden erscheinen, wird bei jeder Rückkehr neu geladen.
  window.addEventListener("hashchange", () => {
    if (window.location.hash === `#${id}`) {
      reloadAll();
    }
  });
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && !panel.hidden) {
      reloadAll();
    }
  });

  searchInput.addEventListener("input", () => {
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(reloadProjectsOnly, 200);
  });
  statusFilter.addEventListener("change", reloadProjectsOnly);
  customerFilter.addEventListener("change", reloadProjectsOnly);
  archivedToggle.addEventListener("change", reloadAll);

  listViewBtn.addEventListener("click", () => showView("list"));
  customerViewBtn.addEventListener("click", () => showView("customers"));
  listViewBtn.addEventListener("keydown", onTabKey);
  customerViewBtn.addEventListener("keydown", onTabKey);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (saving) {
      return;
    }
    formMessage.clear();
    message.clear();

    const cid = selectedCustomerId();
    if (cid === null) {
      formMessage.show("Bitte zuerst einen Kunden angeben.", true);
      return;
    }
    const problem = inputProblem();
    if (problem) {
      formMessage.show(problem, true);
      return;
    }

    const payload = {
      customer_id: cid,
      name: nameInput.value.trim(),
      baustelle: siteInput.value.trim(),
      status: statusSelect.value,
      start_date: startInput.value || null,
      duration_days: durationValue(),
      end_date: endInput.value || null,
      notes: notesInput.value.trim(),
    };
    if (customerSource !== "customers") {
      payload.customer_name = customerNameInput.value.trim();
    }

    // Solange gespeichert wird, ist der Knopf gesperrt – ein Doppelklick legt nichts doppelt an.
    const editing = editingProject;
    saving = true;
    updateSaveButton();
    try {
      const saved = editing
        ? await sendJson("PATCH", `/api/projects/${editing.id}`, payload)
        : await sendJson("POST", "/api/projects", payload);
      closeForm();
      message.show(`Projekt „${saved.name}“ wurde ${editing ? "gespeichert" : "angelegt"}.`);
      await reloadAll();
    } catch (error) {
      formMessage.show(errorText(error), true);
    } finally {
      saving = false;
      updateSaveButton();
    }
  });

  updateViewVisibility();
  return reloadAll();
}
