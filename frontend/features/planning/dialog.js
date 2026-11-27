// Ein kleines Fenster (<dialog>) für den Reiter „Kalender“: Überschrift, Inhalt und unten
// „Schließen“. So erscheinen Dinge, die man nicht ständig braucht (Kalender-Abo), erst wenn
// man sie aufruft.

import { el } from "../../shared/dom.js";

let counter = 0;

export function makeDialog(title) {
  counter += 1;
  const headingId = `planning-dialog-${counter}`;
  const heading = el("h2", { id: headingId }, title);
  const body = el("div", { class: "planning-dialog-body" });
  const closeButton = el("button", { type: "button", class: "button-quiet" }, "Schließen");
  const node = el(
    "dialog",
    { class: "planning-dialog", "aria-labelledby": headingId },
    el("div", { class: "form planning-form" }, heading, body, el("div", { class: "form-actions" }, closeButton)),
  );
  closeButton.addEventListener("click", () => node.close());
  document.body.append(node);
  return {
    node,
    body,
    heading,
    open: () => node.showModal(),
    close: () => node.close(),
  };
}
