// Widget „Stunden heute“ für das Dashboard (Feature F4/F12): was heute laut Kalender gearbeitet
// wurde und ob es schon gebucht ist. Bestätigt wird im Reiter „Buchungen → Stunden“.
// Bauplan eines Widgets: siehe frontend/features/start/start.js.

import { getJson } from "../../../shared/api.js";
import { el } from "../../../shared/dom.js";

export const title = "Stunden heute";
export const permission = "hours.book_own";
export const order = 30;
export const defaultOn = true;

const hours = (value) => Number(value).toLocaleString("de-DE", { maximumFractionDigits: 2 });

export async function render(container) {
  const today = new Date().toLocaleDateString("sv-SE");
  const suggestions = await getJson(`/api/hours/suggestions?day=${today}`);
  const open = suggestions.filter((item) => !item.booked);
  const link = el(
    "a",
    {
      href: "#bookings",
      onclick: () => {
        try {
          localStorage.setItem("timbertalk.bookings.section", "hours");
        } catch {
          // Merken geht nicht – dann öffnet sich eben der erste Abschnitt.
        }
      },
    },
    open.length ? "Jetzt bestätigen" : "Zu den Stunden",
  );
  if (suggestions.length === 0) {
    container.append(el("p", { class: "planning-free" }, "Heute steht nichts im Kalender."), el("p", {}, link));
    return;
  }
  container.append(
    el(
      "ul",
      { class: "dashboard-list" },
      ...suggestions.map((item) =>
        el("li", {}, el("strong", {}, item.title), el("small", {}, `${item.time} · ${hours(item.hours)} h · ${item.booked ? "gebucht" : "noch offen"}`)),
      ),
    ),
    el("p", {}, link),
  );
}
