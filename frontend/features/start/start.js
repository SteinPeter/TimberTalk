// Der Reiter "Start": das Dashboard (Feature F12). Man erreicht es über das Logo oben links.
//
// Das Dashboard zeigt Widgets – kleine Karten der einzelnen Features (offene Urlaubsanträge,
// nächste Termine, Stunden heute …). Diese Datei kennt kein einziges Widget mit Namen: Sie fragt
// das Backend, welche es gibt (GET /api/dashboard/widgets), lädt sie und zeigt sie an.
//
// SO BAUT MAN EIN WIDGET – nur eine neue Datei, nichts eintragen:
//   frontend/features/<ordner-des-features>/widgets/<name>.js
//
//   export const title = "Meine nächsten Termine";   // Überschrift der Karte (Pflicht)
//   export const permission = "calendar.view_all";   // nur mit diesem Recht (freiwillig)
//   export const order = 20;                         // Platz in der Voreinstellung (klein = oben)
//   export const defaultOn = true;                   // ohne eigene Auswahl zu sehen? (freiwillig)
//   export const showsWhen = "wenn Anträge offen sind"; // erscheint nur bei Bedarf (freiwillig)
//   export async function render(container) { … }    // füllt die Karte (Pflicht)
//
// Gibt render() `false` zurück, gibt es gerade nichts zu zeigen: Die Karte erscheint dann nicht
// (z. B. „Offene Urlaubsanträge“ ohne offenen Antrag). showsWhen sagt das unter „Anpassen“ an.
//
// Die Karten passen ihre Größe selbst an: Jede ist so hoch wie ihr Inhalt, die Spalten füllen
// die Breite, und ändert sich der Inhalt (Antrag entschieden), rückt der Rest nach.
//
// Jede Person stellt mit „Anpassen“ ein, welche Widgets sie in welcher Reihenfolge sieht; das
// speichert das Backend je Konto (PUT /api/dashboard/layout).

import { getJson, sendJson } from "../../shared/api.js";
import { el, messageBox } from "../../shared/dom.js";
import { can, currentAccount } from "../../shared/session.js";

export const id = "start";
export const title = "Start";

