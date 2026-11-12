// Holt den Status bei der API und schreibt ihn in die Seite.
// Nur fetch, kein Framework, kein Bauschritt.

import { API_BASE } from "./config.js";

const backendStatus = document.getElementById("backend-status");
const databaseStatus = document.getElementById("database-status");

async function showHealth() {
  try {
    const response = await fetch(`${API_BASE}/api/health`);
    if (!response.ok) {
      throw new Error(`Antwort ${response.status}`);
    }
    const health = await response.json();
    backendStatus.textContent = health.status === "ok" ? "antwortet" : health.status;
    databaseStatus.textContent = health.database === "ok" ? "antwortet" : "antwortet nicht";
  } catch (error) {
    backendStatus.textContent = `nicht erreichbar (${error.message})`;
    databaseStatus.textContent = "unbekannt";
  }
}

showHealth();
