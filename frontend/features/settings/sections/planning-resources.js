// Der Abschnitt „Fahrzeuge und Maschinen“ im Reiter „Einstellungen“ (Feature F8):
// Fahrzeuge und Maschinen anlegen, umbenennen und ausmustern. Sie erscheinen dann als eigene
// Zeilen auf der Plantafel im Kalender. Nur mit dem Recht „calendar.dispatch“ sichtbar.
// Eingetragen in settings/sections.js.

import { getJson, sendJson } from "../../../shared/api.js";
import { el, field, messageBox } from "../../../shared/dom.js";

export const id = "planning-resources";
export const title = "Fahrzeuge und Maschinen";
export const permission = "calendar.dispatch";

const CATEGORIES = [
  ["vehicle", "Fahrzeug"],
  ["machine", "Maschine"],
];

export function render(container) {
  const tableBody = el("tbody");
  const empty = el("p", { class: "empty" }, "Noch keine Fahrzeuge oder Maschinen angelegt.");
  const table = el(
    "div",
    { class: "table-scroll" },
    el(
      "table",
      { class: "table" },
      el("thead", {}, el("tr", {}, ...["Name", "Art", "Status", ""].map((text) => el("th", { scope: "col" }, text)))),
      tableBody,
    ),
  );
  const listMessage = messageBox();

  const nameInput = el("input", { type: "text", autocomplete: "off", required: "", placeholder: "z. B. Transporter B-TT 123" });
  const categorySelect = el("select", {}, ...CATEGORIES.map(([value, label]) => el("option", { value }, label)));
  const addButton = el("button", { type: "submit", class: "button", disabled: true }, "Anlegen");
  const formMessage = messageBox();
  const form = el(
    "form",
    { class: "form", novalidate: "" },
    el("h2", {}, "Neu anlegen"),
    el("div", { class: "form-row" }, field("Name", nameInput), field("Art", categorySelect)),
    el("div", { class: "form-actions" }, addButton),
    formMessage,
  );

  container.append(
    el("p", { class: "form-hint accounts-intro" }, "Was hier steht, lässt sich im Kalender wie eine Person einplanen."),
    empty,
    table,
    listMessage,
    form,
  );

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

  // Ausmustern statt löschen: Alte Termine behalten ihr Fahrzeug.
  async function toggle(resource) {
    listMessage.clear();
    try {
      await sendJson("PUT", `/api/planning/resources/${resource.id}`, {
        name: resource.name,
        category: resource.category,
        active: !resource.active,
      });
      listMessage.show(resource.active ? `Ausgemustert: ${resource.name}.` : `Wieder im Einsatz: ${resource.name}.`);
      await load();
    } catch (error) {
      listMessage.show(error.message, true);
    }
  }

  nameInput.addEventListener("input", () => {
    addButton.disabled = !nameInput.value.trim();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    formMessage.clear();
    try {
      const created = await sendJson("POST", "/api/planning/resources", {
        name: nameInput.value,
        category: categorySelect.value,
      });
      form.reset();
      addButton.disabled = true;
      formMessage.show(`Angelegt: ${created.name}.`);
      await load();
    } catch (error) {
      formMessage.show(error.message, true);
    }
  });

  return load();
}
