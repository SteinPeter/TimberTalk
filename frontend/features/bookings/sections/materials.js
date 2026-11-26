// Der Abschnitt „Material und Fahrten“ im Reiter „Buchungen“ (Feature F5):
// Man wählt ein Projekt, bucht Material und Fahrten darauf und sieht die Gesamtkosten.
// Eingetragen ist der Abschnitt in bookings/sections.js.
// Ohne das Recht „finance.view“ (z. B. Gesellen, F10) bleiben Preise, Beträge und Gesamtkosten
// ausgeblendet; buchen geht trotzdem – den Preis setzt das Backend.

import { getJson } from "../../../shared/api.js";
import { can } from "../../../shared/session.js";
import {
  el,
  field,
  formatDate,
  formatEuro,
  formatNumber,
  messageBox,
  sendJson,
  today,
  toDecimalText,
} from "../materials-helpers.js";

const KIND_LABEL = { material: "Material", travel: "Fahrt" };
const STATUS_LABEL = { confirmed: "Gebucht", draft: "Entwurf" };

export const id = "materials";
export const title = "Material und Fahrten";

// Baut den Abschnitt in `container` auf.
export function render(container) {
  const showPrices = can("finance.view");
  let projectId = null;
  let materials = [];

  const message = messageBox(); // Fehler beim Laden von Projekt und Materialliste
  const materialMessage = messageBox();
  const travelMessage = messageBox();

  // --- Projekt wählen ---
  const projectInput = el("input", { type: "number", min: "1", step: "1", inputmode: "numeric" });
  const projectField = field(
    "Projektnummer",
    projectInput,
    "Die Nummer des Projekts, auf das gebucht wird.",
  );

  // --- Kosten ---
  const costs = el("dl", { class: "materials-costs", hidden: !showPrices });

  // --- Material buchen ---
  const materialSelect = el("select", { required: "" });
  const materialDate = el("input", { type: "date", required: "", value: today() });
  const materialQuantity = el("input", {
    type: "text",
    inputmode: "decimal",
    autocomplete: "off",
    required: "",
    placeholder: "z. B. 2,5",
  });
  const priceHint = el("p", { class: "materials-hint" });
  const materialButton = el(
    "button",
    { type: "submit", class: "materials-button", disabled: true },
    "Material buchen",
  );
  const materialForm = el(
    "form",
    { class: "materials-form", novalidate: "" },
    el("h2", {}, "Material buchen"),
    field("Material", materialSelect),
    el(
      "div",
      { class: "materials-row" },
      field("Datum", materialDate),
      field("Menge", materialQuantity),
    ),
    priceHint,
    el("div", { class: "materials-actions" }, materialButton),
    materialMessage,
  );

  // --- Fahrt buchen ---
  const travelDate = el("input", { type: "date", required: "", value: today() });
  const travelKm = el("input", {
    type: "text",
    inputmode: "decimal",
    autocomplete: "off",
    required: "",
    placeholder: "z. B. 40",
  });
  const travelButton = el(
    "button",
    { type: "submit", class: "materials-button", disabled: true },
    "Fahrt buchen",
  );
  const travelForm = el(
    "form",
    { class: "materials-form", novalidate: "" },
    el("h2", {}, "Fahrt buchen"),
    el(
      "div",
      { class: "materials-row" },
      field("Datum", travelDate),
      field("Strecke in km", travelKm),
    ),
    el("div", { class: "materials-actions" }, travelButton),
    travelMessage,
  );

  // --- Buchungen ---
  const bookingsBody = el("tbody");
  const bookingsEmpty = el("p", { class: "empty" }, "Auf dieses Projekt ist noch nichts gebucht.");
  const bookingsTable = el(
    "table",
    { class: "materials-table" },
    el(
      "thead",
      {},
      el(
        "tr",
        {},
        ...["Datum", "Art", "Beschreibung", "Menge", "Preis", "Betrag", "Status"]
          .map((text, i) =>
            el("th", { scope: "col", class: i >= 3 && i <= 5 ? "materials-number" : "" }, text),
          )
          .filter((_, i) => showPrices || (i !== 4 && i !== 5)),
      ),
    ),
    bookingsBody,
  );
  const bookingsWrap = el("div", { class: "materials-scroll" }, bookingsTable);

  const work = el(
    "div",
    { hidden: true },
    el("h2", { hidden: !showPrices }, "Gesamtkosten"),
    costs,
    materialForm,
    travelForm,
    el("h2", {}, "Buchungen auf dieses Projekt"),
    bookingsEmpty,
    bookingsWrap,
  );

  container.append(
    el(
      "section",
      { class: "materials-section" },
      projectField,
      message,
      work,
    ),
  );

  // --- Anzeigen ---

  function showCosts(data) {
    const rows = [
      ["Material", data.material],
      ["Fahrten", data.travel],
      ["Gesamt (netto)", data.total_net],
    ];
    costs.replaceChildren(
      ...rows.flatMap(([label, value]) => [
        el("dt", {}, label),
        el("dd", {}, formatEuro(value)),
      ]),
    );
  }

  function showBookings(list) {
    bookingsEmpty.hidden = list.length > 0;
    bookingsWrap.hidden = list.length === 0;
    bookingsBody.replaceChildren(
      ...list.map((booking) =>
        el(
          "tr",
          {},
          el("td", {}, formatDate(booking.booking_date)),
          el("td", {}, KIND_LABEL[booking.kind] ?? booking.kind),
          el("td", {}, booking.description),
          el("td", { class: "materials-number" }, `${formatNumber(booking.quantity)} ${booking.unit}`),
          ...(showPrices
            ? [
                el("td", { class: "materials-number" }, formatEuro(booking.unit_price)),
                el("td", { class: "materials-number" }, formatEuro(booking.amount)),
              ]
            : []),
          el("td", {}, STATUS_LABEL[booking.status] ?? booking.status),
        ),
      ),
    );
  }

  function showPriceHint() {
    const material = materials.find((m) => String(m.id) === materialSelect.value);
    if (!material) {
      priceHint.textContent = "Im Materialstamm (Einstellungen) ist noch kein Material angelegt.";
    } else if (!showPrices) {
      priceHint.textContent = "Der Preis wird beim Buchen automatisch übernommen.";
    } else if (material.preis === null) {
      priceHint.textContent =
        "Für dieses Material ist noch kein Preis eingetragen. Das geht unter Einstellungen.";
    } else {
      priceHint.textContent =
        `Preis: ${formatEuro(material.preis)} je ${material.einheit}, ` +
        `gültig ab ${formatDate(material.gueltig_ab)}. Gebucht wird zum Preis des Buchungstags.`;
    }
    updateButtons();
  }

  // Die Knöpfe sind erst aktiv, wenn die Angaben stimmen (prüfen, während man tippt).
  function updateButtons() {
    const material = materials.find((m) => String(m.id) === materialSelect.value);
    const quantityOk = toDecimalText(materialQuantity.value) !== null;
    const priceOk = !showPrices || material?.preis !== null;
    materialButton.disabled = !(material && priceOk && quantityOk);
    travelButton.disabled = toDecimalText(travelKm.value) === null;
  }

  async function loadProject() {
    work.hidden = projectId === null;
    message.clear();
    if (projectId === null) {
      return;
    }
    try {
      const bookings = await getJson(`/api/materials/bookings?project_id=${projectId}`);
      showBookings(bookings);
      if (showPrices) {
        showCosts(await getJson(`/api/materials/projects/${projectId}/costs`));
      }
    } catch (error) {
      message.show(error.message, true);
    }
  }

  async function loadMaterials() {
    try {
      materials = await getJson("/api/materials/items");
    } catch (error) {
      materials = [];
      message.show(error.message, true);
    }
    materialSelect.replaceChildren(
      ...materials.map((m) => el("option", { value: String(m.id) }, `${m.name} (${m.einheit})`)),
    );
    showPriceHint();
  }

  // --- Bedienen ---

  projectInput.addEventListener("change", () => {
    const number = Number.parseInt(projectInput.value, 10);
    projectId = Number.isInteger(number) && number >= 1 ? number : null;
    loadProject();
  });
  materialSelect.addEventListener("change", showPriceHint);
  materialQuantity.addEventListener("input", updateButtons);
  travelKm.addEventListener("input", updateButtons);

  materialForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    materialMessage.clear();
    try {
      await sendJson("POST", "/api/materials/bookings/material", {
        project_id: projectId,
        material_id: Number(materialSelect.value),
        quantity: toDecimalText(materialQuantity.value),
        booking_date: materialDate.value,
      });
      const name = materialSelect.selectedOptions[0].textContent;
      materialMessage.show(`Gebucht: ${materialQuantity.value.trim()} × ${name}.`);
      materialQuantity.value = "";
      updateButtons();
      await loadProject();
    } catch (error) {
      materialMessage.show(error.message, true);
    }
  });

  travelForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    travelMessage.clear();
    try {
      await sendJson("POST", "/api/materials/bookings/travel", {
        project_id: projectId,
        km: toDecimalText(travelKm.value),
        booking_date: travelDate.value,
      });
      travelMessage.show(`Gebucht: Fahrt über ${travelKm.value.trim()} km.`);
      travelKm.value = "";
      updateButtons();
      await loadProject();
    } catch (error) {
      travelMessage.show(error.message, true);
    }
  });

  return loadMaterials();
}
