// Der Reiter "Einstellungen": Name, Adresse und Preise des Betriebs.
// Jedes Feature, das hier etwas einstellen lässt, baut seinen Abschnitt in einer eigenen Datei in
// diesem Ordner und wird unten mit einer Zeile aufgerufen.

import { renderCompany } from "./materials-company.js";
import { renderMaterialMaster } from "./materials-master.js";

export const id = "settings";
export const title = "Einstellungen";

export async function render(panel) {
  panel.innerHTML = `
    <h1>Einstellungen</h1>
    <p class="hint">Stammdaten der Abrechnung und Materialstamm mit Preisen.</p>
  `;
  await renderCompany(panel);
  await renderMaterialMaster(panel);
}
