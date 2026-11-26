// Widget „Meine nächsten Termine“ für das Dashboard (Feature F8/F12): die eigenen Termine von
// heute an für sieben Tage. Bauplan eines Widgets: siehe frontend/features/start/start.js.

import { getJson } from "../../../shared/api.js";
import { el } from "../../../shared/dom.js";
import { currentAccount } from "../../../shared/session.js";

export const title = "Meine nächsten Termine";
export const order = 20;
export const defaultOn = true;

const iso = (day) => day.toLocaleDateString("sv-SE");
const label = (text) =>
  new Date(`${text}T12:00:00`).toLocaleDateString("de-DE", { weekday: "short", day: "numeric", month: "numeric" });

export async function render(container) {
  const start = new Date();
  const end = new Date();
  end.setDate(end.getDate() + 6);
  const params = new URLSearchParams({ start: iso(start), end: iso(end), account_id: currentAccount().id });
  const entries = await getJson(`/api/planning/entries?${params}`);
  if (entries.length === 0) {
    container.append(el("p", { class: "planning-free" }, "In den nächsten sieben Tagen ist nichts eingeplant."));
    return;
  }
  container.append(
    el(
      "ul",
      { class: "dashboard-list" },
      ...entries.map((entry) => {
        const days = entry.start_date === entry.end_date ? label(entry.start_date) : `${label(entry.start_date)} – ${label(entry.end_date)}`;
        const time = entry.start_time ? ` · ${entry.start_time.slice(0, 5)}–${entry.end_time.slice(0, 5)}` : "";
        const details = [entry.location, ...entry.people.filter((p) => p.id !== currentAccount().id).map((p) => p.display_name)]
          .filter(Boolean)
          .join(" · ");
        return el(
          "li",
          {},
          el("strong", {}, entry.title),
          el("small", {}, `${days}${time}`),
          ...(details ? [el("small", {}, details)] : []),
        );
      }),
    ),
    el("p", {}, el("a", { href: "#planning" }, "Zum Kalender")),
  );
}
