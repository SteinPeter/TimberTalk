// Urlaubsanträge im Reiter „Kalender“ (Feature F8). planning.js baut diesen Teil unter der Woche ein.
//
// - Mit „calendar.request_absence“ (und ohne Genehmigungsrecht): Formular „Urlaub beantragen“ und
//   die eigenen Anträge.
// - Mit „calendar.approve_absence“: alle Anträge; offene mit Hinweisen, ob die Person in der Zeit
//   schon eingeplant ist, und den Knöpfen „Genehmigen“ und „Ablehnen“ (wahlweise mit Grund).
// Genehmigter Urlaub steht danach als Termin im Kalender; onChange() lädt die Woche neu.

import { getJson, sendJson } from "../../shared/api.js";
import { el, field, messageBox } from "../../shared/dom.js";
import { can } from "../../shared/session.js";

const day = (text) =>
  new Date(`${text}T12:00:00`).toLocaleDateString("de-DE", { weekday: "short", day: "numeric", month: "numeric" });

export function renderRequests(container, { onChange }) {
  const mayRequest = can("calendar.request_absence");
  const mayApprove = can("calendar.approve_absence");
  if (!mayRequest && !mayApprove) {
    return;
  }
  const message = messageBox();
  const list = el("ul", { class: "planning-requests" });
  const section = el("section", { class: "planning-extra" }, el("h2", {}, mayApprove ? "Urlaubsanträge" : "Urlaub"));

  // Wer genehmigt (in der Regel der Chef), trägt eigenen Urlaub direkt im Kalender ein.
  if (mayRequest && !mayApprove) {
    const startInput = el("input", { type: "date", required: "" });
    const endInput = el("input", { type: "date", required: "" });
    const noteInput = el("input", { type: "text", autocomplete: "off", placeholder: "freiwillig" });
    const button = el("button", { type: "submit", class: "button", disabled: true }, "Urlaub beantragen");
    const form = el(
      "form",
      { class: "form", novalidate: "" },
      el("div", { class: "form-row" }, field("Erster Urlaubstag", startInput), field("Letzter Urlaubstag", endInput)),
      field("Notiz", noteInput),
      el("div", { class: "form-actions" }, button),
    );
    const check = () => {
      if (startInput.value && (!endInput.value || endInput.value < startInput.value)) {
        endInput.value = startInput.value;
      }
      button.disabled = !(startInput.value && endInput.value);
    };
    startInput.addEventListener("change", check);
    endInput.addEventListener("change", check);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      message.clear();
      try {
        await sendJson("POST", "/api/planning/requests", {
          start_date: startInput.value,
          end_date: endInput.value,
          note: noteInput.value,
        });
        form.reset();
        button.disabled = true;
        message.show("Beantragt. Sie bekommen eine Mitteilung, sobald entschieden ist.");
        await load();
      } catch (error) {
        message.show(error.message, true);
      }
    });
    section.append(form);
  }
  section.append(message, list);
  container.append(section);

  function item(request) {
    const range =
      request.start_date === request.end_date
        ? day(request.start_date)
        : `${day(request.start_date)} – ${day(request.end_date)} (${request.days} Tage)`;
    const head = mayApprove ? `${request.person.display_name}: ${range}` : range;
    const li = el(
      "li",
      { class: `planning-request planning-request-${request.status}` },
      el("div", { class: "planning-request-head" }, el("strong", {}, head), el("span", { class: "planning-request-status" }, request.status_label)),
    );
    if (request.note) {
      li.append(el("p", {}, request.note));
    }
    if (request.decision_note) {
      li.append(el("p", { class: "form-hint" }, `Begründung: ${request.decision_note}`));
    }
    for (const conflict of request.conflicts) {
      li.append(el("p", { class: "planning-conflict" }, `Achtung: ${conflict}`));
    }
    if (request.status !== "pending") {
      return li;
    }
    if (mayApprove) {
      const reason = el("input", { type: "text", autocomplete: "off", placeholder: "Grund (freiwillig)", "aria-label": `Grund zum Antrag von ${request.person.display_name}` });
      const decide = async (approve) => {
        message.clear();
        try {
          const result = await sendJson("POST", `/api/planning/requests/${request.id}/${approve ? "approve" : "reject"}`, { note: reason.value });
          const done = approve ? `Genehmigt: Urlaub von ${request.person.display_name}.` : `Abgelehnt: Urlaub von ${request.person.display_name}.`;
          message.show(result.warnings.length ? `${done} Achtung: ${result.warnings.join(" ")}` : done);
          await load();
          if (approve) {
            await onChange();
          }
        } catch (error) {
          message.show(error.message, true);
        }
      };
      li.append(
        el(
          "div",
          { class: "planning-request-actions" },
          reason,
          el("button", { type: "button", class: "button", onclick: () => decide(true) }, "Genehmigen"),
          el("button", { type: "button", class: "button-quiet", onclick: () => decide(false) }, "Ablehnen"),
        ),
      );
    } else {
      li.append(
        el(
          "div",
          { class: "planning-request-actions" },
          el(
            "button",
            {
              type: "button",
              class: "button-quiet",
              onclick: async () => {
                await sendJson("DELETE", `/api/planning/requests/${request.id}`);
                message.show("Antrag zurückgezogen.");
                await load();
              },
            },
            "Zurückziehen",
          ),
        ),
      );
    }
    return li;
  }

  async function load() {
    try {
      const requests = await getJson("/api/planning/requests");
      list.replaceChildren(
        ...(requests.length ? requests.map(item) : [el("li", { class: "planning-free" }, "Keine Anträge.")]),
      );
    } catch (error) {
      message.show(error.message, true);
    }
  }

  return load();
}
