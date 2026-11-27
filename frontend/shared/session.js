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
  try {
    sessionStorage.removeItem("timbertalk.loggedOut"); // angemeldet: Merker wieder weg
  } catch {
    // nichts zu tun
  }
  return account;
}

// Das eigene Konto, wie es loadAccount() geholt hat (Name, Rolle, Rechte …).
export function currentAccount() {
  return account;
}

// Hat das eigene Konto dieses Recht? Die Namen stehen in backend/…/accounts/permissions.py.
// permission: ein Recht – oder eine Liste, dann genügt eines davon
// (z. B. ["employees.view_all", "employees.manage"]).
export function can(permission) {
  const wanted = Array.isArray(permission) ? permission : [permission];
  return account !== null && wanted.some((p) => account.permissions.includes(p));
}

// Meldet ab und zeigt wieder die Anmeldung. Der Merker sorgt dafür, dass der Demo-Modus einen
// nicht sofort wieder anmeldet – man soll ein anderes Konto wählen können.
export async function logout() {
  try {
    sessionStorage.setItem("timbertalk.loggedOut", "1");
  } catch {
    // Merken geht nicht – dann eben nicht.
  }
  await sendJson("POST", "/api/accounts/logout");
  window.location.reload();
}
