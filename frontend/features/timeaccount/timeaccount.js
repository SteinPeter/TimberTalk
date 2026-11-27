// Der Reiter "Zeitkonto" (Feature F14): die eigenen Konten – wie viele Stunden man im Plus oder
// Minus ist und wie viele Urlaubstage noch übrig sind. Jede Person hat diesen Reiter.
// Wer die Konten anderer sehen und pflegen darf, hat zusätzlich den Reiter „Personal“
// (employees/employees.js). Die Karten selbst stehen in employees/cards.js.
// In der Karte „Urlaub“ steht neben der Zahl der Knopf „Urlaub beantragen“; er öffnet ein Fenster
// mit Live-Anzeige des Resturlaubs. Darunter die eigenen Anträge (beides in absence.js).

import { getJson } from "../../shared/api.js";
import { el, messageBox } from "../../shared/dom.js";
import { can } from "../../shared/session.js";
import { cards, yearSwitcher } from "../employees/cards.js";
import { requestDialog, requestList } from "./absence.js";

export const id = "timeaccount";
export const title = "Zeitkonto";

export async function render(panel) {
  const mayRequest = can("calendar.request_absence") && !can("calendar.approve_absence");
  const message = messageBox();
  const content = el("div", { class: "employees-content" });
  const years = yearSwitcher(show);
  panel.replaceChildren(el("h1", {}, "Zeitkonto"), el("p", { class: "hint" }, "Ihr Stundenkonto und Ihr Urlaub."), years.node, message, content);

  // Nach Beantragen oder Zurückziehen: Meldung zeigen, Karten und Liste neu laden.
  async function changed(text) {
    await show(years.year());
    await requests?.reload();
    message.show(text);
  }
  const dialog = mayRequest ? requestDialog(changed) : null;
  const requests = mayRequest ? requestList(changed) : null;
  if (requests) {
    panel.append(requests.node);
  }

  async function show(year) {
    message.clear();
    try {
      const data = await getJson(`/api/employees/me?year=${year}`);
      const button = dialog ? el("button", { type: "button", class: "button", onclick: () => dialog.open(data) }, "Urlaub beantragen") : null;
      content.replaceChildren(cards(data, button));
    } catch (error) {
      content.replaceChildren();
      message.show(error.message, true);
    }
  }

  await show(years.year());
  await requests?.reload();
}
