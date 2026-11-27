// Der Reiter "Personal" (Feature F14): Stunden und Urlaub aller Mitarbeitenden.
//
// Nur mit dem Recht „employees.view_all“ oder „employees.manage“ (Voreinstellung: Chef und
// Verwaltung; anderen Rollen oder einzelnen Konten gibt man es unter „Rollen und Rechte“). Zuerst eine
// Tabelle aller Mitarbeitenden; ein Klick auf einen Namen öffnet dessen Stunden- und Urlaubskonto.
// Wer „employees.manage“ hat (Chef, Verwaltung), trägt dort Wochenstunden, Urlaubsanspruch,
// Eintritt und den Rest aus dem Vorjahr ein. Die eigenen Konten zeigt jedem der Reiter
// „Zeitkonto“ (timeaccount/timeaccount.js). Die Karten stehen in cards.js.
// Alles aus der API kommt mit textContent in die Seite.

import { getJson, sendJson } from "../../shared/api.js";
import { el, field, messageBox } from "../../shared/dom.js";
import { can } from "../../shared/session.js";
import { balanceClass, balanceText, cards, hoursText, number, yearSwitcher } from "./cards.js";

export const id = "employees";
export const title = "Personal";
export const permission = ["employees.view_all", "employees.manage"]; // eines genügt

const OVERVIEW = "overview";

export async function render(panel) {
  const mayManage = can("employees.manage");
  let view = OVERVIEW;

  const message = messageBox();
  const content = el("div", { class: "employees-content" });
  const years = yearSwitcher(() => show());
  panel.replaceChildren(
    el("h1", {}, "Personal"),
    el("p", { class: "hint" }, "Stunden und Urlaub aller Mitarbeitenden."),
    years.node,
    message,
    content,
  );

  function open(target) {
    view = target;
    message.clear();
    show();
  }

  async function show() {
    const year = years.year();
    try {
      if (view === OVERVIEW) {
        content.replaceChildren(overviewTable(await getJson(`/api/employees/overview?year=${year}`)));
      } else {
        content.replaceChildren(personView(await getJson(`/api/employees/${view}?year=${year}`)));
      }
    } catch (error) {
      content.replaceChildren();
      message.show(error.message, true);
    }
  }

  // --- Übersicht ---

  function overviewTable(rows) {
    if (rows.length === 0) {
      return el("p", { class: "empty" }, "Es gibt noch keine Konten.");
    }
    // Wird es eng, fallen zuerst Std./Woche und Soll weg, dann Gebucht und Krank (shared/tables.js).
    const head = ["Name", "Std./Woche", "Gebucht", "Soll", "Stundenkonto", "Urlaub übrig", "Krank"];
    const priority = { "Std./Woche": "3", Soll: "3", Gebucht: "2", Krank: "2" };
    return el(
      "div",
      { class: "table-scroll" },
      el(
        "table",
        { class: "table employees-table" },
        el(
          "thead",
          {},
          el("tr", {}, ...head.map((text, i) => el("th", { scope: "col", class: i ? "employees-number" : "", ...(priority[text] ? { "data-priority": priority[text] } : {}) }, text))),
        ),
        el(
          "tbody",
          {},
          ...rows.map((row) =>
            el(
              "tr",
              {},
              el(
                "th",
                { scope: "row" },
                el("button", { type: "button", class: "employees-name", onclick: () => open(row.account_id) }, row.display_name),
              ),
              el("td", { class: "employees-number" }, number(row.weekly_hours)),
              el("td", { class: "employees-number" }, hoursText(row.hours.worked_hours)),
              el("td", { class: "employees-number" }, hoursText(row.hours.target_hours)),
              el("td", { class: `employees-number ${balanceClass(row.hours.balance_hours)}` }, balanceText(row.hours.balance_hours)),
              el("td", { class: "employees-number" }, `${row.vacation.remaining} von ${row.vacation.entitlement + row.vacation.carryover}`),
              el("td", { class: "employees-number" }, String(row.vacation.sick_days)),
            ),
          ),
        ),
      ),
    );
  }

  // --- Konten einer Person ---

  function personView(data) {
    return el(
      "div",
      {},
      el("button", { type: "button", class: "button-quiet employees-back", onclick: () => open(OVERVIEW) }, "‹ Alle Mitarbeiter"),
      el("h2", {}, data.display_name),
      cards(data),
      ...(mayManage ? [contractForm(data)] : []),
    );
  }

  // --- Vereinbarung ändern (nur mit „employees.manage“) ---

  function contractForm(data) {
    const weekly = el("input", { type: "number", min: "0", max: "60", step: "0.5", inputmode: "decimal", value: data.weekly_hours, required: "" });
    const vacation = el("input", { type: "number", min: "0", max: "60", step: "1", inputmode: "numeric", value: String(data.vacation_days), required: "" });
    const start = el("input", { type: "date", value: data.start_date ?? "" });
    const carryover = el("input", { type: "number", min: "0", max: "60", step: "1", inputmode: "numeric", value: String(data.vacation.carryover) });
    const formMessage = messageBox();
    const form = el(
      "form",
      { class: "form employees-form", novalidate: "" },
      el("h3", {}, "Vereinbarung"),
      el("div", { class: "form-row" }, field("Wochenstunden", weekly, "Verteilt auf Montag bis Freitag."), field("Urlaubstage im Jahr", vacation)),
      el("div", { class: "form-row" }, field("Eintritt", start, "Freiwillig. Davor zählt kein Soll."), field(`Rest aus ${data.year - 1}`, carryover, `Wird in ${data.year} dazugezählt.`)),
      formMessage,
      el("div", { class: "form-actions" }, el("button", { type: "submit", class: "button" }, "Speichern")),
    );
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      formMessage.clear();
      try {
        await sendJson("PUT", `/api/employees/${data.account_id}/contract`, {
          weekly_hours: weekly.value,
          vacation_days: Number(vacation.value),
          start_date: start.value || null,
        });
        await sendJson("PUT", `/api/employees/${data.account_id}/carryover/${data.year}`, { days: Number(carryover.value) || 0 });
        await show();
        message.show(`Gespeichert: Vereinbarung von ${data.display_name}.`);
      } catch (error) {
        formMessage.show(error.message, true);
      }
    });
    return form;
  }

  await show();
}
