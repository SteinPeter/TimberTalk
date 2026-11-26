// Anmeldung und eigenes Passwort (F10).
// app.js zeigt renderLogin(), solange niemand angemeldet ist, und renderFirstPassword(), solange
// das Konto noch ein Startpasswort hat. passwordForm() benutzt auch der Abschnitt „Mein Konto“.

import { sendJson } from "./api.js";
import { el, field, messageBox } from "./dom.js";

// So lang muss ein Passwort mindestens sein (wie MIN_PASSWORD_LENGTH im Backend).
const MIN_LENGTH = 8;

// Die Anmeldeseite. Nach erfolgreicher Anmeldung wird die Seite neu geladen.
export function renderLogin(container) {
  const identifier = el("input", {
    type: "text",
    name: "username",
    autocomplete: "username",
    autocapitalize: "none",
    spellcheck: "false",
    required: "",
  });
  const password = el("input", {
    type: "password",
    name: "password",
    autocomplete: "current-password",
    required: "",
  });
  const button = el("button", { type: "submit", class: "button" }, "Anmelden");
  const message = messageBox();

  const form = el(
    "form",
    { class: "form login-card" },
    el("h1", {}, "Anmelden"),
    el(
      "p",
      { class: "form-hint" },
      "Mit Ihrem Anmeldenamen oder Ihrer Personalnummer. Passwort vergessen? " +
        "Der Admin setzt es zurück.",
    ),
    field("Anmeldename oder Personalnummer", identifier),
    field("Passwort", password),
    el("div", { class: "form-actions" }, button),
    message,
  );

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    message.clear();
    button.disabled = true;
    try {
      await sendJson("POST", "/api/accounts/login", {
        identifier: identifier.value,
        password: password.value,
      });
      window.location.reload();
    } catch (error) {
      message.show(error.message, true);
      password.value = "";
      password.focus();
      button.disabled = false;
    }
  });

  container.replaceChildren(form);
  identifier.focus();
}

// Erste Anmeldung mit Startpasswort: erst ein eigenes Passwort festlegen, dann geht es weiter.
export function renderFirstPassword(container, account) {
  const form = passwordForm({
    oldLabel: "Startpasswort",
    submitText: "Passwort festlegen und weiter",
    onDone: () => window.location.reload(),
  });
  container.replaceChildren(
    el(
      "div",
      { class: "login-card" },
      el("h1", {}, `Willkommen, ${account.display_name}`),
      el(
        "p",
        { class: "form-hint" },
        `Ihr Konto hat noch ein Startpasswort. Legen Sie jetzt ein eigenes fest ` +
          `(mindestens ${MIN_LENGTH} Zeichen). Danach kennt es nur noch Sie.`,
      ),
      form,
    ),
  );
  form.querySelector("input").focus();
}

// Formular „Passwort ändern“: bisheriges Passwort, neues Passwort, neues Passwort wiederholen.
// Der Knopf wird erst aktiv, wenn das neue Passwort lang genug ist und beide gleich sind.
export function passwordForm({ oldLabel = "Bisheriges Passwort", submitText, onDone }) {
  const oldPassword = el("input", {
    type: "password",
    autocomplete: "current-password",
    required: "",
  });
  const newPassword = el("input", {
    type: "password",
    autocomplete: "new-password",
    minlength: String(MIN_LENGTH),
    required: "",
  });
  const repeat = el("input", { type: "password", autocomplete: "new-password", required: "" });
  const repeatHint = el("small", { class: "form-hint", "aria-live": "polite" });
  const button = el("button", { type: "submit", class: "button", disabled: true }, submitText);
  const message = messageBox();

  const repeatField = field("Neues Passwort wiederholen", repeat);
  repeatField.append(repeatHint);

  const form = el(
    "form",
    { class: "form" },
    field(oldLabel, oldPassword),
    field("Neues Passwort", newPassword, `Mindestens ${MIN_LENGTH} Zeichen.`),
    repeatField,
    el("div", { class: "form-actions" }, button),
    message,
  );

  // Während man tippt: Knopf freigeben, sobald alles passt; Unterschied gleich anzeigen.
  function check() {
    const longEnough = newPassword.value.length >= MIN_LENGTH;
    const same = newPassword.value === repeat.value;
    repeatHint.textContent =
      repeat.value && !same ? "Die beiden neuen Passwörter sind noch nicht gleich." : "";
    button.disabled = !(oldPassword.value && longEnough && same);
  }
  for (const input of [oldPassword, newPassword, repeat]) {
    input.addEventListener("input", check);
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    message.clear();
    button.disabled = true;
    try {
      const account = await sendJson("POST", "/api/accounts/me/password", {
        old_password: oldPassword.value,
        new_password: newPassword.value,
      });
      form.reset();
      message.show("Das neue Passwort gilt ab sofort. Andere Geräte sind abgemeldet.");
      onDone?.(account);
    } catch (error) {
      message.show(error.message, true);
    }
    check();
  });

  return form;
}
