// Der Reiter "Buchungen": gebuchte Stunden, Materialien und Fahrten.
// Noch leer – das Feature, das diesen Bereich füllt, arbeitet nur in dieser Datei.

export const id = "bookings";
export const title = "Buchungen";

export function render(panel) {
  panel.innerHTML = `
    <h1>Buchungen</h1>
    <p class="empty">Hier erscheinen bald die gebuchten Stunden, Materialien und Fahrten. Dieser Bereich ist noch im Aufbau.</p>
  `;
}
