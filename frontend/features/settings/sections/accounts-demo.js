// Der Abschnitt „Demo-Modus“ im Reiter „Einstellungen“ (Feature F10):
// Ist er an, meldet TimberTalk beim Öffnen ohne Passwort als das gewählte Konto an, und die
// Anmeldeseite bietet Knöpfe „Anmelden als …“ für jedes Konto. Niemand muss dann zuerst ein eigenes
// Passwort festlegen. Nur für Vorführungen und Entwicklung – dann kommt jeder ins Programm, der die
// Seite erreicht. Nur mit dem Recht „accounts.manage“. Eingetragen in settings/sections.js.

import { getJson, sendJson } from "../../../shared/api.js";
import { el, field, messageBox } from "../../../shared/dom.js";

export const id = "accounts-demo";
export const title = "Demo-Modus";
export const permission = "accounts.manage";

export async function render(container) {
  const [settings, accounts] = await Promise.all([getJson("/api/accounts/demo-mode"), getJson("/api/accounts")]);
  const enabled = el("input", { type: "checkbox", checked: settings.enabled });
  const accountSelect = el(
    "select",
    {},
    ...accounts.filter((a) => a.active).map((a) => el("option", { value: String(a.id) }, `${a.display_name} (${a.role_label})`)),
  );
  if (settings.account_id) {
    accountSelect.value = String(settings.account_id);
  }
  const message = messageBox();
  const warning = el(
    "p",
    { class: "accounts-demo-warning" },
    "Achtung: Im Demo-Modus kommt jeder ohne Passwort ins Programm, der die Seite erreicht – auch an " +
      "Preise und Konten, je nach gewähltem Konto. Nur für Vorführungen, nie im echten Betrieb.",
  );

  async function save() {
    message.clear();
    try {
      const saved = await sendJson("PUT", "/api/accounts/demo-mode", {
        enabled: enabled.checked,
        account_id: Number(accountSelect.value) || null,
      });
      message.show(saved.enabled ? "Demo-Modus ist an." : "Demo-Modus ist aus – Anmeldung wieder mit Passwort.");
    } catch (error) {
      enabled.checked = !enabled.checked;
      message.show(error.message, true);
    }
  }
  enabled.addEventListener("change", save);
  accountSelect.addEventListener("change", save);

  container.append(
    el(
      "div",
      { class: "form" },
      el("label", { class: "form-check" }, enabled, el("span", {}, "Demo-Modus: ohne Passwort anmelden")),
      field("Automatisch anmelden als", accountSelect, "Nach „Abmelden“ kann man auf der Anmeldeseite jedes andere Konto wählen."),
      warning,
      message,
    ),
  );
}
