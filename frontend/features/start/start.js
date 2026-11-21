// Der Reiter "Start": Übersicht mit dem Zustand von Backend und Datenbank.

import { getJson } from "../../shared/api.js";

export const id = "start";
export const title = "Start";

// Füllt den Bereich und fragt danach /api/health, ob Backend und Datenbank antworten.
export async function render(panel) {
  panel.innerHTML = `
    <h1>Übersicht</h1>
    <p class="hint">Betriebssoftware für Zimmereien.</p>

    <dl class="status">
      <dt>Programm</dt>
      <dd>TimberTalk läuft</dd>
      <dt>Backend</dt>
      <dd data-status="backend">wird geprüft …</dd>
      <dt>Datenbank</dt>
      <dd data-status="database">wird geprüft …</dd>
    </dl>
  `;

  const backendStatus = panel.querySelector('[data-status="backend"]');
  const databaseStatus = panel.querySelector('[data-status="database"]');

  try {
    const health = await getJson("/api/health");
    backendStatus.textContent = health.status === "ok" ? "antwortet" : health.status;
    databaseStatus.textContent = health.database === "ok" ? "antwortet" : "antwortet nicht";
  } catch (error) {
    backendStatus.textContent = `nicht erreichbar (${error.message})`;
    databaseStatus.textContent = "unbekannt";
  }
}
