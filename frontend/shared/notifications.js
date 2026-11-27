// Der Knopf „Mitteilungen“ oben rechts in der Leiste (Feature notifications, F8).
// Er zeigt, wie viele Mitteilungen ungelesen sind, und öffnet darunter eine Liste. Beim Öffnen
// gelten alle als gelesen. Aufgaben („bitte Urlaubsantrag entscheiden“) verschwinden von selbst,
// sobald sie erledigt sind; jede andere Mitteilung entfernt man mit ✕. Die Zahl wird jede Minute neu geholt, solange die Seite sichtbar ist.

import { CHANGED_EVENT, getJson, sendJson } from "./api.js";
import { el, formatDateTime } from "./dom.js";

const REFRESH_MS = 60_000;

export function notificationsButton() {
  const badge = el("span", { class: "notify-badge", hidden: true });
  // Eine Glocke statt des Worts – der Name steht für Bildschirmleser in aria-label.
  const bell = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  bell.setAttribute("viewBox", "0 0 24 24");
  bell.setAttribute("class", "notify-bell");
  bell.setAttribute("aria-hidden", "true");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute(
    "d",
    "M12 3a6 6 0 0 0-6 6v3.5L4.5 15v1.5h15V15L18 12.5V9a6 6 0 0 0-6-6Zm-2 15a2 2 0 0 0 4 0",
  );
  bell.append(path);
  const button = el(
    "button",
    {
      type: "button",
      class: "notify-button",
      title: "Mitteilungen",
      "aria-label": "Mitteilungen",
      "aria-expanded": "false",
      "aria-haspopup": "true",
    },
    bell,
    badge,
  );
  const list = el("ul", { class: "notify-list" });
  const panel = el(
    "div",
    { class: "notify-panel", role: "region", "aria-label": "Mitteilungen", hidden: true },
    list,
  );
  const box = el("div", { class: "notify" }, button, panel);

  function showCount(unread) {
    badge.textContent = String(unread);
    badge.hidden = unread === 0;
    button.setAttribute("aria-label", unread ? `Mitteilungen, ${unread} ungelesen` : "Mitteilungen");
  }

  async function refresh() {
    if (document.hidden) {
      return;
    }
    try {
      showCount((await getJson("/api/notifications/unread-count")).unread);
    } catch {
      // Keine Verbindung: beim nächsten Mal wieder versuchen.
    }
  }

  function row(message) {
    const remove = el(
      "button",
      {
        type: "button",
        class: "notify-remove",
        title: "Entfernen",
        "aria-label": `Mitteilung entfernen: ${message.text}`,
      },
      "✕",
    );
    const item = el(
      "li",
      { class: message.read_at ? "" : "notify-unread" },
      el(
        "div",
        { class: "notify-text" },
        // Mit Link (z. B. offener Urlaubsantrag → Dashboard) ist die Mitteilung ein Knopf.
        message.link
          ? el(
              "button",
              {
                type: "button",
                class: "notify-link",
                onclick: () => {
                  close();
                  window.location.hash = message.link;
                },
              },
              message.text,
            )
          : el("span", {}, message.text),
        el("small", {}, formatDateTime(message.created_at)),
      ),
      remove,
    );
    remove.addEventListener("click", async (event) => {
      event.stopPropagation(); // sonst schließt der Klick „daneben“ die Liste
      try {
        await sendJson("DELETE", `/api/notifications/${message.id}`);
      } catch {
        return; // schon weg oder keine Verbindung – die Liste bleibt, wie sie ist
      }
      item.remove();
      if (!list.children.length) {
        list.append(el("li", { class: "notify-empty" }, "Keine Mitteilungen."));
      }
    });
    return item;
  }

  async function open() {
    const messages = await getJson("/api/notifications");
    list.replaceChildren(
      ...(messages.length
        ? messages.map(row)
        : [el("li", { class: "notify-empty" }, "Keine Mitteilungen.")]),
    );
    panel.hidden = false;
    button.setAttribute("aria-expanded", "true");
    if (messages.some((message) => !message.read_at)) {
      await sendJson("POST", "/api/notifications/read-all");
      showCount(0);
    }
  }

  function close() {
    panel.hidden = true;
    button.setAttribute("aria-expanded", "false");
  }

  button.addEventListener("click", () => (panel.hidden ? open() : close()));
  // Schließen mit Escape oder mit einem Klick daneben.
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !panel.hidden) {
      close();
      button.focus();
    }
  });
  document.addEventListener("click", (event) => {
    if (!box.contains(event.target)) {
      close();
    }
  });
  document.addEventListener("visibilitychange", refresh);
  window.addEventListener(CHANGED_EVENT, refresh);

  refresh();
  setInterval(refresh, REFRESH_MS);
  return box;
}
