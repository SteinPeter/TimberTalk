// Der Reiter "Einstellungen": eigenes Konto, Stammdaten und Preise des Betriebs.
// Jedes Feature bringt hier seinen Abschnitt als eigene Datei unter sections/ mit und trägt ihn
// in sections.js ein. Diese Datei wird dafür nicht geändert (F0e).

import { renderSections } from "../../shared/sections.js";
import { SECTIONS } from "./sections.js";

export const id = "settings";
export const title = "Einstellungen";

export function render(panel) {
  panel.innerHTML = `
    <h1>Einstellungen</h1>
    <p class="hint">Ihr Konto, die Stammdaten und Preise des Betriebs.</p>
  `;
  renderSections(panel, {
    tabId: id,
    sections: SECTIONS,
    layout: "sidebar",
    emptyText:
      "Hier stellen Sie bald Ihren Betrieb ein, etwa Name, Adresse und Preise. Dieser Bereich ist noch im Aufbau.",
  });
}
