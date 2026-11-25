// Projekte suchen, bearbeiten und als Entwurf vorlegen; Daten werden sicher als Text eingesetzt.
import { getJson } from "../../shared/api.js";

export const id = "projects";
export const title = "Projekte";
const statuses = {
  angefragt: "Angefragt", geplant: "Geplant", in_arbeit: "In Arbeit",
  abgeschlossen: "Abgeschlossen", abgerechnet: "Abgerechnet",
};

// Der gemeinsame S-10-Reiter liefert diese Aktionen samt angemeldetem Benutzer.
// Keine erfundene Benutzer-ID und kein direkter Datenbankzugriff aus dem Browser.
let confirmation = null;
export function connectConfirmation(actions) {
  confirmation = actions;
}

function element(tag, text, parent) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (parent) parent.append(node);
  return node;
}

function field(form, labelText, name, type = "text") {
  const label = element("label", labelText, form);
  const input = element("input", undefined, label);
  input.name = name;
  input.type = type;
  return input;
}

function select(form, labelText, options) {
  const label = element("label", labelText, form);
  const input = element("select", undefined, label);
  for (const [value, text] of options) {
    const option = element("option", text, input);
    option.value = value;
  }
  return input;
}

function button(parent, text, action) {
  const node = element("button", text, parent);
  node.type = "button";
  if (action) node.addEventListener("click", action);
  return node;
}

function unwrap(result) {
  if (result.status === "rueckfrage") throw new Error(result.rueckfrage.frage);
  if (result.status !== "ok") throw new Error(result.fehler?.meldung || "Die Anfrage ist fehlgeschlagen.");
  return result.daten;
}

