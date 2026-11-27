// Anmeldung und eigenes Passwort (F10).
// app.js zeigt renderLogin(), solange niemand angemeldet ist, und renderFirstPassword(), solange
// das Konto noch ein Startpasswort hat. passwordForm() benutzt auch der Abschnitt „Mein Konto“.

import { getJson, sendJson } from "./api.js";
import { el, field, messageBox } from "./dom.js";

// So lang muss ein Passwort mindestens sein (wie MIN_PASSWORD_LENGTH im Backend).
const MIN_LENGTH = 8;

// Merkt sich im Browser, dass das Fenster mit den Anmeldedaten schon einmal gezeigt wurde.
const HINT_SEEN_KEY = "timbertalk.devhint.seen";

// Die Anmeldeseite. Nach erfolgreicher Anmeldung wird die Seite neu geladen.
// info kommt von GET /api/accounts/login-info: Demo-Modus (Knöpfe „Anmelden als …“) und – während
// der Entwicklung – die Anmeldedaten, die vor der ersten Anmeldung in einem Fenster erscheinen.
export function renderLogin(container, info = null) {
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
  if (info?.demo_mode) {
    form.append(demoChooser(info));
  }
  if (info?.hint) {
    const dialog = hintDialog(info.hint);
    form.append(
      el("p", { class: "form-hint" }, el("button", { type: "button", class: "login-hint-link", onclick: () => dialog.showModal() }, "Anmeldedaten für die Entwicklung anzeigen")),
      dialog,
    );
    // Vor der ersten Anmeldung in diesem Browser: von selbst öffnen.
    if (!recall(HINT_SEEN_KEY)) {
      remember(HINT_SEEN_KEY, "1");
      dialog.showModal();
      return;
    }
  }
  identifier.focus();
}

// Demo-Modus: mit einem Klick ohne Passwort als ein Konto anmelden.
function demoChooser(info) {
  const message = messageBox();
  return el(
    "section",
    { class: "login-demo" },
    el("h2", {}, "Demo-Modus"),
    el("p", { class: "form-hint" }, "Ohne Passwort anmelden als:"),
    el(
      "div",
      { class: "login-demo-people" },
      ...info.demo_people.map((person) =>
        el(
          "button",
          {
            type: "button",
            class: person.id === info.demo_account_id ? "button" : "button-quiet",
            onclick: async () => {
              try {
                await sendJson("POST", "/api/accounts/demo-login", { account_id: person.id });
                window.location.reload();
              } catch (error) {
                message.show(error.message, true);
              }
            },
          },
          `${person.display_name} (${person.role_label})`,
        ),
      ),
    ),
    message,
  );
}

// Fenster mit den Anmeldedaten – nur während der Entwicklung (TIMBERTALK_DEV_LOGIN_HINT).
function hintDialog(hint) {
  const rows = [];
  if (hint.initial_admin) {
    rows.push(["Erstes Konto", "admin", "admin"]);
  }
  rows.push(["Neue Konten", "ihr Anmeldename", hint.standard_password]);
  const close = el("button", { type: "button", class: "button" }, "Verstanden");
  const dialog = el(
    "dialog",
    { class: "accounts-dialog", "aria-labelledby": "login-hint-title" },
    el(
      "div",
      { class: "form accounts-form" },
      el("h2", { id: "login-hint-title" }, "Anmeldedaten (Entwicklung)"),
      el(
        "table",
        { class: "table" },
        el("thead", {}, el("tr", {}, ...["", "Anmeldename", "Passwort"].map((t) => el("th", { scope: "col" }, t)))),
        el(
          "tbody",
          {},
          ...rows.map(([label, user, password]) =>
            el("tr", {}, el("th", { scope: "row" }, label), el("td", {}, user), el("td", { class: "accounts-standard-value" }, password)),
          ),
        ),
      ),
      el(
        "p",
        { class: "form-hint" },
        "Bei der ersten Anmeldung muss man ein eigenes Passwort festlegen (außer im Demo-Modus). " +
          "Dieses Fenster gibt es nur während der Entwicklung; im Betrieb schaltet " +
          "TIMBERTALK_DEV_LOGIN_HINT=false es aus.",
      ),
      el("div", { class: "form-actions" }, close),
    ),
  );
  close.addEventListener("click", () => dialog.close());
  return dialog;
}

// Merken im Browser kann scheitern (z. B. im privaten Fenster) – dann eben nicht.
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

// Was die Anmeldeseite vorher wissen muss. Fehler sind nicht schlimm: dann normale Anmeldung.
export async function loadLoginInfo() {
  try {
    return await getJson("/api/accounts/login-info");
  } catch {
    return null;
  }
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
// Der Knopf ist immer bedienbar: Beim Klick wird geprüft, und eine Meldung sagt genau, was noch
// fehlt. (Ein grauer Knopf ohne Erklärung hilft niemandem – und Passwort-Manager füllen Felder
// oft aus, ohne dass der Browser „input“ meldet.)
export function passwordForm({ oldLabel = "Bisheriges Passwort", submitText, onDone }) {
  const oldPassword = el("input", {
    type: "password",
    name: "current-password",
    autocomplete: "current-password",
  });
  const newPassword = el("input", { type: "password", name: "new-password", autocomplete: "new-password" });
  const repeat = el("input", { type: "password", name: "new-password-repeat", autocomplete: "new-password" });
  const repeatHint = el("small", { class: "form-hint", "aria-live": "polite" });
  const button = el("button", { type: "submit", class: "button" }, submitText);
  const message = messageBox();

  const repeatField = field("Neues Passwort wiederholen", repeat);
  repeatField.append(repeatHint);

  // novalidate: Wir prüfen selbst und sagen es auf Deutsch in der Meldung darunter.
  const form = el(
    "form",
    { class: "form", novalidate: "" },
    field(oldLabel, oldPassword),
    field("Neues Passwort", newPassword, `Mindestens ${MIN_LENGTH} Zeichen.`),
    repeatField,
    el("div", { class: "form-actions" }, button),
    message,
  );

  // Was noch fehlt – oder null, wenn alles passt.
  function problem() {
    if (!oldPassword.value) {
      return `Bitte oben das ${oldLabel === "Startpasswort" ? "Startpasswort" : "bisherige Passwort"} eingeben.`;
    }
    if (newPassword.value.length < MIN_LENGTH) {
      return `Das neue Passwort braucht mindestens ${MIN_LENGTH} Zeichen.`;
    }
    if (newPassword.value !== repeat.value) {
      return "Die beiden neuen Passwörter sind nicht gleich.";
    }
    return null;
  }

  // Unterschied schon beim Tippen (oder Ausfüllen durch den Passwort-Manager) anzeigen.
  function hint() {
    repeatHint.textContent =
      repeat.value && newPassword.value !== repeat.value ? "Die beiden neuen Passwörter sind noch nicht gleich." : "";
  }
  for (const input of [oldPassword, newPassword, repeat]) {
    input.addEventListener("input", hint);
    input.addEventListener("change", hint);
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    message.clear();
    const missing = problem();
    if (missing) {
      message.show(missing, true);
      return;
    }
    button.disabled = true;
    try {
      const account = await sendJson("POST", "/api/accounts/me/password", {
        old_password: oldPassword.value,
        new_password: newPassword.value,
      });
      form.reset();
      hint();
      message.show("Das neue Passwort gilt ab sofort. Andere Geräte sind abgemeldet.");
      onDone?.(account);
    } catch (error) {
      message.show(error.message, true);
    }
    button.disabled = false;
  });

  return form;
}
