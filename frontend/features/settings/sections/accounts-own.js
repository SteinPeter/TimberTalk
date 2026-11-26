// Der Abschnitt „Mein Konto“ im Reiter „Einstellungen“ (Feature F10):
// zeigt das eigene Konto und lässt jeden sein eigenes Passwort ändern.
// Eingetragen ist der Abschnitt in settings/sections.js.

import { el } from "../../../shared/dom.js";
import { passwordForm } from "../../../shared/login.js";
import { currentAccount } from "../../../shared/session.js";

export const id = "accounts-own";
export const title = "Mein Konto";

export function render(container) {
  const me = currentAccount();
  const rows = [
    ["Name", me.display_name],
    ["Anmeldename", me.username],
    ["Personalnummer", me.personnel_number ?? "–"],
    ["Rolle", me.role_label],
  ];
  container.append(
    el("dl", { class: "status" }, ...rows.flatMap(([label, value]) => [
      el("dt", {}, label),
      el("dd", {}, value),
    ])),
    el("h2", { class: "form-title" }, "Passwort ändern"),
    passwordForm({ submitText: "Passwort ändern" }),
  );
}
