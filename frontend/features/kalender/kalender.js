// Der Reiter "Kalender": Termine und Einsätze auf den Baustellen.
// Noch leer – das Feature, das diesen Bereich füllt, arbeitet nur in dieser Datei.

export const id = "kalender";
export const title = "Kalender";

export function render(panel) {
  panel.innerHTML = `
    <h1>Kalender</h1>
    <p class="empty">Hier erscheinen bald Termine und Einsätze auf den Baustellen. Dieser Bereich ist noch im Aufbau.</p>
  `;
}
