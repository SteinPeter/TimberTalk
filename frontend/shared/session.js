// Wer ist angemeldet, und was darf er? (F10)
// app.js lädt das eigene Konto einmal beim Start mit loadAccount(). Danach fragt jeder Reiter
// mit can("finance.view") usw., ob er etwas zeigen soll. Die eigentliche Prüfung macht immer
// das Backend – hier geht es nur darum, nichts anzuzeigen, was ohnehin abgelehnt würde.

import { API_BASE } from "../config.js";
import { sendJson } from "./api.js";

let account = null;

// Holt das eigene Konto. Gibt null zurück, wenn niemand angemeldet ist.
export async function loadAccount() {
  const response = await fetch(`${API_BASE}/api/accounts/me`);
  if (response.status === 401) {
    account = null;
    return null;
  }
  if (!response.ok) {
    throw new Error(`Antwort ${response.status}`);
  }
  account = await response.json();
  return account;
}

// Das eigene Konto, wie es loadAccount() geholt hat (Name, Rolle, Rechte …).
export function currentAccount() {
  return account;
}

// Hat das eigene Konto dieses Recht? Die Namen stehen in backend/…/accounts/permissions.py.
export function can(permission) {
  return account !== null && account.permissions.includes(permission);
}

// Meldet ab und zeigt wieder die Anmeldung.
export async function logout() {
  await sendJson("POST", "/api/accounts/logout");
  window.location.reload();
}