export async function render(panel) {
  const me = currentAccount();
  const editButton = el("button", { type: "button", class: "button-quiet" }, "Anpassen");
  const grid = el("div", { class: "dashboard-grid" });
  const editor = el("div", { class: "form dashboard-editor", hidden: true });
  const message = messageBox();

  panel.replaceChildren(
    el(
      "div",
      { class: "dashboard-head" },
      el("div", {}, el("h1", {}, me ? `Hallo ${me.display_name.split(" ")[0]}` : "Übersicht"), el("p", { class: "hint" }, "Was heute wichtig ist.")),
      me ? editButton : "",
    ),
    message,
    editor,
    grid,
  );

  // Ohne Backend (oder ohne Anmeldung) gibt es nur den Systemstatus – er sagt, was los ist.
  let widgets;
  try {
    widgets = await loadWidgets();
  } catch (error) {
    const status = await import("./widgets/status.js");
    grid.replaceChildren((await card({ id: "start/status", module: status })) ?? "");
    return;
  }
  let chosen = await currentChoice();

  async function loadWidgets() {
    const found = await getJson("/api/dashboard/widgets");
    const loaded = await Promise.all(
      found.map(async (widget) => {
        try {
          return { ...widget, module: await import(widget.path) };
        } catch (error) {
          console.error(`Widget "${widget.id}" ließ sich nicht laden:`, error);
          return null;
        }
      }),
    );
    // Nur Widgets, für die man das Recht hat; sortiert nach ihrem Platz in der Voreinstellung.
    return loaded
      .filter((widget) => widget && (!widget.module.permission || can(widget.module.permission)))
      .sort((a, b) => (a.module.order ?? 100) - (b.module.order ?? 100) || a.id.localeCompare(b.id));
  }

  async function currentChoice() {
    const layout = await getJson("/api/dashboard/layout");
    const known = new Set(widgets.map((widget) => widget.id));
    if (layout.widgets === null) {
      return widgets.filter((widget) => widget.module.defaultOn).map((widget) => widget.id);
    }
    return layout.widgets.filter((widgetId) => known.has(widgetId));
  }

  // Eine Karte: Überschrift und Inhalt des Widgets. Ein Fehler betrifft nur diese Karte.
  // null: Das Widget hat gerade nichts zu zeigen (render() gab false zurück).
  async function card(widget) {
    const body = el("div", { class: "dashboard-body" });
    const section = el("section", { class: "dashboard-card", "aria-label": widget.module.title }, el("h2", {}, widget.module.title), body);
    try {
      if ((await widget.module.render(body)) === false) {
        return null;
      }
    } catch (error) {
      console.error(`Widget "${widget.id}" konnte nicht aufgebaut werden:`, error);
      body.replaceChildren(el("p", { class: "planning-free" }, `Konnte nicht geladen werden (${error.message}).`));
    }
    return section;
  }

  async function showGrid() {
    const byId = new Map(widgets.map((widget) => [widget.id, widget]));
    const cards = (await Promise.all(chosen.map((widgetId) => card(byId.get(widgetId))))).filter(Boolean);
    let empty = "Keine Widgets gewählt. Mit „Anpassen“ kommen welche dazu.";
    if (chosen.length) {
      empty = "Gerade gibt es nichts zu erledigen.";
    }
    grid.replaceChildren(...(cards.length ? cards : [el("p", { class: "empty" }, empty)]));
    sizer.disconnect();
    cards.forEach((section) => sizer.observe(section));
  }

  // Jede Karte belegt so viele schmale Raster-Zeilen (style.css: .dashboard-grid), wie sie samt
  // Abstand darunter hoch ist. So gibt es keine Lücken unter kurzen Karten, und eine Karte wächst
  // oder schrumpft mit ihrem Inhalt.
  const sizer = new ResizeObserver((changes) => {
    const row = parseFloat(getComputedStyle(grid).gridAutoRows);
    for (const change of changes) {
      const section = change.target;
      const height = section.getBoundingClientRect().height + parseFloat(getComputedStyle(section).marginBottom);
      section.style.gridRowEnd = `span ${Math.max(1, Math.ceil(height / row))}`;
    }
  });

  // --- Anpassen: an- und abwählen, Reihenfolge ändern ---

  function showEditor() {
    let draft = [...chosen, ...widgets.map((w) => w.id).filter((widgetId) => !chosen.includes(widgetId))];
    const on = new Set(chosen);
    const list = el("ul", { class: "dashboard-choose" });

    function row(widgetId, index) {
      const widget = widgets.find((w) => w.id === widgetId);
      const box = el("input", { type: "checkbox", checked: on.has(widgetId) });
      box.addEventListener("change", () => (box.checked ? on.add(widgetId) : on.delete(widgetId)));
      const move = (step) => {
        const target = index + step;
        if (target < 0 || target >= draft.length) {
          return;
        }
        [draft[index], draft[target]] = [draft[target], draft[index]];
        fill();
      };
      return el(
        "li",
        {},
        el(
          "label",
          { class: "form-check" },
          box,
          el(
            "span",
            {},
            widget.module.title,
            ...(widget.module.showsWhen ? [el("small", { class: "dashboard-when" }, `Erscheint nur, ${widget.module.showsWhen}.`)] : []),
          ),
        ),
        el(
          "span",
          { class: "dashboard-move" },
          el("button", { type: "button", class: "button-quiet", "aria-label": `${widget.module.title} nach oben`, disabled: index === 0, onclick: () => move(-1) }, "↑"),
          el("button", { type: "button", class: "button-quiet", "aria-label": `${widget.module.title} nach unten`, disabled: index === draft.length - 1, onclick: () => move(1) }, "↓"),
        ),
      );
    }
    function fill() {
      list.replaceChildren(...draft.map(row));
    }
    fill();

    const save = async (widgetIds) => {
      try {
        const saved = await sendJson("PUT", "/api/dashboard/layout", { widgets: widgetIds });
        chosen = saved.widgets ?? (await currentChoice());
        editor.hidden = true;
        editButton.hidden = false;
        await showGrid();
        message.show("Dashboard gespeichert.");
      } catch (error) {
        message.show(error.message, true);
      }
    };
    editor.replaceChildren(
      el("h2", {}, "Dashboard anpassen"),
      el("p", { class: "form-hint" }, "Häkchen: wird angezeigt. Mit ↑ und ↓ die Reihenfolge ändern."),
      list,
      el(
        "div",
        { class: "form-actions" },
        el("button", { type: "button", class: "button", onclick: () => save(draft.filter((widgetId) => on.has(widgetId))) }, "Speichern"),
        el("button", { type: "button", class: "button-quiet", onclick: () => save(null) }, "Voreinstellung"),
        el("button", { type: "button", class: "button-quiet", onclick: () => { editor.hidden = true; editButton.hidden = false; } }, "Abbrechen"),
      ),
    );
    editor.hidden = false;
    editButton.hidden = true;
    message.clear();
  }

  editButton.addEventListener("click", showEditor);
  await showGrid();
}
