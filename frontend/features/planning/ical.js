// „Kalender aufs Handy holen“ im Reiter „Kalender“ (Feature F8): Ein Fenster, das man über das
// Menü „Mehr“ öffnet. Jede Person erzeugt sich dort einen geheimen Abo-Link für ihren eigenen
// Kalender; die Kalender-App des Handys holt die Termine dann selbst, etwa jede Stunde. Der Link
// wird nur direkt nach dem Erzeugen angezeigt; ein neuer Link macht den alten ungültig. Das Handy
// muss den Rechner im Betrieb erreichen (WLAN oder VPN).

import { getJson, sendJson } from "../../shared/api.js";
import { el, messageBox } from "../../shared/dom.js";
import { makeDialog } from "./dialog.js";

let dialog = null;

export function openIcal() {
  if (!dialog) {
    dialog = buildDialog();
  }
  dialog.open();
}

function buildDialog() {
  const box = makeDialog("Kalender aufs Handy holen");
  const message = messageBox();
  const linkBox = el("div", { class: "planning-ical-link", hidden: true });
  const createButton = el("button", { type: "button", class: "button" }, "Abo-Link erzeugen");
  const deleteButton = el("button", { type: "button", class: "button-quiet", hidden: true }, "Link ungültig machen");

  box.body.append(
    el(
      "p",
      { class: "form-hint" },
      "Mit dem Abo-Link zeigt die Kalender-App Ihres Handys Ihre Einsätze an und hält sie aktuell. " +
        "Der Link ist geheim wie ein Passwort – wer ihn hat, sieht Ihren Kalender.",
    ),
    el("div", { class: "form-actions" }, createButton, deleteButton),
    linkBox,
    message,
  );

  function showState(active) {
    createButton.textContent = active ? "Neuen Link erzeugen" : "Abo-Link erzeugen";
    deleteButton.hidden = !active;
  }

  function showLink(path) {
    const url = new URL(path, window.location.href);
    const webcal = `webcal://${url.host}${url.pathname}`;
    const field = el("input", { type: "text", readonly: "", value: url.href, "aria-label": "Abo-Link" });
    const copy = el("button", { type: "button", class: "button-quiet" }, "Kopieren");
    copy.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(url.href);
        message.show("Link kopiert.");
      } catch {
        field.select();
        message.show("Bitte den markierten Link selbst kopieren.");
      }
    });
    linkBox.replaceChildren(
      el("div", { class: "planning-ical-row" }, field, copy),
      el("p", {}, el("a", { href: webcal }, "Auf diesem Gerät abonnieren")),
      el(
        "p",
        { class: "form-hint" },
        "Dieser Link wird nur jetzt angezeigt. Auf dem iPhone: Einstellungen › Kalender › Accounts › " +
          "Account hinzufügen › Andere › Kalenderabo hinzufügen. Bei Android über Google Kalender im Browser.",
      ),
    );
    linkBox.hidden = false;
  }

  createButton.addEventListener("click", async () => {
    message.clear();
    try {
      const link = await sendJson("POST", "/api/planning/ical-link");
      showLink(link.path);
      showState(true);
      message.show("Neuer Link erzeugt. Ein älterer Link funktioniert nicht mehr.");
    } catch (error) {
      message.show(error.message, true);
    }
  });

  deleteButton.addEventListener("click", async () => {
    if (!window.confirm("Abo-Link ungültig machen? Der Kalender auf dem Handy wird dann nicht mehr aktualisiert.")) {
      return;
    }
    await sendJson("DELETE", "/api/planning/ical-link");
    linkBox.hidden = true;
    showState(false);
    message.show("Der Link ist ungültig.");
  });

  const open = box.open;
  box.open = () => {
    message.clear();
    linkBox.hidden = true;
    getJson("/api/planning/ical-link")
      .then((state) => showState(state.active))
      .catch((error) => message.show(error.message, true));
    open();
  };
  return box;
}
