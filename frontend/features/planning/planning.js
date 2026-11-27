// Der Reiter "Kalender" (Feature F8): wer ist wann wo – Woche für Woche.
//
// Zwei Ansichten, beide als Raster mit der Kalenderwoche (KW) groß oben:
// - Plantafel: eine Zeile je Person, eine Spalte je Wochentag. Für die Planung im Büro.
// - Persönlicher Kalender: die Woche einer Person, ein Kästchen je Tag. Auf dem Handy untereinander.
// Ein Termin zeigt im Raster nur seinen Namen (z. B. „Carport Berger“). Alles Weitere – Art, Zeit,
// Ort, wer noch dabei ist – steht im Tooltip, für Bildschirmleser im Namen des Knopfs und nach
// einem Klick: mit Planungsrecht im Dialog, sonst klappt der Termin auf.
// Mit dem Recht „calendar.dispatch“ trägt man Termine ein (Klick auf + in einer Zelle oder
// „Termin eintragen“) und ändert sie (Klick auf den Termin). Wer „calendar.view_all“ nicht hat,
// sieht nur den eigenen Kalender. Alles aus der API kommt mit textContent in die Seite.
//
// Fahrzeuge und Maschinen stehen als eigene Zeilen unter den Personen. Wer planen darf, zieht
// einen Termin mit der Maus auf einen anderen Tag oder eine andere Zeile; „Rückgängig“ holt ihn
// zurück. Auf dem Handy (ohne Ziehen) geht dasselbe über den Dialog.

