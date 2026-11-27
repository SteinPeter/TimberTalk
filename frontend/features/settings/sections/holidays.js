// Der Abschnitt „Feiertage“ im Reiter „Einstellungen“ (Feature F15):
// Zeigt, nach welchem Bundesland TimberTalk die Feiertage rechnet – erkannt an der Postleitzahl
// in der Firmenadresse (Abschnitt „Firma und Bank“) – und die Feiertage des Jahres. Wer die
// Firmendaten ändern darf („finance.edit“), kann das Bundesland auch selbst festlegen, etwa wenn
// der Betrieb an einer Landesgrenze liegt. Eingetragen in settings/sections.js.

import { getJson, sendJson } from "../../../shared/api.js";
import { el, field, messageBox } from "../../../shared/dom.js";
import { can } from "../../../shared/session.js";

export const id = "holidays";
export const title = "Feiertage";

const AUTO = "";

// Woher das Bundesland kommt, als Satz.
function sourceText(info) {
  if (info.source === "manual") {
    const detected = info.detected ? ` (die Postleitzahl ${info.postcode} ergäbe ${info.detectedName})` : "";
    return `Von Hand festgelegt${detected}.`;
  }
  if (info.source === "address") {
    return `Erkannt an der Postleitzahl ${info.postcode} in der Firmenadresse.`;
  }
  return "In der Firmenadresse steht keine Postleitzahl – es gelten nur die bundesweiten Feiertage. Bitte unter „Firma und Bank“ die Adresse mit Postleitzahl eintragen.";
}

export async function render(container) {
  const year = new Date().getFullYear();
  const [states, initial] = await Promise.all([getJson("/api/holidays/states"), getJson("/api/holidays/state")]);
  const names = Object.fromEntries(states.map((s) => [s.state, s.name]));
  const heading = el("p", { class: "holidays-state" });
  const source = el("p", { class: "form-hint" });
  const list = el("ul", { class: "holidays-list" });
  const message = messageBox();
  const select = el(
    "select",
    { disabled: !can("finance.edit") },
    el("option", { value: AUTO }, "Automatisch aus der Firmenadresse"),
    ...states.map((s) => el("option", { value: s.state }, s.name)),
  );

  async function show(info) {
    heading.replaceChildren("Bundesland: ", el("strong", {}, info.name));
    source.textContent = sourceText({ ...info, detectedName: names[info.detected] ?? "" });
    select.value = info.source === "manual" ? info.state : AUTO;
    const days = await getJson(`/api/holidays?start=${year}-01-01&end=${year}-12-31`);
    list.replaceChildren(
      ...days.map((holiday) =>
        el(
          "li",
          {},
          el("span", {}, new Date(`${holiday.day}T12:00:00`).toLocaleDateString("de-DE", { weekday: "short", day: "numeric", month: "long" })),
          el("span", {}, holiday.name),
        ),
      ),
    );
  }

  select.addEventListener("change", async () => {
    message.clear();
    try {
      const info = await sendJson("PUT", "/api/holidays/state", { state: select.value || null });
      await show(info);
      message.show(`Feiertage gelten jetzt für: ${info.name}.`);
    } catch (error) {
      message.show(error.message, true);
    }
  });

  container.append(
    el(
      "div",
      { class: "form" },
      heading,
      source,
      field("Bundesland festlegen", select, can("finance.edit") ? "Nur nötig, wenn die Postleitzahl das falsche Bundesland ergibt." : "Ändern darf, wer die Firmendaten ändern darf."),
      message,
      el("h3", { class: "holidays-year" }, `Feiertage ${year}`),
      list,
      el("p", { class: "form-hint" }, "Feiertage stehen im Kalender und zählen beim Stunden- und Urlaubskonto nicht als Arbeitstag."),
    ),
  );
  await show(initial);
}
