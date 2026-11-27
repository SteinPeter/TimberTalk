// Der Abschnitt „Stunden“ im Reiter „Buchungen“ (Feature F4, Grundversion):
// Abends den Tag bestätigen – was im Kalender stand, ist schon als Vorschlag ausgefüllt
// (Arbeitszeit laut Kalender minus gesetzlicher Pause, ohne Uhrzeit 8 h). Dazu weitere Stunden
// von Hand und die Liste der Woche mit Summe. Wer „hours.view_all“ hat, sieht auch alle anderen.
// Eingetragen in bookings/sections.js.

import { getJson, sendJson } from "../../../shared/api.js";
import { el, field, messageBox } from "../../../shared/dom.js";
import { can, currentAccount } from "../../../shared/session.js";

export const id = "hours";
export const title = "Stunden";
export const permission = "hours.book_own";

const isoDate = (day) => day.toLocaleDateString("sv-SE");
const parseDate = (text) => new Date(`${text}T12:00:00`);
const addDays = (text, days) => {
  const day = parseDate(text);
  day.setDate(day.getDate() + days);
  return isoDate(day);
};
const mondayOf = (text) => addDays(text, -((parseDate(text).getDay() + 6) % 7));
const longDate = (text) =>
  parseDate(text).toLocaleDateString("de-DE", { weekday: "long", day: "numeric", month: "long" });
const shortDate = (text) =>
  parseDate(text).toLocaleDateString("de-DE", { weekday: "short", day: "numeric", month: "numeric" });
const hoursText = (value) => Number(value).toLocaleString("de-DE", { minimumFractionDigits: 0, maximumFractionDigits: 2 });

// „7,5“ oder „7.5“ → „7.5“; keine Zahl → null.
function toDecimalText(input) {
  const text = input.trim().replace(",", ".");
  return /^\d+(\.\d+)?$/.test(text) ? text : null;
}

