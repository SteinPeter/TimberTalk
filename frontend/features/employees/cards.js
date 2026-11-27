// Bausteine für Stunden- und Urlaubskonto (Feature F14), die beide Reiter des Features nutzen:
// „Zeitkonto“ (timeaccount/timeaccount.js – die eigenen Konten) und „Personal“
// (employees/employees.js – alle Mitarbeitenden). Keine Reiter-Datei, nur Funktionen.
// Alles aus der API kommt mit textContent in die Seite.

import { el } from "../../shared/dom.js";

// --- Zahlen und Daten auf Deutsch ---------------------------------------------------

export const number = (value) =>
  Number(value).toLocaleString("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
export const hoursText = (value) => `${number(value)} h`;
// Plus und Minus stehen als Zeichen davor – nicht nur als Farbe.
export const balanceText = (value) => {
  const amount = Number(value);
  if (amount === 0) {
    return "± 0,00 h";
  }
  return `${amount > 0 ? "+" : "−"} ${number(Math.abs(amount))} h`;
};
export const daysText = (count) => `${count} ${Math.abs(count) === 1 ? "Tag" : "Tage"}`;
const dateText = (text) => new Date(`${text}T12:00:00`).toLocaleDateString("de-DE");

// Minus zusätzlich in Akzentfarbe (das Zeichen steht immer dabei).
export function balanceClass(value) {
  return Number(value) < 0 ? "employees-minus" : "";
}

// ‹ 2026 › – onChange(jahr) wird beim Blättern aufgerufen. Gibt { node, show(jahr) } zurück.
export function yearSwitcher(onChange) {
  let year = new Date().getFullYear();
  const label = el("strong", { class: "employees-year", "aria-live": "polite" });
  const go = (step) => {
    year += step;
    label.textContent = String(year);
    onChange(year);
  };
  label.textContent = String(year);
  const node = el(
    "div",
    { class: "employees-toolbar" },
    el("button", { type: "button", class: "button-quiet", "aria-label": "Vorjahr", onclick: () => go(-1) }, "‹"),
    label,
    el("button", { type: "button", class: "button-quiet", "aria-label": "Folgejahr", onclick: () => go(1) }, "›"),
  );
  return { node, year: () => year };
}

function facts(pairs) {
  return el("dl", { class: "employees-facts" }, ...pairs.flatMap(([label, value]) => [el("dt", {}, label), el("dd", {}, value)]));
}

// Die Karte „Stundenkonto“: groß das Plus oder Minus, darunter woraus es sich ergibt.
export function hoursCard(data) {
  const account = data.hours;
  if (!account.until) {
    return el("section", { class: "employees-card" }, el("h3", {}, "Stundenkonto"), el("p", { class: "employees-sub" }, `${data.year} hat noch nicht begonnen.`));
  }
  const amount = Number(account.balance_hours);
  const word = amount > 0 ? "im Plus" : amount < 0 ? "im Minus" : "ausgeglichen";
  const from = data.start_date && data.start_date > `${data.year}-01-01` ? dateText(data.start_date) : `1.1.${data.year}`;
  return el(
    "section",
    { class: "employees-card" },
    el("h3", {}, "Stundenkonto"),
    el("p", { class: `employees-big ${balanceClass(account.balance_hours)}` }, balanceText(account.balance_hours)),
    el("p", { class: "employees-sub" }, word),
    facts([
      ["Gebucht", hoursText(account.worked_hours)],
      ["Soll", hoursText(account.target_hours)],
      ["Diesen Monat gebucht", hoursText(account.worked_month_hours)],
      ["Vereinbart", `${number(data.weekly_hours)} h pro Woche`],
    ]),
    el(
      "p",
      { class: "form-hint" },
      `Gerechnet vom ${from} bis ${dateText(account.until)}. Urlaub, Krankheit, Berufsschule und Feiertage (${data.holiday_region}) zählen als erfüllt.`,
    ),
  );
}

// Die Karte „Urlaub“: groß die übrigen Tage. action: ein Knopf neben der Zahl (im Zeitkonto
// „Urlaub beantragen“), sonst nichts.
export function vacationCard(data, action = null) {
  const v = data.vacation;
  const card = el(
    "section",
    { class: "employees-card" },
    el("h3", {}, `Urlaub ${data.year}`),
    el(
      "div",
      { class: "employees-big-row" },
      el(
        "div",
        {},
        el("p", { class: `employees-big${v.remaining < 0 ? " employees-minus" : ""}` }, daysText(v.remaining)),
        el("p", { class: "employees-sub" }, "noch übrig"),
      ),
      ...(action ? [action] : []),
    ),
    facts([
      ["Anspruch", daysText(v.entitlement)],
      ["Rest aus dem Vorjahr", daysText(v.carryover)],
      ["Genommen", daysText(v.taken)],
      ["Genehmigt, kommt noch", daysText(v.planned)],
      ["Beantragt, offen", daysText(v.requested)],
      ["Krankheitstage", daysText(v.sick_days)],
    ]),
    el("p", { class: "form-hint" }, `Gezählt werden Arbeitstage: Montag bis Freitag ohne Feiertage (${data.holiday_region}).`),
  );
  return card;
}

// Beide Karten nebeneinander (schmal untereinander). vacationAction: Knopf in der Urlaubskarte.
export function cards(data, vacationAction = null) {
  return el("div", { class: "employees-cards" }, hoursCard(data), vacationCard(data, vacationAction));
}
