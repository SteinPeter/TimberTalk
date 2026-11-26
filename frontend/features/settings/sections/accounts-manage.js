// Der Abschnitt „Benutzerkonten“ im Reiter „Einstellungen“ (Feature F10):
// Konten anlegen, ändern, sperren, Fotos setzen und Passwörter zurücksetzen. Nur mit dem Recht
// „accounts.manage“ sichtbar (Admin, und wem er dieses Recht gibt). Eingetragen in
// settings/sections.js.
//
// Auf der Seite steht nur die Liste. Anlegen und Bearbeiten öffnen ein Fenster. Neue Konten und
// zurückgesetzte Passwörter bekommen immer das Standardpasswort – es steht oben und lässt sich
// ändern. Bei der ersten Anmeldung muss jede Person es durch ein eigenes ersetzen.

import { getJson, sendJson } from "../../../shared/api.js";
import { avatar, el, field, formatDateTime, messageBox, photoFromFile } from "../../../shared/dom.js";
import { currentAccount } from "../../../shared/session.js";

export const id = "accounts-manage";
export const title = "Benutzerkonten";
export const permission = "accounts.manage";

export function render(container) {
  const me = currentAccount();
  let roles = [];
  let editing = null; // das Konto, das gerade bearbeitet wird – oder null beim Anlegen
  let photo; // undefined: Foto unverändert, null: entfernen, Text: neues Foto

  // --- Standardpasswort ---
  const standardValue = el("strong", { class: "accounts-standard-value" });
  const standardInput = el("input", { type: "text", autocomplete: "off", spellcheck: "false", "aria-label": "Neues Standardpasswort" });
  const standardEdit = el(
    "form",
    { class: "accounts-standard-edit", hidden: true, novalidate: "" },
    standardInput,
    el("button", { type: "submit", class: "button" }, "Speichern"),
    el("button", { type: "button", class: "button-quiet", onclick: () => toggleStandard(false) }, "Abbrechen"),
  );
  const standardButton = el("button", { type: "button", class: "button-quiet", onclick: () => toggleStandard(true) }, "Ändern");
  const standardMessage = messageBox();
  const standardBox = el(
    "div",
    { class: "accounts-standard" },
    el("p", {}, "Standardpasswort für neue Konten: ", standardValue, " ", standardButton),
    standardEdit,
    el("p", { class: "form-hint" }, "Bei der ersten Anmeldung muss jede Person es durch ein eigenes Passwort ersetzen."),
    standardMessage,
  );

  // --- Liste ---
  const newButton = el("button", { type: "button", class: "button" }, "+ Neues Konto");
  const tableBody = el("tbody");
  const table = el(
    "div",
    { class: "table-scroll" },
    el(
      "table",
      { class: "table" },
      el("thead", {}, el("tr", {}, ...["Name", "Rolle", "Status", "Zuletzt angemeldet", ""].map((text) => el("th", { scope: "col" }, text)))),
      tableBody,
    ),
  );
  const listMessage = messageBox();

  // --- Fenster: anlegen oder bearbeiten ---
  const formTitle = el("h2", { id: "accounts-dialog-title" });
  const photoPreview = el("div", { class: "accounts-photo-preview" });
  const photoInput = el("input", { type: "file", accept: "image/*", class: "accounts-photo-input" });
  const photoRemove = el("button", { type: "button", class: "button-quiet" }, "Foto entfernen");
  const photoRow = el(
    "div",
    { class: "accounts-photo-row" },
    photoPreview,
    el("div", { class: "form-actions" }, el("label", { class: "button-quiet accounts-photo-pick" }, "Foto wählen …", photoInput), photoRemove),
  );
  const nameInput = el("input", { type: "text", autocomplete: "off", required: "" });
  const usernameInput = el("input", { type: "text", autocomplete: "off", autocapitalize: "none", spellcheck: "false", required: "" });
  const numberInput = el("input", { type: "text", autocomplete: "off", inputmode: "numeric" });
  const roleSelect = el("select", { required: "" });
  const lockedInput = el("input", { type: "checkbox" });
  const lockedField = el("label", { class: "form-check" }, lockedInput, el("span", {}, "Konto gesperrt – Anmeldung nicht möglich"));
  const saveButton = el("button", { type: "submit", class: "button", disabled: true }, "Konto anlegen");
  const resetButton = el("button", { type: "button", class: "button-quiet" }, "Passwort zurücksetzen");
  const cancelButton = el("button", { type: "button", class: "button-quiet" }, "Abbrechen");
  const formMessage = messageBox();

  const form = el(
    "form",
    { class: "form accounts-form", novalidate: "" },
    formTitle,
    photoRow,
    el(
      "div",
      { class: "form-row" },
      field("Name", nameInput, "Vor- und Nachname, z. B. Max Berger."),
      field("Anmeldename", usernameInput, "Kleinbuchstaben, z. B. m.berger"),
    ),
    el(
      "div",
      { class: "form-row" },
      field("Personalnummer", numberInput, "Freiwillig. Damit kann man sich auch anmelden."),
      field("Rolle", roleSelect),
    ),
    lockedField,
    formMessage,
    el("div", { class: "form-actions" }, saveButton, cancelButton, resetButton),
  );
  const dialog = el("dialog", { class: "accounts-dialog", "aria-labelledby": "accounts-dialog-title" }, form);
  cancelButton.addEventListener("click", () => dialog.close());

  container.append(standardBox, el("div", { class: "form-actions" }, newButton), listMessage, table, dialog);

  // --- Anzeigen ---

  function status(account) {
    if (!account.active) {
      return "Gesperrt";
    }
    // Kurz gesperrt nach zu vielen falschen Passwörtern; „Passwort zurücksetzen“ hebt das auf.
    if (account.locked_until && new Date(account.locked_until) > new Date()) {
      const until = new Date(account.locked_until).toLocaleTimeString("de-DE", { timeStyle: "short" });
      return `Fehlversuche – gesperrt bis ${until}`;
    }
    return account.must_change_password ? "Standardpasswort" : "Aktiv";
  }

  function showAccounts(accounts) {
    tableBody.replaceChildren(
      ...accounts.map((account) =>
        el(
          "tr",
          {},
          // Foto, Name und darunter klein, womit sich die Person anmeldet.
          el(
            "td",
            {},
            el(
              "div",
              { class: "accounts-person" },
              avatar(account, "medium"),
              el(
                "span",
                {},
                account.display_name,
                el(
                  "small",
                  { class: "accounts-login" },
                  account.personnel_number ? `${account.username} · Nr. ${account.personnel_number}` : account.username,
                ),
              ),
            ),
          ),
          el("td", {}, account.role_label),
          el("td", {}, status(account)),
          el("td", {}, formatDateTime(account.last_login_at)),
          el(
            "td",
            {},
            el(
              "button",
              { type: "button", class: "button-quiet", "aria-label": `${account.display_name} bearbeiten`, onclick: () => openForm(account) },
              "Bearbeiten",
            ),
          ),
        ),
      ),
    );
  }

  // Nur ein Admin vergibt die Rolle Admin (das Backend prüft das ebenso).
  function showRoles() {
    roleSelect.replaceChildren(
      ...roles.map((role) => el("option", { value: role.role, disabled: role.role === "admin" && me.role !== "admin" }, role.label)),
    );
  }

  function showPhoto(person) {
    photoPreview.replaceChildren(avatar(person, "large"));
    photoRemove.hidden = !person.photo;
  }

  // Öffnet das Fenster – mit Konto zum Bearbeiten, ohne zum Anlegen.
  function openForm(account = null) {
    editing = account;
    photo = undefined;
    form.reset();
    formMessage.clear();
    formTitle.textContent = account ? `Konto bearbeiten: ${account.display_name}` : "Neues Konto";
    nameInput.value = account?.display_name ?? "";
    usernameInput.value = account?.username ?? "";
    usernameInput.disabled = Boolean(account);
    numberInput.value = account?.personnel_number ?? "";
    roleSelect.value = account?.role ?? "journeyman";
    lockedInput.checked = account ? !account.active : false;
    // Das eigene Konto kann man nicht sperren und seine Rolle nicht ändern.
    const self = account?.id === me.id;
    lockedInput.disabled = self;
    roleSelect.disabled = self;
    lockedField.hidden = !account;
    resetButton.hidden = !account;
    saveButton.textContent = account ? "Änderungen speichern" : "Konto anlegen";
    showPhoto(account ?? { display_name: "?", photo: null });
    updateButton();
    dialog.showModal();
    nameInput.focus();
  }

  function updateButton() {
    saveButton.disabled = !(nameInput.value.trim() && (editing || usernameInput.value.trim()));
  }

  function toggleStandard(open) {
    standardEdit.hidden = !open;
    standardButton.hidden = open;
    standardMessage.clear();
    if (open) {
      standardInput.value = standardValue.textContent;
      standardInput.focus();
    }
  }

  async function loadList() {
    try {
      showAccounts(await getJson("/api/accounts"));
    } catch (error) {
      listMessage.show(error.message, true);
    }
  }

  // --- Bedienen ---

  newButton.addEventListener("click", () => openForm());
  nameInput.addEventListener("input", updateButton);
  usernameInput.addEventListener("input", updateButton);

  photoInput.addEventListener("change", async () => {
    const file = photoInput.files[0];
    if (!file) {
      return;
    }
    try {
      photo = await photoFromFile(file);
      showPhoto({ display_name: nameInput.value || "?", photo });
    } catch (error) {
      formMessage.show(error.message, true);
    }
  });
  photoRemove.addEventListener("click", () => {
    photo = null;
    showPhoto({ display_name: nameInput.value || "?", photo: null });
  });

  standardEdit.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const saved = await sendJson("PUT", "/api/accounts/standard-password", { start_password: standardInput.value });
      standardValue.textContent = saved.start_password;
      toggleStandard(false);
      standardMessage.show("Gespeichert. Es gilt für alle Konten, die ab jetzt angelegt oder zurückgesetzt werden.");
    } catch (error) {
      standardMessage.show(error.message, true);
    }
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    formMessage.clear();
    try {
      let saved;
      let text;
      if (editing) {
        saved = await sendJson("PUT", `/api/accounts/${editing.id}`, {
          display_name: nameInput.value,
          role: roleSelect.value,
          personnel_number: numberInput.value,
          active: !lockedInput.checked,
        });
        text = `Gespeichert: ${saved.display_name}.`;
      } else {
        const created = await sendJson("POST", "/api/accounts", {
          display_name: nameInput.value,
          username: usernameInput.value,
          role: roleSelect.value,
          personnel_number: numberInput.value,
        });
        saved = created.account;
        text = `Konto angelegt: ${saved.display_name}. Erste Anmeldung mit „${saved.username}“ und dem Standardpasswort „${created.start_password}“.`;
      }
      if (photo !== undefined) {
        await sendJson("PUT", `/api/accounts/${saved.id}/photo`, { photo });
      }
      dialog.close();
      await loadList();
      listMessage.show(text);
    } catch (error) {
      formMessage.show(error.message, true);
    }
  });

  resetButton.addEventListener("click", async () => {
    const account = editing;
    const sure = window.confirm(
      `Passwort von ${account.display_name} zurücksetzen?\n\n` +
        "Es gilt dann wieder das Standardpasswort, und das Konto wird auf allen Geräten abgemeldet.",
    );
    if (!sure) {
      return;
    }
    try {
      const answer = await sendJson("POST", `/api/accounts/${account.id}/reset-password`, {});
      dialog.close();
      await loadList();
      listMessage.show(`Passwort von ${account.display_name} zurückgesetzt – jetzt gilt das Standardpasswort „${answer.start_password}“.`);
    } catch (error) {
      formMessage.show(error.message, true);
    }
  });

  return Promise.all([getJson("/api/accounts/roles"), getJson("/api/accounts/standard-password")])
    .then(([matrix, standard]) => {
      roles = matrix.roles;
      standardValue.textContent = standard.start_password;
      showRoles();
    })
    .then(loadList)
    .catch((error) => listMessage.show(error.message, true));
}
