// Der Abschnitt „Benutzerkonten“ im Reiter „Einstellungen“ (Feature F10):
// Konten anlegen, ändern, sperren und Passwörter zurücksetzen. Nur mit dem Recht
// „accounts.manage“ sichtbar (Chef und Admin). Eingetragen in settings/sections.js.
//
// Das Startpasswort zeigt die Seite genau einmal – nach dem Anlegen oder Zurücksetzen. Danach
// kennt es niemand mehr; gespeichert ist nur sein Hash.

import { getJson, sendJson } from "../../../shared/api.js";
import { el, field, formatDateTime, messageBox } from "../../../shared/dom.js";
import { currentAccount } from "../../../shared/session.js";

export const id = "accounts-manage";
export const title = "Benutzerkonten";
export const permission = "accounts.manage";

export function render(container) {
  const me = currentAccount();
  let roles = [];
  let editing = null; // das Konto, das gerade bearbeitet wird – oder null beim Anlegen

  // --- Liste ---
  const tableBody = el("tbody");
  const table = el(
    "div",
    { class: "table-scroll" },
    el(
      "table",
      { class: "table" },
      el(
        "thead",
        {},
        el(
          "tr",
          {},
          ...["Name", "Rolle", "Status", "Zuletzt angemeldet", ""].map((text) =>
            el("th", { scope: "col" }, text),
          ),
        ),
      ),
      tableBody,
    ),
  );
  const listMessage = messageBox();

  // --- Formular: anlegen oder bearbeiten ---
  const formTitle = el("h2", {}, "Neues Konto");
  const nameInput = el("input", { type: "text", autocomplete: "off", required: "" });
  const usernameInput = el("input", {
    type: "text",
    autocomplete: "off",
    autocapitalize: "none",
    spellcheck: "false",
    required: "",
  });
  const numberInput = el("input", { type: "text", autocomplete: "off", inputmode: "numeric" });
  const roleSelect = el("select", { required: "" });
  const startInput = el("input", { type: "text", autocomplete: "off", spellcheck: "false" });
  const startField = field(
    "Startpasswort",
    startInput,
    "Leer lassen: TimberTalk denkt sich eines aus. Bei der ersten Anmeldung wird es ersetzt.",
  );
  const lockedInput = el("input", { type: "checkbox" });
  const lockedField = el(
    "label",
    { class: "form-check" },
    lockedInput,
    el("span", {}, "Konto gesperrt – Anmeldung nicht möglich"),
  );
  const saveButton = el("button", { type: "submit", class: "button", disabled: true }, "Konto anlegen");
  const resetButton = el("button", { type: "button", class: "button-quiet" }, "Passwort zurücksetzen");
  const cancelButton = el("button", { type: "button", class: "button-quiet" }, "Abbrechen");
  const formMessage = messageBox();
  const secret = el("div", { class: "accounts-secret", role: "status", hidden: true });

  const form = el(
    "form",
    { class: "form", novalidate: "" },
    formTitle,
    el(
      "div",
      { class: "form-row" },
      field("Name", nameInput, "Wie er in Listen und im Kalender steht."),
      field("Anmeldename", usernameInput, "Kleinbuchstaben, z. B. m.berger"),
    ),
    el(
      "div",
      { class: "form-row" },
      field("Personalnummer", numberInput, "Freiwillig. Damit kann man sich auch anmelden."),
      field("Rolle", roleSelect),
    ),
    startField,
    lockedField,
    el("div", { class: "form-actions" }, saveButton, resetButton, cancelButton),
    formMessage,
    secret,
  );

  container.append(table, listMessage, form);

  // --- Anzeigen ---

  function status(account) {
    if (!account.active) {
      return "Gesperrt";
    }
    return account.must_change_password ? "Startpasswort" : "Aktiv";
  }

  function showAccounts(accounts) {
    tableBody.replaceChildren(
      ...accounts.map((account) =>
        el(
          "tr",
          {},
          // Unter dem Namen klein: womit sich die Person anmeldet.
          el(
            "td",
            {},
            account.display_name,
            el(
              "small",
              { class: "accounts-login" },
              account.personnel_number
                ? `${account.username} · Nr. ${account.personnel_number}`
                : account.username,
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
              {
                type: "button",
                class: "button-quiet",
                "aria-label": `${account.display_name} bearbeiten`,
                onclick: () => startEditing(account),
              },
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
      ...roles.map((role) =>
        el(
          "option",
          { value: role.role, disabled: role.role === "admin" && me.role !== "admin" },
          role.label,
        ),
      ),
    );
    roleSelect.value = "journeyman";
  }

  // Zeigt das Startpasswort einmal groß an, damit man es abschreiben oder weitergeben kann.
  function showSecret(name, password) {
    secret.replaceChildren(
      el("p", {}, `Startpasswort für ${name}:`),
      el("p", { class: "accounts-secret-value" }, password),
      el(
        "p",
        { class: "form-hint" },
        "Bitte jetzt weitergeben. Es wird nur dieses eine Mal angezeigt und bei der ersten " +
          "Anmeldung durch ein eigenes Passwort ersetzt.",
      ),
    );
    secret.hidden = false;
  }

  function startEditing(account) {
    editing = account;
    formTitle.textContent = `Konto bearbeiten: ${account.display_name}`;
    nameInput.value = account.display_name;
    usernameInput.value = account.username;
    usernameInput.disabled = true;
    numberInput.value = account.personnel_number ?? "";
    roleSelect.value = account.role;
    lockedInput.checked = !account.active;
    // Das eigene Konto kann man nicht sperren und seine Rolle nicht ändern.
    const self = account.id === me.id;
    lockedInput.disabled = self;
    roleSelect.disabled = self;
    startField.hidden = true;
    lockedField.hidden = false;
    resetButton.hidden = false;
    cancelButton.hidden = false;
    saveButton.textContent = "Änderungen speichern";
    formMessage.clear();
    secret.hidden = true;
    updateButton();
    form.scrollIntoView({ behavior: "smooth", block: "start" });
    nameInput.focus({ preventScroll: true });
  }

  function startCreating() {
    editing = null;
    form.reset();
    formTitle.textContent = "Neues Konto";
    usernameInput.disabled = false;
    roleSelect.disabled = false;
    roleSelect.value = "journeyman";
    startField.hidden = false;
    lockedField.hidden = true;
    resetButton.hidden = true;
    cancelButton.hidden = true;
    saveButton.textContent = "Konto anlegen";
    updateButton();
  }

  function updateButton() {
    const ok = nameInput.value.trim() && (editing || usernameInput.value.trim());
    saveButton.disabled = !ok;
  }

  async function load() {
    try {
      const [accountList, matrix] = await Promise.all([
        getJson("/api/accounts"),
        getJson("/api/accounts/roles"),
      ]);
      roles = matrix.roles;
      showAccounts(accountList);
    } catch (error) {
      listMessage.show(error.message, true);
    }
  }

  async function reloadList() {
    try {
      showAccounts(await getJson("/api/accounts"));
    } catch (error) {
      listMessage.show(error.message, true);
    }
  }

  // --- Bedienen ---

  nameInput.addEventListener("input", updateButton);
  usernameInput.addEventListener("input", updateButton);
  cancelButton.addEventListener("click", startCreating);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    formMessage.clear();
    secret.hidden = true;
    try {
      if (editing) {
        const saved = await sendJson("PUT", `/api/accounts/${editing.id}`, {
          display_name: nameInput.value,
          role: roleSelect.value,
          personnel_number: numberInput.value,
          active: !lockedInput.checked,
        });
        startCreating();
        formMessage.show(`Gespeichert: ${saved.display_name}.`);
      } else {
        const created = await sendJson("POST", "/api/accounts", {
          display_name: nameInput.value,
          username: usernameInput.value,
          role: roleSelect.value,
          personnel_number: numberInput.value,
          start_password: startInput.value || null,
        });
        startCreating();
        formMessage.show(`Konto angelegt: ${created.account.display_name}.`);
        showSecret(created.account.display_name, created.start_password);
      }
      await reloadList();
    } catch (error) {
      formMessage.show(error.message, true);
    }
  });

  resetButton.addEventListener("click", async () => {
    const account = editing;
    const sure = window.confirm(
      `Passwort von ${account.display_name} zurücksetzen?\n\n` +
        "Das bisherige Passwort gilt dann nicht mehr, und das Konto wird auf allen Geräten " +
        "abgemeldet.",
    );
    if (!sure) {
      return;
    }
    formMessage.clear();
    try {
      const answer = await sendJson("POST", `/api/accounts/${account.id}/reset-password`, {});
      startCreating();
      formMessage.show(`Passwort von ${account.display_name} zurückgesetzt.`);
      showSecret(account.display_name, answer.start_password);
      await reloadList();
    } catch (error) {
      formMessage.show(error.message, true);
    }
  });

  return load().then(() => {
    showRoles();
    startCreating();
  });
}
