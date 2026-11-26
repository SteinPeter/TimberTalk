// Widget „Systemstatus“ für das Dashboard (Feature F12): ob Backend und Datenbank antworten.
// Bauplan eines Widgets: siehe frontend/features/start/start.js.

import { getJson } from "../../../shared/api.js";
import { el } from "../../../shared/dom.js";

export const title = "Systemstatus";
export const order = 90; // eher unten
export const defaultOn = true;

export async function render(container) {
  const backend = el("dd", {}, "wird geprüft …");
  const database = el("dd", {}, "wird geprüft …");
  container.append(
    el(
      "dl",
      { class: "status" },
      el("dt", {}, "Programm"),
      el("dd", {}, "TimberTalk läuft"),
      el("dt", {}, "Backend"),
      backend,
      el("dt", {}, "Datenbank"),
      database,
    ),
  );
  try {
    const health = await getJson("/api/health");
    backend.textContent = health.status === "ok" ? "antwortet" : health.status;
    database.textContent = health.database === "ok" ? "antwortet" : "antwortet nicht";
  } catch (error) {
    backend.textContent = `nicht erreichbar (${error.message})`;
    database.textContent = "unbekannt";
  }
}
