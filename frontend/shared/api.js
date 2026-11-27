// Fragt die API. Alle Reiter holen ihre Daten über diese Datei,
// damit Adresse und Fehlerbehandlung nur an einer Stelle stehen.
//
// Angemeldet ist man über ein Cookie, das der Browser bei jeder Anfrage von selbst mitschickt
// (F10). Antwortet die API mit 401, ist die Anmeldung abgelaufen oder beendet: Dann wird die
// Seite neu geladen und zeigt wieder die Anmeldung. Nur bei der Anmeldung selbst bedeutet 401
// „Passwort falsch“ – dann kommt die Meldung als Fehler zurück.

import { API_BASE } from "../config.js";

const LOGIN_PATH = "/api/accounts/login";

// Holt path (z. B. "/api/health") und gibt die Antwort als Objekt zurück.
// Antwortet die API mit einem Fehler, wird eine Ausnahme mit ihrem deutschen Text geworfen.
export async function getJson(path) {
  const response = await call(`${API_BASE}${path}`);
  return readAnswer(response, path);
}

// Name des Ereignisses, das nach jeder erfolgreichen Änderung auf `window` ausgelöst wird.
// Die Glocke (notifications.js) holt dann ihre Zahl neu – z. B. verschwindet „bitte Urlaubsantrag
// entscheiden“ sofort, wenn der Antrag entschieden ist.
export const CHANGED_EVENT = "timbertalk:changed";

// Schickt Daten an die API (POST, PUT, DELETE) und gibt die Antwort als Objekt zurück.
export async function sendJson(method, path, body) {
  const options = { method };
  if (body !== undefined) {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(body);
  }
  const response = await call(`${API_BASE}${path}`, options);
  const answer = await readAnswer(response, path);
  window.dispatchEvent(new Event(CHANGED_EVENT));
  return answer;
}

// fetch() wirft ohne Verbindung nur „Failed to fetch“ (Englisch, ohne Hinweis). Daraus wird
// ein deutscher Satz, der sagt, was los ist und was hilft.
async function call(url, options) {
  try {
    return await fetch(url, options);
  } catch {
    throw new Error(
      "Der Server ist nicht erreichbar. Läuft TimberTalk noch (uv run timbertalk)? " +
        "Dann die Seite neu laden.",
    );
  }
}

async function readAnswer(response, path) {
  if (response.status === 401 && path !== LOGIN_PATH) {
    window.location.reload();
  }
  if (!response.ok) {
    throw new Error(await errorText(response));
  }
  return response.status === 204 ? null : response.json();
}

// Der deutsche Fehlertext aus der Antwort ("detail") – oder der Statuscode, wenn keiner da ist.
async function errorText(response) {
  try {
    const data = await response.json();
    if (typeof data.detail === "string") {
      return data.detail;
    }
    if (Array.isArray(data.detail)) {
      return "Bitte die Eingaben prüfen.";
    }
  } catch {
    // Keine lesbare Fehlermeldung: es bleibt beim Statuscode.
  }
  return `Antwort ${response.status}`;
}
