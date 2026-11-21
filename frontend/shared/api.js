// Fragt die API. Alle Reiter holen ihre Daten über diese Datei,
// damit Adresse und Fehlerbehandlung nur an einer Stelle stehen.

import { API_BASE } from "../config.js";

// Holt path (z. B. "/api/health") und gibt die Antwort als Objekt zurück.
// Antwortet die API mit einem Fehler, wird eine Ausnahme mit dem Statuscode geworfen.
export async function getJson(path) {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`Antwort ${response.status}`);
  }
  return response.json();
}
