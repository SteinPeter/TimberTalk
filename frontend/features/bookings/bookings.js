// Der Reiter "Buchungen": gebuchte Stunden, Materialien und Fahrten.
// Jedes Feature bringt hier seinen Abschnitt als eigene Datei unter sections/ mit und trägt ihn
// in sections.js ein. Diese Datei wird dafür nicht geändert (F0e).

import { renderSections } from "../../shared/sections.js";
import { SECTIONS } from "./sections.js";

export const id = "bookings";
export const title = "Buchungen";

export function render(panel) {
  panel.innerHTML = `
    <h1>Buchungen</h1>
    <p class="hint">Stunden, Material und Fahrten auf Projekte buchen.</p>
  `;
  renderSections(panel, {
    tabId: id,
    sections: SECTIONS,
    layout: "tabs",
    emptyText:
      "Hier erscheinen bald die gebuchten Stunden, Materialien und Fahrten. Dieser Bereich ist noch im Aufbau.",
  });
}
