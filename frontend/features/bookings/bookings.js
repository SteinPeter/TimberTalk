// Der Reiter "Buchungen": gebuchte Stunden, Materialien und Fahrten.
// Jedes Feature, das hier etwas zeigt, baut seinen Abschnitt in einer eigenen Datei in diesem
// Ordner und wird unten mit einer Zeile aufgerufen.

import { renderMaterialBooking } from "./materials-booking.js";

export const id = "bookings";
export const title = "Buchungen";

export async function render(panel) {
  panel.innerHTML = `
    <h1>Buchungen</h1>
    <p class="hint">Material und Fahrten auf ein Projekt buchen und die Kosten ansehen.</p>
  `;
  await renderMaterialBooking(panel);
}
