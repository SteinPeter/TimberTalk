// Der Reiter "Kalender" (Feature F8): wer ist wann wo – Woche für Woche.
//
// Zwei Ansichten:
// - Plantafel: eine Zeile je Person, eine Spalte je Wochentag. Für die Planung im Büro.
// - Persönlicher Kalender: die Woche einer Person als Liste nach Tagen. Gut lesbar auf dem Handy.
// Mit dem Recht „calendar.dispatch“ trägt man Termine ein (Klick auf + in einer Zelle oder
// „Termin eintragen“) und ändert sie (Klick auf den Termin). Wer „calendar.view_all“ nicht hat,
// sieht nur den eigenen Kalender. Alles aus der API kommt mit textContent in die Seite.

import { getJson, sendJson } from "../../shared/api.js";
import { el, field, messageBox } from "../../shared/dom.js";
import { can, currentAccount } from "../../shared/session.js";

export const id = "planning";
export const title = "Kalender";

const BOARD = "board"; // Wert der Ansicht „Plantafel“; sonst steht dort die Nummer einer Person
const VIEW_KEY = "timbertalk.planning.view";
const DAY_NAMES = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];

// --- Datum ohne Zeitzonen-Ärger: immer als Text JJJJ-MM-TT, gerechnet am Mittag ---------

function isoDate(day) {
  return day.toLocaleDateString("sv-SE");
}

function parseDate(text) {
  return new Date(`${text}T12:00:00`);
}

function addDays(text, days) {
  const day = parseDate(text);
  day.setDate(day.getDate() + days);
  return isoDate(day);
}

function mondayOf(text) {
  const day = parseDate(text);
  return addDays(text, -((day.getDay() + 6) % 7));
}

// Kalenderwoche nach ISO 8601: Die Woche gehört zu dem Jahr, in dem ihr Donnerstag liegt, und
// KW 1 ist die Woche mit dem ersten Donnerstag im Januar.
function weekNumber(monday) {
  const thursday = parseDate(addDays(monday, 3));
  const januaryFirst = new Date(thursday.getFullYear(), 0, 1, 12);
  return 1 + Math.floor((thursday - januaryFirst) / 86400000 / 7);
}

const shortDate = (text) => parseDate(text).toLocaleDateString("de-DE", { day: "numeric", month: "numeric" });
const longDate = (text) =>
  parseDate(text).toLocaleDateString("de-DE", { weekday: "long", day: "numeric", month: "long" });
const shortTime = (text) => (text ? text.slice(0, 5) : "");