export function render(container) {
  const viewAll = can("hours.view_all");
  let day = isoDate(new Date());

  // --- Tag wählen ---
  const dayInput = el("input", { type: "date", value: day, "aria-label": "Tag" });
  const dayLabel = el("h2", { class: "hours-day" });
  const nav = el(
    "div",
    { class: "hours-nav" },
    el("button", { type: "button", class: "button-quiet", onclick: () => setDay(addDays(day, -1)) }, "‹ Vortag"),
    dayInput,
    el("button", { type: "button", class: "button-quiet", onclick: () => setDay(isoDate(new Date())) }, "Heute"),
    el("button", { type: "button", class: "button-quiet", onclick: () => setDay(addDays(day, 1)) }, "Folgetag ›"),
  );

  // --- Aus dem Kalender ---
  const suggestionList = el("div", { class: "hours-suggestions" });
  const confirmButton = el("button", { type: "button", class: "button", disabled: true }, "Ausgewählte bestätigen");
  const suggestionMessage = messageBox();
  const fromCalendar = el(
    "section",
    { class: "form" },
    el("h2", {}, "Aus dem Kalender"),
    suggestionList,
    el("div", { class: "form-actions" }, confirmButton),
    suggestionMessage,
  );

  // --- Weitere Stunden von Hand ---
  const projectInput = el("input", { type: "number", min: "1", step: "1", inputmode: "numeric" });
  const titleInput = el("input", { type: "text", autocomplete: "off", placeholder: "z. B. Aufmaß, Werkstatt" });
  const hoursInput = el("input", { type: "text", inputmode: "decimal", autocomplete: "off", placeholder: "z. B. 2,5" });
  const noteInput = el("textarea", { rows: "1" });
  const bookButton = el("button", { type: "submit", class: "button", disabled: true }, "Stunden buchen");
  const manualMessage = messageBox();
  // Von Hand bucht man selten – das Formular erscheint erst nach einem Klick.
  const manualToggle = el(
    "button",
    { type: "button", class: "button-quiet hours-toggle", "aria-expanded": "false" },
    "+ Weitere Stunden buchen",
  );
  const manualForm = el(
    "form",
    { class: "form", novalidate: "", hidden: true },
    el("h2", {}, "Weitere Stunden"),
    el("div", { class: "form-row" }, field("Projektnummer", projectInput), field("Wofür", titleInput)),
    el("div", { class: "form-row" }, field("Stunden", hoursInput), field("Notiz", noteInput)),
    el(
      "div",
      { class: "form-actions" },
      bookButton,
      el("button", { type: "button", class: "button-quiet", onclick: () => showManual(false) }, "Abbrechen"),
    ),
  );

  function showManual(visible) {
    manualForm.hidden = !visible;
    manualToggle.hidden = visible;
    manualToggle.setAttribute("aria-expanded", String(visible));
    if (visible) {
      manualMessage.clear();
      projectInput.focus();
    }
  }
  manualToggle.addEventListener("click", () => showManual(true));

  // --- Woche ---
  const whoSelect = el(
    "select",
    { "aria-label": "Wessen Stunden", hidden: !viewAll },
    el("option", { value: "me" }, "Nur meine"),
    el("option", { value: "all" }, "Alle Mitarbeitenden"),
  );
  const weekTitle = el("h2", {});
  const weekBody = el("tbody");
  const weekFoot = el("tfoot");
  const weekEmpty = el("p", { class: "empty" }, "In dieser Woche ist noch nichts gebucht.");
  const weekTable = el(
    "div",
    { class: "table-scroll" },
    el("table", { class: "table" }, el("thead", {}, el("tr", {})), weekBody, weekFoot),
  );
  const weekMessage = messageBox();

  container.append(
    el("section", { class: "hours-section" }, nav, dayLabel, fromCalendar, manualToggle, manualForm, manualMessage),
    el("section", { class: "hours-week" }, el("div", { class: "hours-week-head" }, weekTitle, whoSelect), weekMessage, weekEmpty, weekTable),
  );

  // --- Anzeigen ---

  function showSuggestions(list) {
    if (list.length === 0) {
      suggestionList.replaceChildren(el("p", { class: "planning-free" }, "Für diesen Tag steht nichts im Kalender."));
      confirmButton.hidden = true;
      return;
    }
    confirmButton.hidden = false;
    suggestionList.replaceChildren(
      ...list.map((item) => {
        const box = el("input", { type: "checkbox", checked: !item.booked, disabled: item.booked, "aria-label": `${item.title} bestätigen` });
        const project = el("input", { type: "number", min: "1", step: "1", inputmode: "numeric", value: item.project_id ?? "", "aria-label": `Projektnummer für ${item.title}` });
        const hours = el("input", { type: "text", inputmode: "decimal", value: hoursText(item.hours), "aria-label": `Stunden für ${item.title}` });
        const row = el(
          "div",
          { class: `hours-suggestion${item.booked ? " hours-booked" : ""}` },
          el("label", { class: "form-check" }, box, el("span", {}, el("strong", {}, item.title), el("small", {}, item.booked ? `${item.time} · schon gebucht` : item.time))),
          el("label", { class: "hours-small-field" }, el("span", {}, "Projekt"), project),
          el("label", { class: "hours-small-field" }, el("span", {}, "Stunden"), hours),
        );
        row.read = () => ({
          chosen: box.checked && !item.booked,
          data: {
            work_date: day,
            hours: toDecimalText(hours.value),
            project_id: project.value ? Number(project.value) : null,
            title: item.title,
            calendar_entry_id: item.calendar_entry_id,
          },
        });
        for (const input of [box, hours]) {
          input.addEventListener("input", updateConfirm);
        }
        return row;
      }),
    );
    updateConfirm();
  }

  function chosenSuggestions() {
    return [...suggestionList.querySelectorAll(".hours-suggestion")].map((row) => row.read()).filter((r) => r.chosen);
  }

  function updateConfirm() {
    const chosen = chosenSuggestions();
    confirmButton.disabled = chosen.length === 0 || chosen.some((r) => r.data.hours === null);
  }

  function showWeek(list, monday) {
    const showPerson = viewAll && whoSelect.value === "all";
    weekTitle.textContent = `Gebucht in der Woche ab ${shortDate(monday)}`;
    weekEmpty.hidden = list.length > 0;
    weekTable.hidden = list.length === 0;
    const headers = ["Tag", ...(showPerson ? ["Person"] : []), "Wofür", "Stunden", ""];
    weekTable.querySelector("thead tr").replaceChildren(
      ...headers.map((text) => el("th", { scope: "col", class: text === "Stunden" ? "hours-number" : "" }, text)),
    );
    weekBody.replaceChildren(
      ...list.map((entry) =>
        el(
          "tr",
          {},
          el("td", {}, shortDate(entry.work_date)),
          ...(showPerson ? [el("td", {}, entry.person)] : []),
          el(
            "td",
            {},
            entry.title || "–",
            el("small", { class: "audit-area" }, [entry.project_id ? `Projekt ${entry.project_id}` : "", entry.note].filter(Boolean).join(" · ")),
          ),
          el("td", { class: "hours-number" }, `${hoursText(entry.hours)} h`),
          el(
            "td",
            {},
            el("button", { type: "button", class: "button-quiet", "aria-label": `Buchung ${entry.title} vom ${shortDate(entry.work_date)} löschen`, onclick: () => remove(entry) }, "Löschen"),
          ),
        ),
      ),
    );
    // Summe je Person (bei „Alle“) oder eine Summe.
    const sums = new Map();
    for (const entry of list) {
      sums.set(entry.person, (sums.get(entry.person) ?? 0) + Number(entry.hours));
    }
    const span = headers.length - 2;
    weekFoot.replaceChildren(
      ...[...sums].map(([person, sum]) =>
        el(
          "tr",
          {},
          el("th", { scope: "row", colspan: String(span) }, showPerson ? `Summe ${person}` : "Summe"),
          el("td", { class: "hours-number" }, `${hoursText(sum)} h`),
          el("td", {}),
        ),
      ),
    );
  }

  // --- Laden ---

  async function loadDay() {
    dayLabel.textContent = longDate(day);
    suggestionMessage.clear();
    try {
      showSuggestions(await getJson(`/api/hours/suggestions?day=${day}`));
    } catch (error) {
      suggestionMessage.show(error.message, true);
    }
    await loadWeek();
  }

  async function loadWeek() {
    const monday = mondayOf(day);
    const params = new URLSearchParams({ start: monday, end: addDays(monday, 6) });
    // Ohne „hours.view_all“ liefert die API ohnehin nur die eigenen; mit dem Recht wählt man.
    if (viewAll && whoSelect.value !== "all") {
      params.set("account_id", currentAccount().id);
    }
    weekMessage.clear();
    try {
      showWeek(await getJson(`/api/hours?${params}`), monday);
    } catch (error) {
      weekMessage.show(error.message, true);
    }
  }

  function setDay(value) {
    day = value;
    dayInput.value = value;
    loadDay();
  }

  async function remove(entry) {
    if (!window.confirm(`Buchung „${entry.title || "Stunden"}“ vom ${shortDate(entry.work_date)} löschen?`)) {
      return;
    }
    try {
      await sendJson("DELETE", `/api/hours/${entry.id}`);
      await loadDay();
      weekMessage.show(`Gelöscht: ${hoursText(entry.hours)} h ${entry.title}.`);
    } catch (error) {
      weekMessage.show(error.message, true);
    }
  }

  // --- Bedienen ---

  dayInput.addEventListener("change", () => dayInput.value && setDay(dayInput.value));
  whoSelect.addEventListener("change", loadWeek);

  confirmButton.addEventListener("click", async () => {
    suggestionMessage.clear();
    const items = chosenSuggestions().map((r) => r.data);
    try {
      const booked = await sendJson("POST", "/api/hours/confirm-day", { items });
      const total = booked.reduce((sum, entry) => sum + Number(entry.hours), 0);
      await loadDay(); // erst neu laden – das leert die Meldungen –, dann melden
      suggestionMessage.show(`Bestätigt: ${hoursText(total)} h am ${shortDate(day)}.`);
    } catch (error) {
      suggestionMessage.show(error.message, true);
    }
  });

  const updateBook = () => {
    bookButton.disabled = toDecimalText(hoursInput.value) === null || !(projectInput.value || titleInput.value.trim());
  };
  for (const input of [projectInput, titleInput, hoursInput]) {
    input.addEventListener("input", updateBook);
  }

  manualForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    manualMessage.clear();
    try {
      const booked = await sendJson("POST", "/api/hours", {
        work_date: day,
        hours: toDecimalText(hoursInput.value),
        project_id: projectInput.value ? Number(projectInput.value) : null,
        title: titleInput.value,
        note: noteInput.value,
      });
      manualForm.reset();
      updateBook();
      showManual(false);
      manualMessage.show(`Gebucht: ${hoursText(booked.hours)} h ${booked.title || `Projekt ${booked.project_id}`}.`);
      await loadWeek();
    } catch (error) {
      manualMessage.show(error.message, true);
    }
  });

  return loadDay();
}