import { getJson, sendJson } from "../../shared/api.js";
import { el, field, menuButton, messageBox } from "../../shared/dom.js";
import { can, currentAccount } from "../../shared/session.js";
import { openIcal } from "./ical.js";
import { openOwnRequests } from "./requests.js";

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
  let resources = [];
  let kinds = [];
  let entries = [];
  let view = BOARD;

  // --- Gerüst ---
  const weekNumberLabel = el("strong", { class: "planning-week-number" });
  const weekRange = el("span", { class: "planning-week-range" });
  const weekLabel = el("p", { class: "planning-week", "aria-live": "polite" }, weekNumberLabel, weekRange);
  const viewSelect = el("select", { "aria-label": "Ansicht" });
  const newButton = el("button", { type: "button", class: "button", hidden: !mayDispatch }, "Termin eintragen");

  // Was man selten braucht, steht im Menü „Mehr“ statt dauerhaft auf der Seite.
  function moreMenu() {
    const items = [];
    if (can("calendar.request_absence") && !can("calendar.approve_absence")) {
      items.push({ label: "Urlaub beantragen …", onSelect: openOwnRequests });
    }
    items.push({ label: "Kalender aufs Handy holen …", onSelect: openIcal });
    return menuButton(el("button", { type: "button", class: "button-quiet" }, "Mehr ▾"), items);
  }
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
    el("div", { class: "planning-actions" }, viewSelect, newButton, moreMenu()),
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
    weekNumberLabel.textContent = `KW ${weekNumber(monday)}`;
    weekRange.textContent = `${shortDate(monday)}–${parseDate(sunday).toLocaleDateString("de-DE")}`;
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

  // Eine Zeile der Plantafel: eine Person ("p:3") oder ein Fahrzeug/eine Maschine ("r:2").
  const rowKey = (type, rowId) => `${type}:${rowId}`;
  const parseRow = (key) => ({ type: key[0], id: Number(key.slice(2)) });

  function inRow(entry, key) {
    const row = parseRow(key);
    const list = row.type === "p" ? entry.people : entry.resources;
    return list.some((item) => item.id === row.id);
  }

  function entriesOn(day, key) {
    return entries.filter(
      (entry) => entry.start_date <= day && entry.end_date >= day && (key === undefined || inRow(entry, key)),
    );
  }

  // Ein Termin als Eingabe für die API (für Verschieben und Rückgängig).
  function toBody(entry) {
    return {
      title: entry.title,
      kind: entry.kind,
      start_date: entry.start_date,
      end_date: entry.end_date,
      start_time: entry.start_time ? shortTime(entry.start_time) : null,
      end_time: entry.end_time ? shortTime(entry.end_time) : null,
      location: entry.location,
      note: entry.note,
      project_id: entry.project_id,
      people: entry.people.map((person) => person.id),
      resources: entry.resources.map((resource) => resource.id),
    };
  }

  // --- Verschieben per Ziehen ---

  // Zieht man einen Termin von Tag/Zeile A nach Tag/Zeile B, rücken erster und letzter Tag um
  // denselben Abstand. Wechselt die Zeile, tritt die neue Person (das neue Fahrzeug) an die Stelle
  // der alten; alle anderen Eingeplanten bleiben.
  async function moveEntry(entryId, fromKey, fromDay, toKey, toDay) {
    const entry = entries.find((item) => item.id === entryId);
    if (!entry || (fromKey === toKey && fromDay === toDay)) {
      return;
    }
    const from = parseRow(fromKey);
    const to = parseRow(toKey);
    if (from.type !== to.type) {
      message.show("Termine lassen sich nur von Person zu Person oder von Fahrzeug zu Fahrzeug ziehen.", true);
      return;
    }
    const before = toBody(entry);
    const after = toBody(entry);
    const shift = Math.round((parseDate(toDay) - parseDate(fromDay)) / 86400000);
    after.start_date = addDays(entry.start_date, shift);
    after.end_date = addDays(entry.end_date, shift);
    const listName = from.type === "p" ? "people" : "resources";
    if (from.id !== to.id) {
      after[listName] = [...new Set(after[listName].map((id) => (id === from.id ? to.id : id)))];
    }
    await saveMove(entry.id, after, before, `Verschoben: ${entry.title}`);
  }

  async function saveMove(entryId, body, undoBody, text) {
    try {
      const saved = await sendJson("PUT", `/api/planning/entries/${entryId}`, body);
      await loadWeek();
      const warning = saved.warnings.length ? ` Achtung: ${saved.warnings.join(" ")}` : "";
      message.show(`${text}.${warning}`);
      if (undoBody) {
        message.append(
          " ",
          el(
            "button",
            {
              type: "button",
              class: "button-quiet planning-undo",
              onclick: () => saveMove(entryId, undoBody, null, `Zurückgeholt: ${body.title}`),
            },
            "Rückgängig",
          ),
        );
      }
    } catch (error) {
      message.show(error.message, true);
    }
  }

  // --- Anzeigen ---

  function show() {
    content.replaceChildren(view === BOARD ? board() : personalList(Number(view)));
  }

  // Alles, was man über einen Termin wissen will, als Zeilen: Art, Zeit und Ort, wer noch dabei
  // ist. withPeople: auch die Personen nennen (im persönlichen Kalender die Kollegen).
  function detailLines(entry, withPeople) {
    const lines = [];
    if (entry.title !== entry.kind_label) {
      lines.push(entry.kind_label);
    }
    const time = entry.start_time ? `${shortTime(entry.start_time)}–${shortTime(entry.end_time)}` : "ganztägig";
    lines.push([time, entry.location].filter(Boolean).join(" · "));
    const together = withPeople ? [...entry.people, ...entry.resources] : entry.resources;
    if (together.length) {
      lines.push(together.map((p) => p.display_name).join(", "));
    }
    if (entry.note) {
      lines.push(entry.note);
    }
    return lines;
  }

  // Ein Termin als kurzes Kärtchen: nur der Name. Mit Planungsrecht ist es ein Knopf zum Ändern
  // und lässt sich auf der Plantafel ziehen (drag = { key, day }: woher er gezogen wird). Ohne
  // Planungsrecht klappt es per Klick auf und zeigt die Einzelheiten.
  function chip(entry, { withPeople = false, drag = null } = {}) {
    const lines = detailLines(entry, withPeople);
    const absent = kinds.find((kind) => kind.kind === entry.kind)?.absence;
    const className = `planning-chip${absent ? " planning-chip-absence" : ""}`;
    const name = el("span", { class: "planning-chip-title" }, entry.title);
    const tooltip = [entry.title, ...lines].join("\n");
    if (!mayDispatch) {
      return el(
        "details",
        { class: className, title: tooltip },
        el("summary", {}, name),
        ...lines.map((line) => el("span", { class: "planning-chip-detail" }, line)),
      );
    }
    const button = el(
      "button",
      {
        type: "button",
        class: className,
        title: tooltip,
        "aria-label": `${entry.title} ändern – ${lines.join(", ")}`,
        onclick: () => dialog.open(entry),
      },
      name,
    );
    if (drag) {
      button.draggable = true;
      button.addEventListener("dragstart", (event) => {
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", JSON.stringify({ id: entry.id, ...drag }));
      });
    }
    return button;
  }

  // Eine Zelle der Plantafel: Termine dieser Zeile an diesem Tag, dazu „+“ und Ablegen.
  function cell(key, label, day, dayIndex) {
    const td = el(
      "td",
      { class: day === today ? "planning-today" : "" },
      ...entriesOn(day, key).map((entry) => chip(entry, { drag: mayDispatch ? { key, day } : null })),
    );
    if (!mayDispatch) {
      return td;
    }
    const row = parseRow(key);
    td.append(
      el(
        "button",
        {
          type: "button",
          class: "planning-add",
          "aria-label": `Termin für ${label} am ${DAY_NAMES[dayIndex]} ${shortDate(day)} eintragen`,
          onclick: () =>
            dialog.open(null, row.type === "p" ? { day, personId: row.id } : { day, resourceId: row.id }),
        },
        "+",
      ),
    );
    td.addEventListener("dragover", (event) => {
      event.preventDefault();
      td.classList.add("planning-drop");
    });
    td.addEventListener("dragleave", () => td.classList.remove("planning-drop"));
    td.addEventListener("drop", (event) => {
      event.preventDefault();
      td.classList.remove("planning-drop");
      try {
        const data = JSON.parse(event.dataTransfer.getData("text/plain"));
        moveEntry(data.id, data.key, data.day, key, day);
      } catch {
        // Etwas anderes als ein Termin wurde abgelegt – nichts zu tun.
      }
    });
    return td;
  }

  function board() {
    if (people.length === 0) {
      return el("p", { class: "empty" }, "Es gibt noch keine Konten, die man einplanen kann.");
    }
    const head = el(
      "tr",
      {},
      el("th", { scope: "col", class: "planning-person planning-corner" }, `KW ${weekNumber(monday)}`),
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
        ...days().map((day, i) => cell(rowKey("p", person.id), person.display_name, day, i)),
      ),
    );
    if (resources.length) {
      rows.push(
        el("tr", { class: "planning-group" }, el("th", { scope: "rowgroup", colspan: "8" }, "Fahrzeuge und Maschinen")),
        ...resources.map((resource) =>
          el(
            "tr",
            {},
            el(
              "th",
              { scope: "row", class: "planning-person" },
              resource.name,
              el("small", { class: "planning-resource-kind" }, resource.category_label),
            ),
            ...days().map((day, i) => cell(rowKey("r", resource.id), resource.name, day, i)),
          ),
        ),
      );
    }
    return el("div", { class: "table-scroll planning-board-wrap" }, el("table", { class: "planning-board" }, el("thead", {}, head), el("tbody", {}, ...rows)));
  }

  // Die Woche einer Person als Raster: ein Kästchen je Tag (auf schmalen Bildschirmen untereinander).
  function personalList(personId) {
    const person = people.find((p) => p.id === personId);
    const list = el("div", { class: "planning-list" });
    if (person) {
      list.append(el("h2", {}, person.id === me.id ? "Meine Woche" : `Woche von ${person.display_name}`));
    }
    const grid = el("div", { class: "planning-week-grid" });
    days().forEach((day, i) => {
      const dayEntries = entriesOn(day, rowKey("p", personId));
      grid.append(
        el(
          "section",
          {
            class: `planning-day${day === today ? " planning-today" : ""}`,
            "aria-label": longDate(day),
            "aria-current": day === today ? "date" : "false",
          },
          el("h3", {}, day === today ? `Heute · ${shortDate(day)}` : `${DAY_NAMES[i]} ${shortDate(day)}`),
          ...(dayEntries.length
            ? dayEntries.map((entry) => chip(entry, { withPeople: entry.people.length > 1 }))
            : [el("p", { class: "planning-free" }, "frei")]),
        ),
      );
    });
    list.append(grid);
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
    const noteInput = el("textarea", { rows: "1", placeholder: "z. B. Material vorher in der Halle laden" });
    const projectInput = el("input", { type: "number", min: "1", step: "1", inputmode: "numeric" });
    const peopleBox = el("fieldset", { class: "planning-people" });
    const resourcesBox = el("fieldset", { class: "planning-people" });
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
      el(
        "div",
        { class: "form-row" },
        field("Ort", locationInput),
        field("Projektnummer", projectInput, "Freiwillig. Damit landen die Stunden auf dem Projekt."),
      ),
      field("Notiz", noteInput),
      peopleBox,
      resourcesBox,
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

    function fillResources(selected) {
      resourcesBox.hidden = resources.length === 0;
      resourcesBox.replaceChildren(
        el("legend", {}, "Fahrzeuge und Maschinen"),
        ...resources.map((resource) =>
          el(
            "label",
            { class: "form-check" },
            el("input", { type: "checkbox", value: String(resource.id), checked: selected.includes(resource.id) }),
            el("span", {}, `${resource.name} (${resource.category_label})`),
          ),
        ),
      );
    }

    function open(entry, { day = today, personId = null, resourceId = null } = {}) {
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
      projectInput.value = entry?.project_id ?? "";
      fillPeople(entry ? entry.people.map((p) => p.id) : personId ? [personId] : []);
      fillResources(entry ? entry.resources.map((r) => r.id) : resourceId ? [resourceId] : []);
      deleteButton.hidden = !entry;
      node.showModal();
      titleInput.focus();
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      formMessage.clear();
      const chosen = [...peopleBox.querySelectorAll("input:checked")].map((box) => Number(box.value));
      const chosenResources = [...resourcesBox.querySelectorAll("input:checked")].map((box) => Number(box.value));
      const body = {
        title: titleInput.value,
        kind: kindSelect.value,
        start_date: startInput.value,
        end_date: endInput.value || startInput.value,
        start_time: allDay.checked ? null : startTime.value,
        end_time: allDay.checked ? null : endTime.value,
        location: locationInput.value,
        note: noteInput.value,
        project_id: projectInput.value ? Number(projectInput.value) : null,
        people: chosen,
        resources: chosenResources,
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
  [people, resources, kinds] = await Promise.all([
    getJson("/api/planning/people"),
    getJson("/api/planning/resources"),
    getJson("/api/planning/kinds"),
  ]);
  fillViewSelect();
  await loadWeek();
}
