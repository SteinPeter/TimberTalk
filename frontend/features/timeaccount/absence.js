// Urlaub beantragen im Reiter „Zeitkonto“ (Feature F14, Daten aus F8).
//
// requestDialog(onSaved): das Fenster „Urlaub beantragen“. Es öffnet sich über den Knopf in der
// Karte „Urlaub“. Während man den ersten und letzten Tag eingibt, rechnet das Backend
// (GET /api/employees/me/vacation-preview) die Arbeitstage aus, und die große Zahl zeigt live,
// wie viele Urlaubstage danach noch übrig sind. Gespeichert wird über die API des Kalenders
// (POST /api/planning/requests); der Chef bekommt eine Mitteilung und entscheidet auf dem Dashboard.
//
// requestList(onChange): die eigenen Anträge mit Status; offene lassen sich zurückziehen.
//
// Beides nur mit dem Recht „calendar.request_absence“ und ohne „calendar.approve_absence“
// (wer selbst genehmigt, beantragt nicht bei sich selbst) – das prüft timeaccount.js.

import { getJson, sendJson } from "../../shared/api.js";
import { el, field, messageBox } from "../../shared/dom.js";
import { daysText } from "../employees/cards.js";

const day = (text) =>
  new Date(`${text}T12:00:00`).toLocaleDateString("de-DE", { weekday: "short", day: "numeric", month: "numeric", year: "numeric" });
const range = (request) => (request.start_date === request.end_date ? day(request.start_date) : `${day(request.start_date)} – ${day(request.end_date)}`);

// --- Fenster „Urlaub beantragen“ ---------------------------------------------------------

export function requestDialog(onSaved) {
  const startInput = el("input", { type: "date", required: "" });
  const endInput = el("input", { type: "date", required: "" });
  const noteInput = el("textarea", { rows: "1", placeholder: "freiwillig, z. B. Familienfeier" });
  const submit = el("button", { type: "submit", class: "button", disabled: true }, "Beantragen");
  const cancel = el("button", { type: "button", class: "button-quiet" }, "Abbrechen");
  const message = messageBox();

  // Die Live-Anzeige: groß der Resturlaub, darunter woraus er sich ergibt.
  const yearLabel = el("p", { class: "employees-sub" });
  const big = el("p", { class: "employees-big" });
  const detail = el("p", { class: "employees-sub" });
  const live = el("div", { class: "timeaccount-live", "aria-live": "polite" }, yearLabel, big, detail);

  const form = el(
    "form",
    { class: "form planning-form", method: "dialog", novalidate: "" },
    el("h2", { id: "timeaccount-dialog-title" }, "Urlaub beantragen"),
    live,
    el("div", { class: "form-row" }, field("Erster Urlaubstag", startInput), field("Letzter Urlaubstag", endInput)),
    field("Notiz", noteInput),
    el("p", { class: "form-hint" }, "Gezählt werden Arbeitstage: Montag bis Freitag ohne Feiertage. Der Chef entscheidet; Sie bekommen eine Mitteilung."),
    message,
    el("div", { class: "form-actions" }, submit, cancel),
  );
  const node = el("dialog", { class: "timeaccount-dialog", "aria-labelledby": "timeaccount-dialog-title" }, form);
  document.body.append(node);

  let summary = null; // die Konten beim Öffnen: Jahr und Resturlaub
  let asked = 0; // Nummer der letzten Vorschau-Anfrage – ältere Antworten werden verworfen

  function showRemaining(year, before, after = before, workdays = null, otherYear = 0) {
    yearLabel.textContent = `Noch übrig ${year}`;
    big.textContent = daysText(after);
    big.classList.toggle("employees-minus", after < 0);
    if (workdays === null) {
      detail.textContent = "Wählen Sie den ersten und letzten Urlaubstag.";
      return;
    }
    const parts = [`vorher ${daysText(before)}`, `dieser Antrag: ${workdays} ${workdays === 1 ? "Arbeitstag" : "Arbeitstage"}`];
    if (otherYear) {
      parts.push(`davon ${otherYear} im Jahr ${year + 1}`);
    }
    if (after < 0) {
      parts.push("mehr als der Resturlaub");
    }
    detail.textContent = parts.join(" · ");
  }

  async function preview() {
    if (startInput.value && (!endInput.value || endInput.value < startInput.value)) {
      endInput.value = startInput.value;
    }
    submit.disabled = !(startInput.value && endInput.value);
    if (submit.disabled) {
      showRemaining(summary.year, summary.vacation.remaining);
      return;
    }
    const number = ++asked;
    try {
      const params = new URLSearchParams({ start: startInput.value, end: endInput.value });
      const result = await getJson(`/api/employees/me/vacation-preview?${params}`);
      if (number === asked) {
        message.clear();
        showRemaining(result.year, result.remaining_before, result.remaining_after, result.workdays, result.other_year_days);
      }
    } catch (error) {
      if (number === asked) {
        message.show(error.message, true);
      }
    }
  }
  for (const input of [startInput, endInput]) {
    input.addEventListener("input", preview);
    input.addEventListener("change", preview);
  }
  cancel.addEventListener("click", () => node.close());

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    message.clear();
    try {
      await sendJson("POST", "/api/planning/requests", { start_date: startInput.value, end_date: endInput.value, note: noteInput.value });
      node.close();
      await onSaved("Beantragt. Sie bekommen eine Mitteilung, sobald entschieden ist.");
    } catch (error) {
      message.show(error.message, true);
    }
  });

  return {
    // data: die Konten aus GET /api/employees/me (für Jahr und Resturlaub vor dem Antrag).
    open(data) {
      summary = data;
      form.reset();
      submit.disabled = true;
      message.clear();
      showRemaining(data.year, data.vacation.remaining);
      node.showModal();
      startInput.focus();
    },
  };
}

// --- Eigene Anträge ----------------------------------------------------------------------

export function requestList(onChange) {
  const message = messageBox();
  const list = el("ul", { class: "timeaccount-requests" });

  function item(request) {
    const li = el(
      "li",
      { class: `timeaccount-request timeaccount-request-${request.status}` },
      el("div", { class: "timeaccount-request-head" }, el("strong", {}, range(request)), el("span", { class: "timeaccount-request-status" }, request.status_label)),
    );
    if (request.note) {
      li.append(el("p", { class: "timeaccount-request-note" }, request.note));
    }
    if (request.decision_note) {
      li.append(el("p", { class: "form-hint" }, `Begründung: ${request.decision_note}`));
    }
    if (request.status === "pending") {
      li.append(
        el(
          "button",
          {
            type: "button",
            class: "button-quiet",
            onclick: async () => {
              if (!window.confirm(`Antrag für ${range(request)} zurückziehen?`)) {
                return;
              }
              try {
                await sendJson("DELETE", `/api/planning/requests/${request.id}`);
                await onChange("Antrag zurückgezogen.");
              } catch (error) {
                message.show(error.message, true);
              }
            },
          },
          "Zurückziehen",
        ),
      );
    }
    return li;
  }

  async function reload() {
    try {
      const requests = await getJson("/api/planning/requests");
      list.replaceChildren(...(requests.length ? requests.map(item) : [el("li", { class: "employees-sub" }, "Noch keine Anträge.")]));
    } catch (error) {
      message.show(error.message, true);
    }
  }

  const node = el("section", { class: "timeaccount-absence", "aria-labelledby": "timeaccount-absence-title" }, el("h2", { id: "timeaccount-absence-title" }, "Meine Urlaubsanträge"), message, list);
  return { node, reload };
}
