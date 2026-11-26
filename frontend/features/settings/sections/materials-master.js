// Der Abschnitt „Materialstamm“ im Reiter „Einstellungen“ (Feature F5):
// Materialien anlegen und ihnen Preise mit Gültigkeitsdatum geben.
// Eingetragen ist der Abschnitt in settings/sections.js.

import { getJson } from "../../../shared/api.js";
import {
  el,
  field,
  formatDate,
  formatEuro,
  messageBox,
  sendJson,
  today,
  toDecimalText,
} from "../../bookings/materials-helpers.js";

// Vorschläge für die Einheit – man darf auch etwas anderes eintippen.
const UNITS = ["m³", "m²", "m", "Stk", "kg", "l", "Pack"];

export const id = "materials-master";
export const title = "Materialstamm";
// Nur für Konten, die Preise sehen dürfen (F10). Ändern prüft das Backend mit „finance.edit“.
export const permission = "finance.view";

// Baut den Abschnitt in `container` auf.
export function render(container) {
  let materials = [];

  const message = messageBox(); // gehört zum Formular „Material anlegen“
  const priceMessage = messageBox(); // gehört zum Formular „Preis eintragen“
  const tableBody = el("tbody");
  const empty = el("p", { class: "empty" }, "Noch kein Material angelegt.");
  const tableWrap = el(
    "div",
    { class: "materials-scroll" },
    el(
      "table",
      { class: "materials-table" },
      el(
        "thead",
        {},
        el(
          "tr",
          {},
          ...["Name", "Kategorie", "Einheit", "Preis (netto)", "Gültig ab"].map((text, i) =>
            el("th", { scope: "col", class: i === 3 ? "materials-number" : "" }, text),
          ),
        ),
      ),
      tableBody,
    ),
  );

  // --- Material anlegen ---
  const nameInput = el("input", { type: "text", required: "", autocomplete: "off" });
  const categoryInput = el("input", {
    type: "text",
    autocomplete: "off",
    list: "materials-categories",
  });
  const categoryList = el("datalist", { id: "materials-categories" });
  const unitInput = el("input", {
    type: "text",
    required: "",
    autocomplete: "off",
    list: "materials-units",
  });
  const unitList = el("datalist", { id: "materials-units" }, ...UNITS.map((u) => el("option", { value: u })));
  const createButton = el(
    "button",
    { type: "submit", class: "materials-button", disabled: true },
    "Material anlegen",
  );
  const createForm = el(
    "form",
    { class: "materials-form", novalidate: "" },
    el("h2", {}, "Material anlegen"),
    field("Name", nameInput),
    el(
      "div",
      { class: "materials-row" },
      field("Kategorie", categoryInput, "z. B. Bauholz oder Kleinteile"),
      field("Einheit", unitInput),
    ),
    categoryList,
    unitList,
    el("div", { class: "materials-actions" }, createButton),
    message,
  );

  // --- Preis eintragen ---
  const priceMaterial = el("select", { required: "" });
  const priceInput = el("input", {
    type: "text",
    inputmode: "decimal",
    autocomplete: "off",
    required: "",
    placeholder: "z. B. 450,00",
  });
  const priceDate = el("input", { type: "date", required: "", value: today() });
  const priceButton = el(
    "button",
    { type: "submit", class: "materials-button", disabled: true },
    "Preis eintragen",
  );
  const priceForm = el(
    "form",
    { class: "materials-form", novalidate: "" },
    el("h2", {}, "Preis eintragen"),
    field("Material", priceMaterial),
    el(
      "div",
      { class: "materials-row" },
      field("Preis in Euro (netto) je Einheit", priceInput),
      field("Gilt ab", priceDate, "Der Preis gilt, bis ein neuerer beginnt."),
    ),
    el("div", { class: "materials-actions" }, priceButton),
    priceMessage,
  );

  container.append(
    el(
      "section",
      { class: "materials-section" },
      empty,
      tableWrap,
      createForm,
      priceForm,
    ),
  );

  // --- Anzeigen ---

  function showMaterials() {
    empty.hidden = materials.length > 0;
    tableWrap.hidden = materials.length === 0;
    tableBody.replaceChildren(
      ...materials.map((m) =>
        el(
          "tr",
          {},
          el("td", {}, m.name),
          el("td", {}, m.kategorie),
          el("td", {}, m.einheit),
          el("td", { class: "materials-number" }, m.preis === null ? "kein Preis" : formatEuro(m.preis)),
          el("td", {}, m.gueltig_ab === null ? "–" : formatDate(m.gueltig_ab)),
        ),
      ),
    );
    priceMaterial.replaceChildren(
      ...materials.map((m) => el("option", { value: String(m.id) }, `${m.name} (${m.einheit})`)),
    );
    const categories = [...new Set(materials.map((m) => m.kategorie).filter(Boolean))];
    categoryList.replaceChildren(...categories.map((c) => el("option", { value: c })));
    updateButtons();
  }

  // Die Knöpfe sind erst aktiv, wenn die Angaben stimmen.
  function updateButtons() {
    createButton.disabled = !(nameInput.value.trim() && unitInput.value.trim());
    priceButton.disabled = !(priceMaterial.value && toDecimalText(priceInput.value) !== null);
  }

  async function load() {
    try {
      materials = await getJson("/api/materials/items");
      showMaterials();
    } catch (error) {
      message.show(error.message, true);
    }
  }

  // --- Bedienen ---

  for (const input of [nameInput, unitInput, priceInput]) {
    input.addEventListener("input", updateButtons);
  }
  priceMaterial.addEventListener("change", updateButtons);

  createForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    message.clear();
    try {
      await sendJson("POST", "/api/materials/items", {
        name: nameInput.value,
        category: categoryInput.value,
        unit: unitInput.value,
      });
      message.show(`Material „${nameInput.value.trim()}“ angelegt. Als Nächstes den Preis eintragen.`);
      nameInput.value = "";
      await load();
    } catch (error) {
      message.show(error.message, true);
    }
  });

  priceForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    priceMessage.clear();
    try {
      await sendJson("POST", `/api/materials/items/${priceMaterial.value}/prices`, {
        unit_price: toDecimalText(priceInput.value),
        valid_from: priceDate.value,
      });
      priceMessage.show(`Preis ab ${formatDate(priceDate.value)} eingetragen.`);
      priceInput.value = "";
      await load();
    } catch (error) {
      priceMessage.show(error.message, true);
    }
  });

  return load();
}
