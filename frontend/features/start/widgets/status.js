// Widget „Systemstatus“ für das Dashboard (Feature F12): ob Backend und Datenbank antworten.
// Es erscheint nur, wenn etwas nicht stimmt – läuft alles, braucht man es nicht zu sehen.
// Bauplan eines Widgets: siehe frontend/features/start/start.js.

import { getJson } from "../../../shared/api.js";
import { el } from "../../../shared/dom.js";

export const title = "Systemstatus";
export const order = 90; // eher unten
export const defaultOn = true;
export const showsWhen = "wenn etwas nicht läuft";

export async function render(container) {
  let backend;
  let database;
  try {
    const health = await getJson("/api/health");
    if (health.status === "ok" && health.database === "ok") {
      return false; // alles in Ordnung: keine Karte
    }
    backend = health.status === "ok" ? "antwortet" : health.status;
    database = health.database === "ok" ? "antwortet" : "antwortet nicht";
  } catch (error) {
    backend = `nicht erreichbar (${error.message})`;
    database = "unbekannt";
  }
  container.append(
    el(
      "dl",
      { class: "status" },
      el("dt", {}, "Backend"),
      el("dd", {}, backend),
      el("dt", {}, "Datenbank"),
      el("dd", {}, database),
    ),
  );
}
