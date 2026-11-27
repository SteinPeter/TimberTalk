// Widget „Offene Urlaubsanträge“ für das Dashboard (Feature F8/F12). Nur mit dem Recht
// „calendar.approve_absence“ (Voreinstellung: Chef). Hierhin führt auch die Mitteilung über einen
// neuen Antrag. Genehmigen oder ablehnen geht direkt hier; der Antrag bleibt stehen, bis er
// entschieden ist. Ohne offenen Antrag erscheint die Karte gar nicht.
// Bauplan eines Widgets: siehe frontend/features/start/start.js.

import { getJson, sendJson } from "../../../shared/api.js";
import { el, messageBox } from "../../../shared/dom.js";
import { card, range } from "../requests.js";

export const title = "Offene Urlaubsanträge";
export const permission = "calendar.approve_absence";
export const order = 10;
export const defaultOn = true;
export const showsWhen = "wenn Anträge offen sind";

export async function render(container) {
  const list = el("ul", { class: "planning-requests" });
  const message = messageBox();
  container.append(list, message);

  function item(request) {
    const reason = el("textarea", {
      rows: "1",
      placeholder: "Grund (freiwillig)",
      "aria-label": `Grund zum Antrag von ${request.person.display_name}`,
    });
    const decide = async (approve) => {
      message.clear();
      try {
        const result = await sendJson(
          "POST",
          `/api/planning/requests/${request.id}/${approve ? "approve" : "reject"}`,
          { note: reason.value },
        );
        const done = `${approve ? "Genehmigt" : "Abgelehnt"}: Urlaub von ${request.person.display_name}.`;
        await load();
        message.show(result.warnings.length ? `${done} Achtung: ${result.warnings.join(" ")}` : done);
      } catch (error) {
        message.show(error.message, true);
      }
    };
    return card(
      request,
      `${request.person.display_name}: ${range(request)}`,
      el(
        "div",
        { class: "planning-request-actions" },
        reason,
        el("button", { type: "button", class: "button", onclick: () => decide(true) }, "Genehmigen"),
        el("button", { type: "button", class: "button-quiet", onclick: () => decide(false) }, "Ablehnen"),
      ),
    );
  }

  // Gibt zurück, wie viele Anträge offen sind. Ist der letzte entschieden, bleibt die Karte bis
  // zum nächsten Öffnen des Dashboards stehen – mit der Bestätigung darunter.
  async function load() {
    const pending = (await getJson("/api/planning/requests")).filter((r) => r.status === "pending");
    list.replaceChildren(
      ...(pending.length ? pending.map(item) : [el("li", { class: "planning-free" }, "Keine offenen Anträge.")]),
    );
    return pending.length;
  }

  if ((await load()) === 0) {
    return false; // nichts zu entscheiden: keine Karte
  }
}
