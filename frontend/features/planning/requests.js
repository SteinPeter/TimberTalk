// Darstellung von Urlaubsanträgen (Feature F8) für das Dashboard-Widget „Offene Urlaubsanträge“
// (widgets/absence-requests.js), in dem der Chef entscheidet: range() und card().
// Beantragt wird im Reiter „Zeitkonto“ (frontend/features/timeaccount/absence.js, F14).

import { el } from "../../shared/dom.js";

const day = (text) =>
  new Date(`${text}T12:00:00`).toLocaleDateString("de-DE", { weekday: "short", day: "numeric", month: "numeric" });

export function range(request) {
  return request.start_date === request.end_date
    ? day(request.start_date)
    : `${day(request.start_date)} – ${day(request.end_date)} (${request.days} Tage)`;
}

// Ein Antrag als Karte; extra = Knöpfe darunter (Zurückziehen bzw. Genehmigen/Ablehnen).
export function card(request, title, ...extra) {
  const li = el(
    "li",
    { class: `planning-request planning-request-${request.status}` },
    el("div", { class: "planning-request-head" }, el("strong", {}, title), el("span", { class: "planning-request-status" }, request.status_label)),
  );
  if (request.note) {
    li.append(el("p", { class: "planning-request-note" }, request.note));
  }
  if (request.decision_note) {
    li.append(el("p", { class: "form-hint" }, `Begründung: ${request.decision_note}`));
  }
  for (const conflict of request.conflicts) {
    li.append(el("p", { class: "planning-conflict" }, `Achtung: ${conflict}`));
  }
  li.append(...extra);
  return li;
}
