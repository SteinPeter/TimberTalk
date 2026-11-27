// Der Abschnitt „Änderungsprotokoll“ im Reiter „Einstellungen“ (Feature F11):
// wer hat wann was geändert – Preise, Konten, Termine, Buchungen. Nur zum Lesen, nur mit dem
// Recht „audit.view“ (Voreinstellung: Admin). Eingetragen in settings/sections.js.

import { getJson } from "../../../shared/api.js";
import { el, formatDateTime, messageBox } from "../../../shared/dom.js";

export const id = "audit";
export const title = "Änderungsprotokoll";
export const permission = "audit.view";

export function render(container) {
  const areaSelect = el("select", { "aria-label": "Bereich" });
  const message = messageBox();
  const empty = el("p", { class: "empty" }, "Noch keine Änderungen.");
  const tableBody = el("tbody");
  const table = el(
    "div",
    { class: "table-scroll" },
    el(
      "table",
      { class: "table" },
      el("thead", {}, el("tr", {}, ...["Wann", "Wer", "Was", "Angaben"].map((text) => el("th", { scope: "col" }, text)))),
      tableBody,
    ),
  );

  container.append(
    el(
      "div",
      { class: "audit-toolbar" },
      el("p", { class: "form-hint" }, "Die letzten 300 Änderungen, die neuesten oben. Passwörter stehen hier nie."),
      areaSelect,
    ),
    message,
    empty,
    table,
  );

  function show(events) {
    empty.hidden = events.length > 0;
    table.hidden = events.length === 0;
    tableBody.replaceChildren(
      ...events.map((event) =>
        el(
          "tr",
          {},
          el("td", { class: "audit-when" }, formatDateTime(event.created_at)),
          el("td", {}, event.account_name),
          // Was: die Aktion, darunter klein der Bereich und welcher Datensatz.
          el(
            "td",
            {},
            event.action,
            el("small", { class: "audit-area" }, [event.area, event.target].filter(Boolean).join(" · ")),
          ),
          el("td", { class: "audit-details" }, event.details || "–"),
        ),
      ),
    );
  }

  async function load() {
    message.clear();
    try {
      const params = areaSelect.value ? `?area=${encodeURIComponent(areaSelect.value)}` : "";
      show(await getJson(`/api/audit${params}`));
    } catch (error) {
      message.show(error.message, true);
    }
  }

  areaSelect.addEventListener("change", load);

  return getJson("/api/audit/areas")
    .then((areas) => {
      areaSelect.replaceChildren(
        el("option", { value: "" }, "Alle Bereiche"),
        ...areas.map((area) => el("option", { value: area }, area)),
      );
    })
    .then(load)
    .catch((error) => message.show(error.message, true));
}
