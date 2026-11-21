// Der Reiter "Kunden": Kunden mit Adressen und Projekten.
// Noch leer – das Feature, das diesen Bereich füllt, arbeitet nur in dieser Datei.

export const id = "customers";
export const title = "Kunden";

export function render(panel) {
  panel.innerHTML = `
    <h1>Kunden</h1>
    <p class="empty">Hier erscheinen bald Ihre Kunden mit Adressen und Projekten. Dieser Bereich ist noch im Aufbau.</p>
  `;
}
