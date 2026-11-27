// Abschnitte in einem gemeinsamen Reiter (F0e): Mehrere Features zeigen ihren Teil in einem
// Reiter wie „Einstellungen“ oder „Buchungen“. Jeder Abschnitt ist eine eigene Datei, die
// genau wie ein Reiter `id`, `title` und `render(container)` exportiert. Diese Datei baut daraus
// eine Auswahl und zeigt immer einen Abschnitt.
//
// layout "sidebar": Liste links, Abschnitt rechts (Einstellungen).
// layout "tabs":    Reiter über dem Abschnitt (Buchungen).
// Beide sind für Bildschirmleser eine Reiterliste (role="tablist") und mit den Pfeiltasten
// bedienbar. Der zuletzt gewählte Abschnitt wird im Browser gemerkt.
//
// Exportiert ein Abschnitt zusätzlich `permission` (z. B. "finance.view"), erscheint er nur für
// Konten mit diesem Recht (F10).

import { can } from "./session.js";

// Baut die Abschnitte in `panel` auf. Gibt es noch keinen, steht dort `emptyText`.
export function renderSections(panel, { tabId, sections: all, layout, emptyText }) {
  const sections = all.filter((section) => !section.permission || can(section.permission));
  if (sections.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = emptyText;
    panel.append(empty);
    return;
  }

  const storageKey = `timbertalk.${tabId}.section`;
  const box = document.createElement("div");
  box.className = `sections sections-${layout}`;

  const list = document.createElement("div");
  list.className = "sections-list";
  list.setAttribute("role", "tablist");
  list.setAttribute("aria-orientation", layout === "sidebar" ? "vertical" : "horizontal");

  const area = document.createElement("div");
  area.className = "sections-area";

  // Je Abschnitt ein Knopf in der Liste und ein leerer Bereich, der beim ersten Öffnen gefüllt
  // wird.
  const entries = sections.map((section) => {
    const button = document.createElement("button");
    button.type = "button";
    button.id = `${tabId}-tab-${section.id}`;
    button.className = "sections-button";
    button.setAttribute("role", "tab");
    button.setAttribute("aria-controls", `${tabId}-section-${section.id}`);
    button.textContent = section.title;

    const container = document.createElement("div");
    container.id = `${tabId}-section-${section.id}`;
    container.className = "sections-panel";
    container.setAttribute("role", "tabpanel");
    container.setAttribute("aria-labelledby", button.id);
    container.hidden = true;

    list.append(button);
    area.append(container);
    return { section, button, container, rendered: false };
  });

  function select(entry, moveFocus = false) {
    for (const other of entries) {
      const active = other === entry;
      other.button.setAttribute("aria-selected", String(active));
      other.button.tabIndex = active ? 0 : -1;
      other.container.hidden = !active;
    }
    if (moveFocus) {
      entry.button.focus();
    }
    remember(storageKey, entry.section.id);
    renderOnce(entry);
  }

  for (const entry of entries) {
    entry.button.addEventListener("click", () => select(entry));
  }

  // Pfeiltasten, Pos1 und Ende wechseln den Abschnitt, wie in einer Reiterliste üblich.
  list.addEventListener("keydown", (event) => {
    const current = entries.findIndex((entry) => entry.button === document.activeElement);
    if (current === -1) {
      return;
    }
    const keys = {
      ArrowDown: current + 1,
      ArrowRight: current + 1,
      ArrowUp: current - 1,
      ArrowLeft: current - 1,
      Home: 0,
      End: entries.length - 1,
    };
    if (!(event.key in keys)) {
      return;
    }
    event.preventDefault();
    const next = (keys[event.key] + entries.length) % entries.length;
    select(entries[next], true);
  });

  box.append(list, area);
  panel.append(box);

  const saved = recall(storageKey);
  select(entries.find((entry) => entry.section.id === saved) ?? entries[0]);
}

// Ruft render() eines Abschnitts beim ersten Öffnen auf. Geht dabei etwas schief, zeigt nur
// dieser Abschnitt eine Meldung – die anderen funktionieren weiter.
async function renderOnce(entry) {
  if (entry.rendered) {
    return;
  }
  entry.rendered = true;
  try {
    await entry.section.render(entry.container);
  } catch (error) {
    console.error(`Abschnitt "${entry.section.id}" konnte nicht aufgebaut werden:`, error);
    const message = document.createElement("p");
    message.className = "empty";
    message.textContent = `Dieser Abschnitt konnte nicht geladen werden (${error.message}).`;
    entry.container.replaceChildren(message);
  }
}

// Merken im Browser kann scheitern (z. B. im privaten Fenster). Dann wird eben nichts gemerkt.
function remember(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // nichts zu tun
  }
}

function recall(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}
