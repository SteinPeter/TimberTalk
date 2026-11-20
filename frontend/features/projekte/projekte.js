// Der Reiter "Projekte": Projekte mit Stand und Kosten.
// Noch leer – das Feature, das diesen Bereich füllt, arbeitet nur in dieser Datei.

export const id = "projekte";
export const title = "Projekte";

export function render(panel) {
  panel.innerHTML = `
    <h1>Projekte</h1>
    <p class="empty">Hier erscheinen bald Ihre Projekte mit Stand und Kosten. Dieser Bereich ist noch im Aufbau.</p>
  `;
}
