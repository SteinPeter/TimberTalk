// Der Abschnitt „Fahrzeuge und Maschinen“ im Reiter „Einstellungen“ (Feature F8):
// Fahrzeuge und Maschinen anlegen, ausmustern und – bei Fahrzeugen – den Kilometersatz für
// Fahrtbuchungen eintragen. Sie erscheinen als eigene Zeilen auf der Plantafel im Kalender.
// Sichtbar mit dem Recht „calendar.dispatch“. Den Kilometersatz sieht nur, wer „finance.view“
// hat, und ändert nur, wer „finance.edit“ hat. Eingetragen in settings/sections.js.

import { getJson, sendJson } from "../../../shared/api.js";
import { el, field, messageBox } from "../../../shared/dom.js";
import { can } from "../../../shared/session.js";

export const id = "planning-resources";
export const title = "Fahrzeuge und Maschinen";
export const permission = "calendar.dispatch";

const CATEGORIES = [
  ["vehicle", "Fahrzeug"],
  ["machine", "Maschine"],
];

const euro = (value) => Number(value).toLocaleString("de-DE", { style: "currency", currency: "EUR", maximumFractionDigits: 3 });

// „0,55“ oder „0.55“ → „0.55“; leer → ""; keine Zahl → null.
function toDecimalText(input) {
  const text = input.trim().replace(",", ".");
  if (text === "") {
    return "";
  }
  return /^\d+(\.\d+)?$/.test(text) ? text : null;
}

export function render(container) {
  const showRates = can("finance.view");
  const editRates = can("finance.edit");

  const tableBody = el("tbody");
  const empty = el("p", { class: "empty" }, "Noch keine Fahrzeuge oder Maschinen angelegt.");
  const headers = ["Name", "Art", ...(showRates ? ["€ je km"] : []), "Status", ""];
  const table = el(
    "div",
    { class: "table-scroll" },
    el(
      "table",
      { class: "table" },
      el("thead", {}, el("tr", {}, ...headers.map((text) => el("th", { scope: "col" }, text)))),
      tableBody,
    ),
  );
  const listMessage = messageBox();

  // Anlegen braucht man selten – das Formular erscheint erst nach einem Klick.
  const newButton = el("button", { type: "button", class: "button" }, "+ Neu anlegen");
  const nameInput = el("input", { type: "text", autocomplete: "off", required: "", placeholder: "z. B. Transporter B-TT 123" });
  const categorySelect = el("select", {}, ...CATEGORIES.map(([value, label]) => el("option", { value }, label)));
  const addButton = el("button", { type: "submit", class: "button", disabled: true }, "Anlegen");
  const form = el(
    "form",
    { class: "form", novalidate: "", hidden: true },
    el("h2", {}, "Neu anlegen"),
    el("div", { class: "form-row" }, field("Name", nameInput), field("Art", categorySelect)),
    el(
      "div",
      { class: "form-actions" },
      addButton,
      el("button", { type: "button", class: "button-quiet", onclick: () => showForm(false) }, "Abbrechen"),
    ),
  );

  container.append(
    el(
      "p",
      { class: "form-hint accounts-intro" },
      "Was hier steht, lässt sich im Kalender wie eine Person einplanen. Mit dem Kilometersatz eines " +
        "Fahrzeugs werden Fahrten auf Projekte gebucht.",
    ),
    el("div", { class: "form-actions" }, newButton),
    form,
    listMessage,
    empty,
    table,
  );

  function showForm(visible) {
    form.hidden = !visible;
    newButton.hidden = visible;
    if (visible) {
      nameInput.focus();
    }
  }

  // Der Kilometersatz: mit „finance.edit“ ein Feld, das beim Verlassen speichert, sonst Text.
  function rateCell(resource) {
    if (resource.category !== "vehicle") {
      return el("td", {}, "–");
    }
    if (!editRates) {
      return el("td", {}, resource.rate_per_km ? euro(resource.rate_per_km) : "fehlt");
    }
    const input = el("input", {
      type: "text",
      inputmode: "decimal",
      class: "resources-rate",
      placeholder: "z. B. 0,55",
      value: resource.rate_per_km ? Number(resource.rate_per_km).toLocaleString("de-DE") : "",
      "aria-label": `Euro je km für ${resource.name}`,
    });
    input.addEventListener("change", async () => {
      const value = toDecimalText(input.value);
      if (value === null) {
        listMessage.show("Der Kilometersatz muss eine Zahl sein, z. B. 0,55.", true);
        return;
      }
      try {
        await sendJson("PUT", `/api/planning/resources/${resource.id}/rate`, { rate_per_km: value || null });
        listMessage.show(value ? `${resource.name}: ${euro(value)} je km gespeichert.` : `${resource.name}: Kilometersatz entfernt.`);
      } catch (error) {
        listMessage.show(error.message, true);
      }
    });
    return el("td", {}, input);
  }

  function show(list) {
    empty.hidden = list.length > 0;
    table.hidden = list.length === 0;
    tableBody.replaceChildren(
      ...list.map((resource) =>
        el(
          "tr",
          {},
          el("td", {}, resource.name),
          el("td", {}, resource.category_label),
          ...(showRates ? [rateCell(resource)] : []),
          el("td", {}, resource.active ? "Im Einsatz" : "Ausgemustert"),
          el(
            "td",
            {},
            el(
              "button",
              {
                type: "button",
                class: "button-quiet",
                "aria-label": `${resource.name} ${resource.active ? "ausmustern" : "wieder in Einsatz nehmen"}`,
                onclick: () => toggle(resource),
              },
              resource.active ? "Ausmustern" : "Wieder in Einsatz",
            ),
          ),
        ),
      ),
    );
  }

  async function load() {
    try {
      show(await getJson("/api/planning/resources?include_inactive=true"));
    } catch (error) {
      listMessage.show(error.message, true);
    }
  }

  // Ausmustern statt löschen: Alte Termine und Fahrten behalten ihr Fahrzeug.
  async function toggle(resource) {
    listMessage.clear();
    try {
      await sendJson("PUT", `/api/planning/resources/${resource.id}`, {
        name: resource.name,
        category: resource.category,
        active: !resource.active,
      });
      await load();
      listMessage.show(resource.active ? `Ausgemustert: ${resource.name}.` : `Wieder im Einsatz: ${resource.name}.`);
    } catch (error) {
      listMessage.show(error.message, true);
    }
  }

  newButton.addEventListener("click", () => showForm(true));
  nameInput.addEventListener("input", () => {
    addButton.disabled = !nameInput.value.trim();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    listMessage.clear();
    try {
      const created = await sendJson("POST", "/api/planning/resources", {
        name: nameInput.value,
        category: categorySelect.value,
      });
      form.reset();
      addButton.disabled = true;
      showForm(false);
      await load();
      listMessage.show(
        created.category === "vehicle" && editRates
          ? `Angelegt: ${created.name}. Jetzt noch den Kilometersatz eintragen.`
          : `Angelegt: ${created.name}.`,
      );
    } catch (error) {
      listMessage.show(error.message, true);
    }
  });

  return load();
}
