// Urlaubsanträge im Reiter „Kalender“ (Feature F8). Nichts davon steht dauerhaft auf der Seite:
//
// - openOwnRequests(): Fenster „Urlaub beantragen“ mit dem Formular und den eigenen Anträgen.
//   planning.js öffnet es über das Menü „Mehr“ (Recht „calendar.request_absence“).
// - setupApprovals(): Für alle mit „calendar.approve_absence“ (in der Regel der Chef). Gibt es
//   offene Anträge, erscheint ein Knopf „Urlaubsanträge (n)“ und das Fenster öffnet sich beim
//   Laden des Kalenders von selbst. Ohne offene Anträge sieht man davon nichts.
// Genehmigter Urlaub steht danach als Termin im Kalender; onChange() lädt die Woche neu.

import { getJson, sendJson } from "../../shared/api.js";
import { el, field, messageBox } from "../../shared/dom.js";
import { makeDialog } from "./dialog.js";

const day = (text) =>
  new Date(`${text}T12:00:00`).toLocaleDateString("de-DE", { weekday: "short", day: "numeric", month: "numeric" });

function range(request) {
  return request.start_date === request.end_date
    ? day(request.start_date)
    : `${day(request.start_date)} – ${day(request.end_date)} (${request.days} Tage)`;
}

// Ein Antrag als Karte; extra = Knöpfe darunter (Zurückziehen bzw. Genehmigen/Ablehnen).
function card(request, title, ...extra) {
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

// --- Eigener Urlaub ---------------------------------------------------------------------

let ownDialog = null;

export function openOwnRequests() {
  if (!ownDialog) {
    ownDialog = buildOwnDialog();
  }
  ownDialog.open();
}

function buildOwnDialog() {
  const dialog = makeDialog("Urlaub beantragen");
  const message = messageBox();
  const list = el("ul", { class: "planning-requests" });
  const startInput = el("input", { type: "date", required: "" });
  const endInput = el("input", { type: "date", required: "" });
  const noteInput = el("textarea", { rows: "1", placeholder: "freiwillig, z. B. Familienfeier" });
  const button = el("button", { type: "submit", class: "button", disabled: true }, "Beantragen");
  const form = el(
    "form",
    { novalidate: "" },
    el("div", { class: "form-row" }, field("Erster Urlaubstag", startInput), field("Letzter Urlaubstag", endInput)),
    field("Notiz", noteInput),
    el("div", { class: "form-actions" }, button),
  );
  dialog.body.append(form, message, el("h3", { class: "planning-subtitle" }, "Meine Anträge"), list);

  const check = () => {
    if (startInput.value && (!endInput.value || endInput.value < startInput.value)) {
      endInput.value = startInput.value;
    }
    button.disabled = !(startInput.value && endInput.value);
  };
  startInput.addEventListener("change", check);
  endInput.addEventListener("change", check);

  async function load() {
    try {
      const requests = await getJson("/api/planning/requests");
      list.replaceChildren(
        ...(requests.length
          ? requests.map((request) =>
              card(
                request,
                range(request),
                ...(request.status === "pending"
                  ? [
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
                    ]
                  : []),
              ),
            )
          : [el("li", { class: "planning-free" }, "Noch keine Anträge.")]),
      );
    } catch (error) {
      message.show(error.message, true);
    }
  }

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

  const open = dialog.open;
  dialog.open = () => {
    message.clear();
    load();
    open();
    startInput.focus();
  };
  return dialog;
}

// --- Anträge entscheiden (Chef) -----------------------------------------------------------

// Baut den Knopf „Urlaubsanträge (n)“ und das Fenster. slot ist die Stelle in der Kopfleiste
// des Kalenders. Öffnet das Fenster von selbst, wenn beim Laden Anträge offen sind.
// onMessage(text) zeigt eine Meldung auf der Kalenderseite – wenn das Fenster schon zu ist.
export async function setupApprovals(slot, { onChange, onMessage }) {
  const dialog = makeDialog("Offene Urlaubsanträge");
  const message = messageBox();
  const list = el("ul", { class: "planning-requests" });
  dialog.body.append(
    el("p", { class: "form-hint" }, "Genehmigter Urlaub steht danach im Kalender. Die Person bekommt eine Mitteilung."),
    list,
    message,
  );
  const button = el("button", { type: "button", class: "button planning-approvals", hidden: true, onclick: () => dialog.open() });
  slot.append(button);

  async function load() {
    const pending = (await getJson("/api/planning/requests")).filter((request) => request.status === "pending");
    button.hidden = pending.length === 0;
    button.textContent = `Urlaubsanträge (${pending.length})`;
    list.replaceChildren(...pending.map(item));
    return pending.length;
  }

  function item(request) {
    const reason = el("textarea", {
      rows: "1",
      placeholder: "Grund (freiwillig)",
      "aria-label": `Grund zum Antrag von ${request.person.display_name}`,
    });
    const decide = async (approve) => {
      message.clear();
      try {
        const result = await sendJson("POST", `/api/planning/requests/${request.id}/${approve ? "approve" : "reject"}`, {
          note: reason.value,
        });
        const done = `${approve ? "Genehmigt" : "Abgelehnt"}: Urlaub von ${request.person.display_name}.`;
        message.show(result.warnings.length ? `${done} Achtung: ${result.warnings.join(" ")}` : done);
        const left = await load();
        if (approve) {
          await onChange();
        }
        // Alles entschieden und keine Warnung, die man lesen sollte: Fenster schließen.
        if (left === 0 && !result.warnings.length) {
          dialog.close();
          onMessage(done);
        }
      } catch (error) {
        message.show(error.message, true);
      }
    };
    return card(
      request,
      `${request.person.display_name}: ${range(request)}`,
      el(
        "div",
        { class: "planning-request-actions" },
        reason,
        el("button", { type: "button", class: "button", onclick: () => decide(true) }, "Genehmigen"),
        el("button", { type: "button", class: "button-quiet", onclick: () => decide(false) }, "Ablehnen"),
      ),
    );
  }

  try {
    if ((await load()) > 0) {
      dialog.open();
    }
  } catch (error) {
    console.error("Urlaubsanträge konnten nicht geladen werden:", error);
  }
}
