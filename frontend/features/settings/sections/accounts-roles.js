// Der Abschnitt „Rollen und Rechte“ im Reiter „Einstellungen“ (Feature F10):
// eine Tabelle mit Häkchen – Zeilen sind Rechte, Spalten sind Rollen. Ein Klick speichert sofort.
// Die Rechte stehen nach Funktionsbereichen gruppiert (Kalender; Zeitkonto, Urlaub und Personal;
// Stunden …), je Bereich eine Kopfzeile. Die Bereiche legt permissions.py (AREAS) fest.
// Jeder Bereich ist zu Beginn zugeklappt; ein Klick auf seine Kopfzeile klappt ihn auf. Welche
// Bereiche offen sind, bleibt beim Speichern eines Häkchens erhalten.
// Nur mit dem Recht „accounts.manage“ sichtbar. Eingetragen in settings/sections.js.

import { getJson, sendJson } from "../../../shared/api.js";
import { el, messageBox } from "../../../shared/dom.js";

export const id = "accounts-roles";
export const title = "Rollen und Rechte";
export const permission = "accounts.manage";

export function render(container) {
  const message = messageBox();
  const open = new Set(); // aufgeklappte Bereiche
  const wrap = el("div", { class: "table-scroll" });

  container.append(
    el(
      "p",
      { class: "form-hint accounts-intro" },
      "Legt fest, was jede Rolle sehen und tun darf. Ein Häkchen gilt sofort – auch für alle, " +
        "die gerade angemeldet sind. Ausnahmen für einzelne Personen: Benutzerkonten → Bearbeiten. " +
        "Konten verwalten kann der Admin immer.",
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
    const row = (perm) =>
      el(
        "tr",
        {},
        el("th", { scope: "row", class: "accounts-permission" }, perm.label),
        ...matrix.roles.map((role) => {
          const box = el("input", {
            type: "checkbox",
            checked: role.permissions.includes(perm.permission),
            // Nicht abwählbar: z. B. „Konten verwalten“ beim Admin.
            disabled: !role.editable || role.locked.includes(perm.permission),
            "aria-label": `${role.label}: ${perm.label}`,
          });
          box.addEventListener("change", () => save(role, perm, box));
          return el("td", { class: "accounts-check" }, box);
        }),
      );
    // Je Funktionsbereich ein eigener Tabellenteil (für Bildschirmleser „rowgroup“). Die
    // Kopfzeile ist ein Knopf zum Auf- und Zuklappen; aria-expanded sagt, ob er offen ist.
    const areas = [...new Set(matrix.permissions.map((perm) => perm.area))];
    const groups = areas.map((area) => {
      const perms = matrix.permissions.filter((perm) => perm.area === area);
      const rows = perms.map(row);
      const toggle = el("button", { type: "button", class: "accounts-area-toggle" });
      const show = () => {
        const isOpen = open.has(area);
        toggle.setAttribute("aria-expanded", String(isOpen));
        toggle.replaceChildren(
          el("span", { class: "accounts-area-arrow", "aria-hidden": "true" }, isOpen ? "▾" : "▸"),
          area,
          el("span", { class: "accounts-area-count" }, `${perms.length} ${perms.length === 1 ? "Recht" : "Rechte"}`),
        );
        rows.forEach((tr) => {
          tr.hidden = !isOpen;
        });
      };
      toggle.addEventListener("click", () => {
        open.has(area) ? open.delete(area) : open.add(area);
        show();
      });
      show();
      return el(
        "tbody",
        {},
        el("tr", { class: "accounts-area" }, el("th", { scope: "rowgroup", colspan: String(matrix.roles.length + 1) }, toggle)),
        ...rows,
      );
    });
    wrap.replaceChildren(el("table", { class: "table accounts-roles" }, el("thead", {}, head), ...groups));
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
