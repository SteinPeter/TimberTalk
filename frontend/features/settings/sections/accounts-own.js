// Der Abschnitt „Mein Konto“ im Reiter „Einstellungen“ (Feature F10):
// zeigt das eigene Konto mit Foto, lässt jeden sein Foto ändern und sein eigenes Passwort.
// Die Rolle steht hier nicht – sie dient nur dem Admin zur Einordnung („Benutzerkonten“).
// Eingetragen ist der Abschnitt in settings/sections.js.

import { sendJson } from "../../../shared/api.js";
import { avatar, el, messageBox, photoFromFile } from "../../../shared/dom.js";
import { passwordForm } from "../../../shared/login.js";
import { currentAccount } from "../../../shared/session.js";

export const id = "accounts-own";
export const title = "Mein Konto";

export function render(container) {
  const me = currentAccount();
  const photoBox = el("div", { class: "accounts-photo-preview" });
  const photoInput = el("input", { type: "file", accept: "image/*", class: "accounts-photo-input" });
  const removeButton = el("button", { type: "button", class: "button-quiet" }, "Foto entfernen");
  const photoMessage = messageBox();

  const rows = [
    ["Name", me.display_name],
    ["Anmeldename", me.username],
    ["Personalnummer", me.personnel_number ?? "–"],
  ];
  container.append(
    el(
      "div",
      { class: "accounts-photo-row" },
      photoBox,
      el(
        "div",
        { class: "form-actions" },
        el("label", { class: "button-quiet accounts-photo-pick" }, "Foto wählen …", photoInput),
        removeButton,
      ),
    ),
    photoMessage,
    el(
      "dl",
      { class: "status" },
      ...rows.flatMap(([label, value]) => [el("dt", {}, label), el("dd", {}, value)]),
    ),
    el("h2", { class: "form-title" }, "Passwort ändern"),
    passwordForm({ submitText: "Passwort ändern" }),
  );

  // Zeigt das Foto hier und oben rechts in der Leiste.
  function showPhoto() {
    photoBox.replaceChildren(avatar(me, "large"));
    removeButton.hidden = !me.photo;
    document.querySelector(".account-button .avatar")?.replaceWith(avatar(me, "small"));
  }

  async function save(photo) {
    photoMessage.clear();
    try {
      const saved = await sendJson("PUT", "/api/accounts/me/photo", { photo });
      me.photo = saved.photo;
      showPhoto();
      photoMessage.show(photo ? "Foto gespeichert." : "Foto entfernt.");
    } catch (error) {
      photoMessage.show(error.message, true);
    }
  }

  photoInput.addEventListener("change", async () => {
    const file = photoInput.files[0];
    if (!file) {
      return;
    }
    try {
      await save(await photoFromFile(file));
    } catch (error) {
      photoMessage.show(error.message, true);
    }
    photoInput.value = "";
  });
  removeButton.addEventListener("click", () => save(null));

  showPhoto();
}
