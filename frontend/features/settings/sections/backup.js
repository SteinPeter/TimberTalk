// Der Abschnitt „Export und Import“ im Reiter „Einstellungen“ (Feature backup):
// Alle Einstellungen des Betriebs – Firmendaten, Stundensätze, Materialstamm mit Preisen,
// Fahrzeuge und Maschinen – mit einem Klick als Datei sichern und mit einem Klick wieder
// einlesen, z. B. auf einem neuen Rechner. Der Import ergänzt nur und löscht nichts.
// Nur mit dem Recht „finance.edit“ (in der Datei stehen Preise und die Bankverbindung).
// Eingetragen in settings/sections.js.

import { getJson, sendJson } from "../../../shared/api.js";
import { el, messageBox } from "../../../shared/dom.js";

export const id = "backup";
export const title = "Export und Import";
export const permission = "finance.edit";

// Was in einer Datei steckt, als kurzer Satz – für die Rückfrage vor dem Import.
function contents(data) {
  const parts = [];
  if (data.company) {
    parts.push(`Firmendaten${data.company.company_name ? ` von „${data.company.company_name}“` : ""}`);
  }
  parts.push(
    `${data.hourly_rates?.length ?? 0} Stundensätze`,
    `${data.materials?.length ?? 0} Materialien`,
    `${data.resources?.length ?? 0} Fahrzeuge und Maschinen`,
  );
  return parts.join(", ");
}

export async function render(container) {
  const message = messageBox();
  const picker = el("input", { type: "file", accept: "application/json,.json", hidden: true });

  async function exportAll() {
    message.clear();
    try {
      const data = await getJson("/api/backup/settings");
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const link = el("a", {
        href: URL.createObjectURL(blob),
        download: `timbertalk-einstellungen-${new Date().toLocaleDateString("sv-SE")}.json`,
      });
      link.click();
      URL.revokeObjectURL(link.href);
      message.show(`Exportiert: ${contents(data)}.`);
    } catch (error) {
      message.show(error.message, true);
    }
  }

  async function importFile(file) {
    message.clear();
    let data;
    try {
      data = JSON.parse(await file.text());
    } catch {
      message.show("Die Datei lässt sich nicht lesen. Bitte eine exportierte .json-Datei wählen.", true);
      return;
    }
    if (!window.confirm(`Aus „${file.name}“ übernehmen: ${contents(data)}?\n\nFirmendaten werden ersetzt. Alles andere wird nur ergänzt – nichts wird gelöscht.`)) {
      return;
    }
    try {
      const result = await sendJson("POST", "/api/backup/settings", data);
      const done = [
        result.company ? "Firmendaten übernommen" : "",
        `${result.hourly_rates} Stundensätze`,
        `${result.materials_new} neue Materialien`,
        `${result.prices_new} neue Preise`,
        `${result.resources_new} neue und ${result.resources_changed} geänderte Fahrzeuge/Maschinen`,
      ].filter(Boolean);
      message.show(`Importiert: ${done.join(", ")}.`);
    } catch (error) {
      message.show(error.message, true);
    }
  }

  picker.addEventListener("change", () => {
    const [file] = picker.files;
    picker.value = ""; // dieselbe Datei lässt sich danach noch einmal wählen
    if (file) {
      importFile(file);
    }
  });

  container.append(
    el(
      "div",
      { class: "form" },
      el(
        "p",
        { class: "form-hint" },
        "Sichert Firmendaten, Stundensätze, Materialstamm mit Preisen sowie Fahrzeuge und Maschinen " +
          "in einer Datei. Konten und Passwörter gehören nicht dazu.",
      ),
      el(
        "div",
        { class: "form-actions" },
        el("button", { type: "button", class: "button", onclick: exportAll }, "Alles exportieren"),
        el("button", { type: "button", class: "button-quiet", onclick: () => picker.click() }, "Importieren …"),
      ),
      picker,
      message,
    ),
  );
}
