// Der Knopf „Mitteilungen“ oben rechts in der Leiste (Feature notifications, F8).
// Er zeigt, wie viele Mitteilungen ungelesen sind, und öffnet darunter eine Liste. Beim Öffnen
// gelten alle als gelesen. Die Zahl wird jede Minute neu geholt, solange die Seite sichtbar ist.

import { getJson, sendJson } from "./api.js";
import { el, formatDateTime } from "./dom.js";

const REFRESH_MS = 60_000;

export function notificationsButton() {
  const badge = el("span", { class: "notify-badge", hidden: true });
  const button = el(
    "button",
    { type: "button", class: "button-quiet notify-button", "aria-expanded": "false", "aria-haspopup": "true" },
    "Mitteilungen",
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

  async function open() {
    const messages = await getJson("/api/notifications");
    list.replaceChildren(
      ...(messages.length
        ? messages.map((message) =>
            el(
              "li",
              { class: message.read_at ? "" : "notify-unread" },
              el("span", {}, message.text),
              el("small", {}, formatDateTime(message.created_at)),
            ),
          )
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

  refresh();
  setInterval(refresh, REFRESH_MS);
  return box;
}