export async function render(panel) {
  panel.replaceChildren();
  // Ausschließlich statische, auf diesen Reiter begrenzte Gestaltung.
  const style = element("style", undefined, panel);
  style.textContent = `
    #projects label { display: grid; gap: .3rem; margin-block: .7rem; }
    #projects input, #projects select, #projects button {
      font: inherit; color: var(--text); background: var(--card);
      border: 1px solid var(--muted); border-radius: .4rem;
      padding: .6rem .75rem; min-height: 2.75rem; box-sizing: border-box;
    }
    #projects input, #projects select { width: 100%; min-width: 0; }
    #projects button { cursor: pointer; margin: .25rem .5rem .25rem 0; max-width: 100%; overflow-wrap: anywhere; }
    #projects button:not(:disabled):hover { border-color: var(--accent); }
    #projects button:not(:disabled):active { background: var(--page); }
    #projects button:disabled { cursor: not-allowed; color: var(--muted); background: var(--page); border-style: dashed; }
    #projects :focus-visible { outline: 3px solid var(--accent); outline-offset: 3px; }
    #projects article, #projects fieldset {
      min-width: 0; margin-block: 1rem; padding: 1rem;
      border: 1px solid var(--line); border-radius: .5rem; background: var(--card);
    }
    #projects h2 { font-size: 1.2rem; margin-block: .3rem; }
    #projects p, #projects li { overflow-wrap: anywhere; }
    #projects .projects-message { white-space: pre-wrap; }
    #projects [hidden] { display: none; }
  `;
  element("h1", "Projekte", panel);
  element("p", "Kunden, Baustellen und Projektstatus im Überblick.", panel);
  const message = element("p", "Projekte werden geladen …", panel);
  message.className = "projects-message";
  message.setAttribute("role", "status");
  message.setAttribute("aria-live", "polite");
  const controls = element("div", undefined, panel);
  const add = button(controls, "Projekt anlegen", () => edit());
  const refresh = button(controls, "Aktualisieren", () => initialize());
  const filter = element("form", undefined, panel);
  const query = field(filter, "Projekt, Kunde oder Baustelle suchen", "text", "search");
  const customerFilter = select(filter, "Kunde", [["", "Alle Kunden"]]);
  const statusFilter = select(filter, "Status", [["", "Alle Status"], ...Object.entries(statuses)]);
  const archiveFilter = select(filter, "Ansicht", [["false", "Aktive Projekte"], ["true", "Archiv"]]);
  const search = button(filter, "Suchen"); search.type = "submit";
  const editor = element("section", undefined, panel);
  const draftPanel = element("section", undefined, panel);
  const results = element("section", undefined, panel);
  results.setAttribute("aria-label", "Suchergebnisse");
  const pager = element("div", undefined, panel);
  let offset = 0;
  let customers = [];
  let ready = false;
  let sequence = 0;
  let submitting = false;
  let pendingDraft = false;

  // Nach jedem Zustandswechsel auch bereits gerenderte Projektaktionen aktualisieren.
  function updateActionButtons() {
    const disabled = !ready || pendingDraft || submitting;
    add.disabled = disabled || !customers.length;
    for (const action of results.querySelectorAll("button")) action.disabled = disabled;
    for (const action of editor.querySelectorAll("button")) action.disabled = disabled;
  }

  async function initialize() {
    refresh.disabled = true;
    try {
      const state = await getJson("/api/projects/readiness");
      ready = state.ready && getJson.length >= 2;
      const response = await getJson("/api/projects/customers");
      customers = response.status === "ok" ? response.daten : [];
      customerFilter.replaceChildren();
      for (const [value, text] of [["", "Alle Kunden"], ...customers.map(c => [String(c.id), c.name])]) {
        const option = element("option", text, customerFilter); option.value = value;
      }
      const loaded = await load();
      if (loaded && !ready) message.textContent = "Das Anlegen und Ändern ist noch nicht verfügbar. Die Projektsuche kann verwendet werden; bei Fragen hilft die Projektbetreuung.";
      else if (loaded && !customers.length) message.textContent = "Keine Kunden verfügbar. Für ein neues Projekt muss zuerst ein Kunde angelegt werden.";
    } catch (error) {
      ready = false;
      message.textContent = `Laden fehlgeschlagen: ${error.message}. Bitte erneut aktualisieren.`;
    } finally {
      refresh.disabled = false;
      updateActionButtons();
    }
  }

  async function load() {
    const current = ++sequence;
    const params = new URLSearchParams({text: query.value, archiviert: archiveFilter.value, offset});
    if (customerFilter.value) params.set("kunde_id", customerFilter.value);
    if (statusFilter.value) params.set("status", statusFilter.value);
    message.textContent = "Projekte werden geladen …";
    try {
      const data = unwrap(await getJson(`/api/projects?${params}`));
      if (current !== sequence) return;
      results.replaceChildren(); pager.replaceChildren();
      message.textContent = `${data.gesamt} Projekt(e) gefunden.`;
      if (!data.treffer.length) element("p", "Keine passenden Projekte. Ändern Sie die Suche oder legen Sie ein Projekt an.", results);
      for (const item of data.treffer) {
        const card = element("article", undefined, results);
        element("h2", item.name, card);
        element("p", `${item.kunde} · ${item.baustelle_ort || "Baustelle noch offen"}`, card);
        element("p", `${statuses[item.status] || item.status}${item.archiviert ? " · Archiviert" : ""}`, card);
        if (item.start) element("p", `Beginn: ${item.start}${item.ende ? ` · Ende: ${item.ende}` : ""}`, card);
        if (!item.archiviert) {
          const change = button(card, "Bearbeiten", () => edit(item));
          const state = button(card, "Status ändern", () => editStatus(item));
          const archive = button(card, "Archivierung vorbereiten", () => submit("projekt_archivieren", {projekt_id: item.projekt_id}));
          for (const action of [change, state, archive]) action.disabled = !ready || pendingDraft || submitting;
        }
      }
      const previous = button(pager, "Zurück", () => { offset = Math.max(0, offset - 10); load(); });
      previous.disabled = offset === 0;
      const next = button(pager, "Weitere Projekte", () => { offset += 10; load(); });
      next.disabled = !data.weitere;
      return true;
    } catch (error) {
      if (current === sequence) message.textContent = `Suche fehlgeschlagen: ${error.message}`;
      return false;
    }
  }

  function edit(item = null) {
    editor.replaceChildren();
    const form = element("form", undefined, editor);
    const fields = element("fieldset", undefined, form);
    element("legend", item ? "Projekt bearbeiten" : "Neues Projekt", fields);
    const name = field(fields, "Projektname (Pflichtfeld)", "name");
    name.required = true; name.maxLength = 200; name.value = item?.name || "";
    const customer = select(fields, "Kunde (Pflichtfeld)", [["", "Bitte auswählen"], ...customers.map(c => [String(c.id), c.name])]);
    customer.required = true; customer.value = String(item?.kunde_id || "");
    const site = field(fields, "Baustelle", "site"); site.maxLength = 500; site.value = item?.baustelle_ort || "";
    const start = field(fields, "Beginn (optional)", "start", "date"); start.value = item?.start || "";
    const days = field(fields, "Dauer in Kalendertagen (optional)", "days", "number");
    days.min = "1"; days.max = "36500"; days.step = "1"; days.value = item?.dauer_tage || "";
    const save = button(fields, "Änderungen prüfen"); save.type = "submit";
    button(fields, "Abbrechen", () => { editor.replaceChildren(); add.focus(); });
    form.addEventListener("submit", async event => {
      event.preventDefault();
      if (!form.reportValidity() || submitting) return;
      const values = {name: name.value.trim(), kunde_id: Number(customer.value), baustelle_ort: site.value.trim(),
        start: start.value || null, dauer_tage: days.value ? Number(days.value) : null};
      if (!values.name) { name.setCustomValidity("Bitte einen Projektnamen eingeben."); name.reportValidity(); return; }
      save.disabled = true;
      try { await submit(item ? "projekt_aendern" : "projekt_anlegen", item ? {projekt_id: item.projekt_id, feldern: values} : values); }
      finally { updateActionButtons(); }
    });
    name.addEventListener("input", () => name.setCustomValidity(""));
    name.focus();
  }

  function editStatus(item) {
    editor.replaceChildren();
    element("h2", `Status ändern: ${item.name}`, editor);
    const input = select(editor, "Neuer Status", Object.entries(statuses)); input.value = item.status;
    button(editor, "Änderung prüfen", () => submit("projekt_status_setzen", {projekt_id: item.projekt_id, status: input.value}));
    button(editor, "Abbrechen", () => editor.replaceChildren()); input.focus();
  }

  async function submit(name, args) {
    if (!ready || submitting || pendingDraft) return;
    submitting = true;
    updateActionButtons();
    message.textContent = "Änderungen werden geprüft …";
    try {
      const result = await getJson("/api/projects/tools", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({name, args, quelle: "ui"})});
      if (result.status !== "ok") { unwrap(result); return; }
      if (!Number.isInteger(result.entwurf_id)) throw new Error("Die Antwort enthält keinen gültigen Entwurf.");
      pendingDraft = true; editor.replaceChildren(); draftPanel.replaceChildren();
      const box = element("fieldset", undefined, draftPanel);
      element("legend", "Änderungen vor dem Speichern prüfen", box);
      element("p", result.zusammenfassung || "Die Änderungen wurden als Entwurf vorbereitet.", box);
      const list = element("ul", undefined, box);
      for (const change of result.aenderungen || []) element("li", `${change.feld}: ${change.alt ?? "–"} → ${change.neu ?? "–"}`, list);
      const accept = button(box, "Bestätigen und speichern", () => finish("confirm", result.entwurf_id));
      const reject = button(box, "Entwurf verwerfen", () => finish("reject", result.entwurf_id));
      accept.disabled = !confirmation?.confirm; reject.disabled = !confirmation?.reject;
      if (!confirmation) element("p", "Der Entwurf ist noch nicht gespeichert. Die gemeinsame Bestätigungsfunktion ist noch nicht angeschlossen.", box);
      if (!accept.disabled) accept.focus();
      else if (!reject.disabled) reject.focus();
      else { box.tabIndex = -1; box.focus(); }
      await load();
    } catch (error) { message.textContent = error.message; }
    finally { submitting = false; updateActionButtons(); }
  }

  async function finish(action, draftId) {
    if (submitting || !confirmation?.[action]) return;
    submitting = true;
    updateActionButtons();
    message.textContent = action === "confirm" ? "Änderungen werden gespeichert …" : "Entwurf wird verworfen …";
    for (const control of draftPanel.querySelectorAll("button")) control.disabled = true;
    try {
      const result = await confirmation[action](draftId);
      if (!((action === "confirm" && result.status === "ok") || (action === "reject" && result.status === "verworfen"))) throw new Error(result.fehler?.meldung || "Der Entwurf konnte nicht abgeschlossen werden.");
      pendingDraft = false; draftPanel.replaceChildren();
      const loaded = await load();
      const outcome = action === "confirm" ? "Änderungen gespeichert." : "Entwurf verworfen. Es wurde nichts geändert.";
      message.textContent = loaded ? outcome : `${outcome} Die Projektliste konnte nicht aktualisiert werden. Bitte erneut suchen.`;
    } catch (error) { message.textContent = error.message; }
    finally {
      submitting = false; updateActionButtons();
      const [accept, reject] = draftPanel.querySelectorAll("button");
      if (accept) accept.disabled = !confirmation?.confirm;
      if (reject) reject.disabled = !confirmation?.reject;
      if (!pendingDraft && !add.disabled) add.focus();
    }
  }

  filter.addEventListener("submit", event => { event.preventDefault(); offset = 0; load(); });
  await initialize();
}

// Der Kundenreiter kann diese Liste einbinden, ohne Projektlogik zu kopieren.
export async function renderCustomerProjects(container, customerId, archived = false) {
  container.replaceChildren();
  const message = element("p", "Projekte werden geladen …", container);
  message.setAttribute("role", "status");
  try {
    const rows = unwrap(await getJson(`/api/projects/customer/${encodeURIComponent(customerId)}?archiviert=${archived}`));
    message.textContent = rows.length ? `${rows.length} Projekt(e)` : "Noch keine Projekte vorhanden.";
    const list = element("ul", undefined, container);
    for (const row of rows) element("li", `${row.name} · ${row.baustelle_ort || "Baustelle offen"} · ${statuses[row.status]}${row.archiviert ? " · Archiviert" : ""}`, list);
  } catch (error) { message.textContent = `Projekte konnten nicht geladen werden: ${error.message}`; }
}
