// Tabellen ohne Querscrollen – und trotzdem kompakt. Passt eine Tabelle nicht in die Breite ihres
// Platzes, versucht diese Datei der Reihe nach, sie passend zu machen; sobald sie passt, hört sie auf:
//
//   1. eng setzen    – weniger Abstand, Text in den Zellen darf umbrechen      (Klasse table-tight)
//   2. Spalten weg   – zuerst Spalten mit data-priority="3", dann "2"          (Klasse table-hide-col)
//                       Wichtiges bleibt immer: Spalten ohne data-priority werden nie ausgeblendet.
//   3. untereinander – nur als letzter Ausweg: jede Zeile ein Block           (Klasse table-stacked)
//
// Ein Reiter markiert verzichtbare Spalten am Kopf: el("th", { "data-priority": "3" }, "Zuletzt …").
// Sonst muss er nichts tun: watchTables() (aufgerufen in app.js) achtet auf neue Tabellen und
// Zeilen von selbst. Für Stufe 3 schreibt die Datei den Spaltennamen in data-label jeder Zelle;
// ein <th> kann mit eigenem data-label einen anderen Namen vorgeben. Aussehen: style.css.

const TIGHT = "table-tight";
const STACKED = "table-stacked";
const HIDDEN = "table-hide-col";
const widths = new WeakMap(); // Platz → zuletzt gemessene Breite (nur bei Änderung neu prüfen)

function headRow(table) {
  return table.tHead?.rows[table.tHead.rows.length - 1] ?? null;
}

// Spaltennummer → Zellen der Spalte (Kopf und Körper), Spannen über mehrere Spalten zählen mit.
function columnCells(table, index) {
  const cells = [];
  for (const row of table.rows) {
    let column = 0;
    for (const cell of row.cells) {
      if (column === index && cell.colSpan === 1) {
        cells.push(cell);
      }
      column += cell.colSpan;
    }
  }
  return cells;
}

// Schreibt in jede Zelle den Namen ihrer Spalte (data-label) – gebraucht in Stufe 3.
function label(table) {
  const head = headRow(table);
  if (!head) {
    return;
  }
  const names = [];
  for (const th of head.cells) {
    for (let i = 0; i < th.colSpan; i += 1) {
      names.push(th.dataset.label ?? th.textContent.trim());
    }
  }
  for (const body of [...table.tBodies, ...(table.tFoot ? [table.tFoot] : [])]) {
    for (const row of body.rows) {
      let column = 0;
      for (const cell of row.cells) {
        if (cell.dataset.label === undefined || cell.dataset.autoLabel) {
          cell.dataset.label = names[column] ?? "";
          cell.dataset.autoLabel = "1";
        }
        column += cell.colSpan;
      }
    }
  }
}

function fits(table) {
  return table.scrollWidth <= table.parentElement.clientWidth + 1;
}

function fit(table) {
  const place = table.parentElement;
  if (!place || !table.isConnected) {
    return;
  }
  // Zurück auf „normal“, dann Stufe für Stufe.
  table.classList.remove(TIGHT, STACKED);
  table.querySelectorAll(`.${HIDDEN}`).forEach((cell) => cell.classList.remove(HIDDEN));
  if (fits(table)) {
    return;
  }
  table.classList.add(TIGHT);
  if (fits(table)) {
    return;
  }
  const head = headRow(table);
  for (const level of ["3", "2"]) {
    let column = 0;
    for (const th of head?.cells ?? []) {
      if (th.dataset.priority === level) {
        columnCells(table, column).forEach((cell) => cell.classList.add(HIDDEN));
      }
      column += th.colSpan;
    }
    if (fits(table)) {
      return;
    }
  }
  table.classList.add(STACKED);
}

const resized = new ResizeObserver((changes) => {
  for (const change of changes) {
    const place = change.target;
    const width = Math.round(change.contentRect.width);
    if (widths.get(place) === width) {
      continue; // nur die Höhe hat sich geändert
    }
    widths.set(place, width);
    for (const table of place.querySelectorAll(":scope > table")) {
      fit(table);
    }
  }
});

function check(table) {
  label(table);
  if (table.parentElement) {
    resized.observe(table.parentElement);
  }
  fit(table);
}

// Beobachtet die Seite: jede neue oder geänderte Tabelle wird beschriftet und geprüft.
export function watchTables(root = document.body) {
  let waiting = false;
  const all = () => {
    waiting = false;
    root.querySelectorAll("table").forEach(check);
  };
  new MutationObserver(() => {
    if (!waiting) {
      waiting = true;
      requestAnimationFrame(all);
    }
  }).observe(root, { childList: true, subtree: true });
  all();
}
