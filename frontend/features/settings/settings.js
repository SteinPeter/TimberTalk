// Der Reiter "Einstellungen": Name, Adresse und Preise des Betriebs.
// Noch leer – das Feature, das diesen Bereich füllt, arbeitet nur in dieser Datei.

export const id = "settings";
export const title = "Einstellungen";

export function render(panel) {
  panel.innerHTML = `
    <h1>Einstellungen</h1>
    <p class="empty">Hier stellen Sie bald Ihren Betrieb ein, etwa Name, Adresse und Preise. Dieser Bereich ist noch im Aufbau.</p>
  `;
}