export async function render(panel) {
  const me = currentAccount();
  const mayDispatch = can("calendar.dispatch");
  const today = isoDate(new Date());

  let monday = mondayOf(today);
  let people = [];
  let kinds = [];
  let entries = [];
  let view = BOARD;

  // --- Gerüst ---
  const weekLabel = el("p", { class: "planning-week", "aria-live": "polite" });
  const viewSelect = el("select", { "aria-label": "Ansicht" });
  const newButton = el("button", { type: "button", class: "button", hidden: !mayDispatch }, "Termin eintragen");
  const toolbar = el(
    "div",
    { class: "planning-toolbar" },
    el(
      "div",
      { class: "planning-nav" },
      el("button", { type: "button", class: "button-quiet", onclick: () => move(-7) }, "‹ Vorwoche"),
      el("button", { type: "button", class: "button-quiet", onclick: () => goTo(today) }, "Heute"),
      el("button", { type: "button", class: "button-quiet", onclick: () => move(7) }, "Nächste ›"),
    ),
    weekLabel,
    el("div", { class: "planning-actions" }, viewSelect, newButton),
  );
  const message = messageBox();
  const content = el("div", { class: "planning-content" });

  panel.replaceChildren(
    el("h1", {}, "Kalender"),
    el("p", { class: "hint" }, "Wer ist wann wo – Woche für Woche."),
    toolbar,
    message,
    content,
  );

  const dialog = buildDialog();
  panel.append(dialog.node);

  // --- Laden ---

  async function loadWeek() {
    const sunday = addDays(monday, 6);
    weekLabel.textContent = `KW ${weekNumber(monday)} · ${shortDate(monday)}–${parseDate(sunday).toLocaleDateString("de-DE")}`;
    const params = new URLSearchParams({ start: monday, end: sunday });
    if (view !== BOARD) {
      params.set("account_id", view);
    }
    try {
      entries = await getJson(`/api/planning/entries?${params}`);
    } catch (error) {
      entries = [];
      message.show(error.message, true);
    }
    show();
  }

  function move(days) {
    monday = addDays(monday, days);
    loadWeek();
  }

  function goTo(day) {
    monday = mondayOf(day);
    loadWeek();
  }

  function days() {
    return Array.from({ length: 7 }, (_, i) => addDays(monday, i));
  }

  function entriesOn(day, personId) {
    return entries.filter(
      (entry) =>
        entry.start_date <= day &&
        entry.end_date >= day &&
        (personId === undefined || entry.people.some((person) => person.id === personId)),
    );
  }

  // --- Anzeigen ---

  function show() {
    content.replaceChildren(view === BOARD ? board() : personalList(Number(view)));
  }

  // Ein Termin als kleines Kärtchen. Mit Planungsrecht ist es ein Knopf zum Ändern.
  function chip(entry, { withPeople = false } = {}) {
    const time = entry.start_time ? `${shortTime(entry.start_time)}–${shortTime(entry.end_time)}` : "";
    // Heißt der Termin wie seine Art (z. B. „Urlaub“), steht er nur einmal da.
    const parts = [el("span", { class: "planning-chip-title" }, entry.title)];
    if (entry.title !== entry.kind_label) {
      parts.unshift(el("span", { class: "planning-chip-kind" }, entry.kind_label));
    }
    const details = [time, entry.location].filter(Boolean).join(" · ");
    if (details) {
      parts.push(el("span", { class: "planning-chip-detail" }, details));
    }
    if (withPeople) {
      parts.push(el("span", { class: "planning-chip-detail" }, entry.people.map((p) => p.display_name).join(", ")));
    }
    const absent = kinds.find((kind) => kind.kind === entry.kind)?.absence;
    const className = `planning-chip${absent ? " planning-chip-absence" : ""}`;
    if (!mayDispatch) {
      return el("div", { class: className }, ...parts);
    }
    return el(
      "button",
      {
        type: "button",
        class: className,
        "aria-label": `${entry.kind_label}: ${entry.title} ändern`,
        onclick: () => dialog.open(entry),
      },
      ...parts,
    );
  }

  function board() {
    if (people.length === 0) {
      return el("p", { class: "empty" }, "Es gibt noch keine Konten, die man einplanen kann.");
    }
    const head = el(
      "tr",
      {},
      el("th", { scope: "col", class: "planning-person" }, "Person"),
      ...days().map((day, i) =>
        el(
          "th",
          { scope: "col", class: day === today ? "planning-today" : "", "aria-current": day === today ? "date" : "false" },
          `${DAY_NAMES[i]} ${shortDate(day)}`,
        ),
      ),
    );
    const rows = people.map((person) =>
      el(
        "tr",
        {},
        el(
          "th",
          { scope: "row", class: "planning-person" },
          el("button", { type: "button", class: "planning-person-link", onclick: () => setView(String(person.id)) }, person.display_name),
        ),
        ...days().map((day, i) => {
          const cell = el("td", { class: day === today ? "planning-today" : "" }, ...entriesOn(day, person.id).map((entry) => chip(entry)));
          if (mayDispatch) {
            cell.append(
              el(
                "button",
                {
                  type: "button",
                  class: "planning-add",
                  "aria-label": `Termin für ${person.display_name} am ${DAY_NAMES[i]} ${shortDate(day)} eintragen`,
                  onclick: () => dialog.open(null, { day, personId: person.id }),
                },
                "+",
              ),
            );
          }
          return cell;
        }),
      ),
    );
    return el("div", { class: "table-scroll planning-board-wrap" }, el("table", { class: "planning-board" }, el("thead", {}, head), el("tbody", {}, ...rows)));
  }

  function personalList(personId) {
    const person = people.find((p) => p.id === personId);
    const list = el("div", { class: "planning-list" });
    if (person) {
      list.append(el("h2", {}, person.id === me.id ? "Meine Woche" : `Woche von ${person.display_name}`));
    }
    for (const day of days()) {
      const dayEntries = entriesOn(day, personId);
      list.append(
        el(
          "section",
          { class: `planning-day${day === today ? " planning-today" : ""}` },
          el("h3", {}, day === today ? `Heute, ${longDate(day)}` : longDate(day)),
          ...(dayEntries.length
            ? dayEntries.map((entry) => chip(entry, { withPeople: entry.people.length > 1 }))
            : [el("p", { class: "planning-free" }, "Nichts eingeplant.")]),
        ),
      );
    }
    return list;
  }

  function setView(value) {
    view = value;
    viewSelect.value = value;
    try {
      localStorage.setItem(VIEW_KEY, value);
    } catch {
      // Merken geht nicht (z. B. privates Fenster) – dann eben nicht.
    }
    loadWeek();
  }

  function fillViewSelect() {
    const options = [];
    if (people.length > 1) {
      options.push(el("option", { value: BOARD }, "Plantafel – alle"));
    }
    for (const person of people) {
      const label = person.id === me.id ? `Mein Kalender (${person.display_name})` : person.display_name;
      options.push(el("option", { value: String(person.id) }, label));
    }
    viewSelect.replaceChildren(...options);
    viewSelect.hidden = options.length < 2;

    let saved = null;
    try {
      saved = localStorage.getItem(VIEW_KEY);
    } catch {
      saved = null;
    }
    const allowed = options.map((option) => option.value);
    // Wer planen darf, beginnt mit der Plantafel; alle anderen mit dem eigenen Kalender.
    const own = String(me.id);
    const fallback = mayDispatch && allowed.includes(BOARD) ? BOARD : own;
    view = allowed.includes(saved) ? saved : fallback;
    viewSelect.value = view;
  }

  viewSelect.addEventListener("change", () => setView(viewSelect.value));
  newButton.addEventListener("click", () =>
    dialog.open(null, { day: today < monday || today > addDays(monday, 6) ? monday : today, personId: view === BOARD ? null : Number(view) }),
  );

  // --- Dialog: Termin eintragen oder ändern ---

  function buildDialog() {
    let editing = null;
    const heading = el("h2", { id: "planning-dialog-title" });
    const titleInput = el("input", { type: "text", required: "", autocomplete: "off", placeholder: "z. B. Carport Berger" });
    const kindSelect = el("select");
    const startInput = el("input", { type: "date", required: "" });
    const endInput = el("input", { type: "date", required: "" });
    const allDay = el("input", { type: "checkbox", checked: true });
    const startTime = el("input", { type: "time", step: "900", value: "07:00" });
    const endTime = el("input", { type: "time", step: "900", value: "16:00" });
    const times = el("div", { class: "form-row", hidden: true }, field("Beginn", startTime), field("Ende", endTime));
    const locationInput = el("input", { type: "text", autocomplete: "off", placeholder: "z. B. Potsdam, Lindenstraße 4" });
    const noteInput = el("input", { type: "text", autocomplete: "off" });
    const peopleBox = el("fieldset", { class: "planning-people" });
    const saveButton = el("button", { type: "submit", class: "button" }, "Speichern");
    const deleteButton = el("button", { type: "button", class: "button-quiet planning-delete" }, "Löschen");
    const cancelButton = el("button", { type: "button", class: "button-quiet" }, "Abbrechen");
    const formMessage = messageBox();

    const form = el(
      "form",
      { class: "form planning-form", method: "dialog", novalidate: "" },
      heading,
      field("Worum geht es?", titleInput),
      field("Art", kindSelect),
      el("div", { class: "form-row" }, field("Erster Tag", startInput), field("Letzter Tag", endInput)),
      el("label", { class: "form-check" }, allDay, el("span", {}, "Ganzer Tag")),
      times,
      field("Ort", locationInput),
      field("Notiz", noteInput),
      peopleBox,
      formMessage,
      el("div", { class: "form-actions" }, saveButton, cancelButton, deleteButton),
    );
    const node = el("dialog", { class: "planning-dialog", "aria-labelledby": "planning-dialog-title" }, form);

    allDay.addEventListener("change", () => {
      times.hidden = allDay.checked;
    });
    // Der letzte Tag folgt dem ersten, solange er davor läge.
    startInput.addEventListener("change", () => {
      if (!endInput.value || endInput.value < startInput.value) {
        endInput.value = startInput.value;
      }
    });
    cancelButton.addEventListener("click", () => node.close());

    function fillPeople(selected) {
      peopleBox.replaceChildren(
        el("legend", {}, "Wer?"),
        ...people.map((person) =>
          el(
            "label",
            { class: "form-check" },
            el("input", { type: "checkbox", value: String(person.id), checked: selected.includes(person.id) }),
            el("span", {}, person.display_name),
          ),
        ),
      );
    }

    function open(entry, { day = today, personId = null } = {}) {
      editing = entry;
      formMessage.clear();
      kindSelect.replaceChildren(...kinds.map((kind) => el("option", { value: kind.kind }, kind.label)));
      heading.textContent = entry ? "Termin ändern" : "Termin eintragen";
      titleInput.value = entry?.title ?? "";
      kindSelect.value = entry?.kind ?? "job";
      startInput.value = entry?.start_date ?? day;
      endInput.value = entry?.end_date ?? day;
      allDay.checked = !entry?.start_time;
      times.hidden = allDay.checked;
      startTime.value = shortTime(entry?.start_time) || "07:00";
      endTime.value = shortTime(entry?.end_time) || "16:00";
      locationInput.value = entry?.location ?? "";
      noteInput.value = entry?.note ?? "";
      fillPeople(entry ? entry.people.map((p) => p.id) : personId ? [personId] : []);
      deleteButton.hidden = !entry;
      node.showModal();
      titleInput.focus();
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      formMessage.clear();
      const chosen = [...peopleBox.querySelectorAll("input:checked")].map((box) => Number(box.value));
      const body = {
        title: titleInput.value,
        kind: kindSelect.value,
        start_date: startInput.value,
        end_date: endInput.value || startInput.value,
        start_time: allDay.checked ? null : startTime.value,
        end_time: allDay.checked ? null : endTime.value,
        location: locationInput.value,
        note: noteInput.value,
        people: chosen,
      };
      try {
        const saved = editing
          ? await sendJson("PUT", `/api/planning/entries/${editing.id}`, body)
          : await sendJson("POST", "/api/planning/entries", body);
        node.close();
        const done = `Gespeichert: ${saved.entry.title}.`;
        message.show(saved.warnings.length ? `${done} Achtung: ${saved.warnings.join(" ")}` : done);
        if (saved.entry.start_date > addDays(monday, 6) || saved.entry.end_date < monday) {
          monday = mondayOf(saved.entry.start_date);
        }
        await loadWeek();
      } catch (error) {
        formMessage.show(error.message, true);
      }
    });

    deleteButton.addEventListener("click", async () => {
      if (!window.confirm(`Termin „${editing.title}“ wirklich löschen?`)) {
        return;
      }
      try {
        await sendJson("DELETE", `/api/planning/entries/${editing.id}`);
        node.close();
        message.show(`Gelöscht: ${editing.title}.`);
        await loadWeek();
      } catch (error) {
        formMessage.show(error.message, true);
      }
    });

    return { node, open };
  }

  // --- Start ---
  [people, kinds] = await Promise.all([getJson("/api/planning/people"), getJson("/api/planning/kinds")]);
  fillViewSelect();
  await loadWeek();
}
