// Der Abschnitt „Stammdaten der Abrechnung“ im Reiter „Einstellungen“ (Feature F5):
// Firma, Logo, Bankverbindung, Fahrtkosten je km, Umsatzsteuer und die Stundensätze.
// Diese Angaben werden einmal eingetragen und später für Kosten und Rechnungen benutzt.
// Der Reiter selbst (settings.js) ruft nur renderCompany() auf.

import { getJson } from "../../shared/api.js";
import {
  el,
  field,
  formatEuro,
  messageBox,
  sendJson,
  toDecimalText,
} from "../bookings/materials-helpers.js";

const MAX_LOGO_BYTES = 350 * 1024;

// Zeigt eine Dezimalzahl aus der API in einem Eingabefeld: „0.5500“ → „0,55“.
function toInputText(value) {
  const text = String(value);
  const trimmed = text.includes(".") ? text.replace(/0+$/, "").replace(/\.$/, "") : text;
  return trimmed.replace(".", ",");
}

// Baut den Abschnitt in `container` auf.
export function renderCompany(container) {
  let logo = null;

  const message = messageBox(); // gehört zum Formular „Firma und Bank“
  const rateMessage = messageBox(); // gehört zum Formular „Stundensätze“

  // --- Firma und Bank ---
  const companyName = el("input", { type: "text", autocomplete: "organization" });
  const address = el("textarea", { rows: "3", autocomplete: "street-address" });
  const bankName = el("input", { type: "text", autocomplete: "off" });
  const iban = el("input", { type: "text", autocomplete: "off", spellcheck: "false" });
  const bic = el("input", { type: "text", autocomplete: "off", spellcheck: "false" });
  const travelRate = el("input", { type: "text", inputmode: "decimal", autocomplete: "off" });
  const vatRate = el("input", { type: "text", inputmode: "decimal", autocomplete: "off" });

  // --- Logo ---
  const logoPreview = el("img", { class: "materials-logo", alt: "Logo des Betriebs", hidden: true });
  const logoInput = el("input", { type: "file", accept: "image/png,image/jpeg,image/svg+xml" });
  const logoRemove = el("button", { type: "button", class: "materials-button-quiet", hidden: true }, "Logo entfernen");

  const saveButton = el("button", { type: "submit", class: "materials-button" }, "Stammdaten speichern");
  const form = el(
    "form",
    { class: "materials-form", novalidate: "" },
    el("h3", {}, "Firma und Bank"),
    field("Firma", companyName),
    field("Adresse", address),
    el("div", { class: "materials-field" }, el("span", {}, "Logo"), logoPreview, logoInput, logoRemove),
    field("Name der Bank", bankName),
    el("div", { class: "materials-row" }, field("IBAN", iban), field("BIC", bic)),
    el("h3", {}, "Preise und Steuer"),
    el(
      "div",
      { class: "materials-row" },
      field("Fahrtkosten je km (Euro, netto)", travelRate, "z. B. 0,55"),
      field("Umsatzsteuer in Prozent", vatRate, "z. B. 19"),
    ),
    el("div", { class: "materials-actions" }, saveButton),
    message,
  );

  // --- Stundensätze ---
  const rateBody = el("tbody");
  const rateEmpty = el("p", { class: "empty" }, "Noch kein Stundensatz eingetragen.");
  const rateWrap = el(
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
          el("th", { scope: "col" }, "Bezeichnung"),
          el("th", { scope: "col", class: "materials-number" }, "Satz je Stunde (netto)"),
          el("th", { scope: "col" }, "Aktion"),
        ),
      ),
      rateBody,
    ),
  );
  const rateName = el("input", { type: "text", autocomplete: "off", required: "" });
  const rateValue = el("input", {
    type: "text",
    inputmode: "decimal",
    autocomplete: "off",
    required: "",
    placeholder: "z. B. 55",
  });
  const rateButton = el("button", { type: "submit", class: "materials-button", disabled: true }, "Stundensatz speichern");
  const rateForm = el(
    "form",
    { class: "materials-form", novalidate: "" },
    el("h3", {}, "Stundensätze"),
    rateEmpty,
    rateWrap,
    el(
      "div",
      { class: "materials-row" },
      field("Bezeichnung", rateName, "z. B. Geselle. Gibt es den Namen schon, wird sein Satz geändert."),
      field("Satz in Euro (netto) je Stunde", rateValue),
    ),
    el("div", { class: "materials-actions" }, rateButton),
    rateMessage,
  );

  container.append(
    el(
      "section",
      { class: "materials-section" },
      el("h2", {}, "Stammdaten der Abrechnung"),
      form,
      rateForm,
    ),
  );

  // --- Anzeigen ---

  function showLogo() {
    logoPreview.hidden = !logo;
    logoRemove.hidden = !logo;
    if (logo) {
      logoPreview.src = logo; // Bild als „data:image/…“; das ist kein HTML
    } else {
      logoPreview.removeAttribute("src");
    }
  }

  function showCompany(company) {
    companyName.value = company.company_name;
    address.value = company.address;
    bankName.value = company.bank_name;
    iban.value = company.iban;
    bic.value = company.bic;
    travelRate.value = company.travel_rate_per_km === "0" ? "" : toInputText(company.travel_rate_per_km);
    vatRate.value = toInputText(company.vat_rate);
    logo = company.logo;
    showLogo();
  }

  function showRates(rates) {
    rateEmpty.hidden = rates.length > 0;
    rateWrap.hidden = rates.length === 0;
    rateBody.replaceChildren(
      ...rates.map((rate) =>
        el(
          "tr",
          {},
          el("td", {}, rate.name),
          el("td", { class: "materials-number" }, formatEuro(rate.rate)),
          el(
            "td",
            {},
            el(
              "button",
              {
                type: "button",
                class: "materials-button-quiet",
                "aria-label": `Stundensatz ${rate.name} löschen`,
                onclick: () => removeRate(rate),
              },
              "Löschen",
            ),
          ),
        ),
      ),
    );
  }

  async function load() {
    try {
      const [company, rates] = await Promise.all([
        getJson("/api/materials/company"),
        getJson("/api/materials/hourly-rates"),
      ]);
      showCompany(company);
      showRates(rates);
    } catch (error) {
      message.show(error.message, true);
    }
  }

  async function removeRate(rate) {
    rateMessage.clear();
    try {
      await sendJson("DELETE", `/api/materials/hourly-rates/${rate.id}`);
      rateMessage.show(`Stundensatz „${rate.name}“ gelöscht.`);
      showRates(await getJson("/api/materials/hourly-rates"));
    } catch (error) {
      rateMessage.show(error.message, true);
    }
  }

  // --- Bedienen ---

  logoInput.addEventListener("change", () => {
    const file = logoInput.files[0];
    if (!file) {
      return;
    }
    if (file.size > MAX_LOGO_BYTES) {
      message.show("Das Logo ist zu groß (höchstens 350 KB).", true);
      logoInput.value = "";
      return;
    }
    const reader = new FileReader();
    reader.addEventListener("load", () => {
      logo = reader.result;
      showLogo();
      message.show("Logo übernommen. Mit „Stammdaten speichern“ wird es gespeichert.");
    });
    reader.readAsDataURL(file);
  });

  logoRemove.addEventListener("click", () => {
    logo = null;
    logoInput.value = "";
    showLogo();
  });

  for (const input of [rateName, rateValue]) {
    input.addEventListener("input", () => {
      rateButton.disabled = !(rateName.value.trim() && toDecimalText(rateValue.value) !== null);
    });
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    message.clear();
    const travel = travelRate.value.trim() === "" ? "0" : toDecimalText(travelRate.value);
    const vat = toDecimalText(vatRate.value);
    if (travel === null || vat === null) {
      message.show("Fahrtkosten und Umsatzsteuer müssen Zahlen sein, z. B. 0,55 und 19.", true);
      return;
    }
    try {
      const saved = await sendJson("PUT", "/api/materials/company", {
        company_name: companyName.value,
        address: address.value,
        logo,
        bank_name: bankName.value,
        iban: iban.value,
        bic: bic.value,
        travel_rate_per_km: travel,
        vat_rate: vat,
      });
      showCompany(saved);
      message.show("Stammdaten gespeichert.");
    } catch (error) {
      message.show(error.message, true);
    }
  });

  rateForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    rateMessage.clear();
    try {
      await sendJson("PUT", "/api/materials/hourly-rates", {
        name: rateName.value,
        rate: toDecimalText(rateValue.value),
      });
      rateMessage.show(`Stundensatz „${rateName.value.trim()}“ gespeichert.`);
      rateName.value = "";
      rateValue.value = "";
      rateButton.disabled = true;
      showRates(await getJson("/api/materials/hourly-rates"));
    } catch (error) {
      rateMessage.show(error.message, true);
    }
  });

  return load();
}
