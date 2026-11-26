// Der Abschnitt „Rollen und Rechte“ im Reiter „Einstellungen“ (Feature F10):
// eine Tabelle mit Häkchen – Zeilen sind Rechte, Spalten sind Rollen. Ein Klick speichert sofort.
// Nur mit dem Recht „accounts.manage“ sichtbar. Eingetragen in settings/sections.js.

import { getJson, sendJson } from "../../../shared/api.js";
import { el, messageBox } from "../../../shared/dom.js";

export const id = "accounts-roles";
export const title = "Rollen und Rechte";
export const permission = "accounts.manage";

export function render(container) {
  const message = messageBox();
  const wrap = el("div", { class: "table-scroll" });

  container.append(
    el(
      "p",
      { class: "form-hint accounts-intro" },
      "Legt fest, was jede Rolle sehen und tun darf. Ein Häkchen gilt sofort – auch für alle, " +
        "die gerade angemeldet sind. Der Admin darf immer alles.",
    ),
    wrap,
    message,
  );

  function showMatrix(matrix) {
    const head = el(
      "tr",
      {},
      el("th", { scope: "col" }, "Recht"),
      ...matrix.roles.map((role) => el("th", { scope: "col", class: "accounts-check" }, role.label)),
    );
    const rows = matrix.permissions.map((perm) =>
      el(
        "tr",
        {},
        el("th", { scope: "row", class: "accounts-permission" }, perm.label),
        ...matrix.roles.map((role) => {
          const box = el("input", {
            type: "checkbox",
            checked: role.permissions.includes(perm.permission),
            disabled: !role.editable,
            "aria-label": `${role.label}: ${perm.label}`,
          });
          box.addEventListener("change", () => save(role, perm, box));
          return el("td", { class: "accounts-check" }, box);
        }),
      ),
    );
    wrap.replaceChildren(el("table", { class: "table" }, el("thead", {}, head), el("tbody", {}, ...rows)));
  }

  async function save(role, perm, box) {
    message.clear();
    try {
      const matrix = await sendJson(
        "PUT",
        `/api/accounts/roles/${role.role}/permissions/${perm.permission}`,
        { allowed: box.checked },
      );
      showMatrix(matrix);
      message.show(
        box.checked
          ? `${role.label}: darf jetzt „${perm.label}“.`
          : `${role.label}: darf „${perm.label}“ nicht mehr.`,
      );
    } catch (error) {
      box.checked = !box.checked;
      message.show(error.message, true);
    }
  }

  return getJson("/api/accounts/roles")
    .then(showMatrix)
    .catch((error) => message.show(error.message, true));
}
