// Baut die Reiterleiste aus reiter.js und schaltet zwischen den Reitern um.
// Was ein Reiter zeigt, steht nicht hier, sondern in seiner Datei unter features/.
// Nur DOM, kein Framework, kein Bauschritt.
//
// Vorher wird geprüft, wer angemeldet ist (F10): Ohne Anmeldung zeigt die Seite nur die
// Anmeldung, mit Startpasswort nur „eigenes Passwort festlegen“. Ein Reiter mit `permission`
// erscheint nur, wenn das Konto dieses Recht hat.

import { REITER } from "./reiter.js";
import { sendJson } from "./shared/api.js";
import { avatar, el, lastName, menuButton, openSettings } from "./shared/dom.js";
import { loadLoginInfo, renderFirstPassword, renderLogin } from "./shared/login.js";
import { notificationsButton } from "./shared/notifications.js";
import { can, loadAccount, logout } from "./shared/session.js";

const DEFAULT_TAB = "start";
const header = document.querySelector(".topbar");
const brand = document.querySelector(".brand");
const nav = document.querySelector(".tabs");
const main = document.querySelector("main");

// --- Anmeldung ------------------------------------------------------------------

let account = null;
let reachable = true;
try {
  account = await loadAccount();
} catch (error) {
  // Backend nicht erreichbar: die Reiter trotzdem aufbauen, „Start“ zeigt dann den Grund.
  reachable = false;
  console.error("Anmeldung konnte nicht geprüft werden:", error);
}

if (reachable && account === null) {
  // Demo-Modus: automatisch als das voreingestellte Konto anmelden – außer man hat sich gerade
  // abgemeldet (dann soll man ein anderes Konto wählen können).
  const info = await loadLoginInfo();
  if (info?.demo_mode && info.demo_account_id && !justLoggedOut()) {
    try {
      await sendJson("POST", "/api/accounts/demo-login", {});
      window.location.reload();
    } catch {
      showLogin(info);
    }
  } else {
    showLogin(info);
  }
} else if (account?.must_change_password) {
  nav.hidden = true;
  header.append(accountBox(account));
  renderFirstPassword(main, account);
} else {
  if (account) {
    header.append(accountBox(account));
    header.querySelector(".account").prepend(notificationsButton());
  }
  startTabs(REITER.filter((reiter) => !reiter.permission || can(reiter.permission)));
}

function showLogin(info) {
  nav.hidden = true;
  renderLogin(main, info);
}

function justLoggedOut() {
  try {
    return sessionStorage.getItem("timbertalk.loggedOut") === "1";
  } catch {
    return false;
  }
}

// Rechts in der Leiste: Foto (oder Initialen) mit dem Nachnamen darunter. Ein Klick öffnet ein
// kleines Menü mit „Mein Konto“ und „Abmelden“. Die Rolle steht hier bewusst nicht – sie sieht
// nur, wer Konten verwaltet (Einstellungen → Benutzerkonten).
function accountBox(me) {
  const button = el(
    "button",
    { type: "button", class: "account-button", "aria-label": `Konto von ${me.display_name}` },
    avatar(me, "small"),
    el("span", { class: "account-name" }, lastName(me.display_name)),
  );
  const items = [el("p", { class: "menu-title" }, me.display_name)];
  if (!me.must_change_password) {
    items.push({ label: "Mein Konto", onSelect: () => openSettings("accounts-own") });
  }
  items.push({ label: "Abmelden", onSelect: logout });
  return el("div", { class: "account" }, menuButton(button, items));
}

// --- Gerüst aufbauen ----------------------------------------------------------

function startTabs(tabs) {
  // Für jeden Reiter ein Link in der Leiste und ein leerer Bereich in <main>. „Start“ bekommt
  // keinen eigenen Link – dorthin führt das Logo oben links.
  for (const reiter of tabs) {
    if (reiter.id !== DEFAULT_TAB) {
      const link = document.createElement("a");
      link.href = `#${reiter.id}`;
      link.textContent = reiter.title;
      nav.append(link);
    }

    const panel = document.createElement("section");
    panel.id = reiter.id;
    panel.className = "panel";
    panel.hidden = true;
    main.append(panel);
  }

  // Reiter, deren render() schon aufgerufen wurde. Jeder Bereich wird nur einmal aufgebaut.
  const rendered = new Set();

  // Ruft render() des Reiters beim ersten Öffnen auf. Geht dabei etwas schief, zeigt nur
  // dieser Bereich eine Meldung – die anderen Reiter funktionieren weiter.
  async function renderOnce(reiter, panel) {
    if (rendered.has(reiter.id)) {
      return;
    }
    rendered.add(reiter.id);
    try {
      await reiter.render(panel);
    } catch (error) {
      console.error(`Reiter "${reiter.id}" konnte nicht aufgebaut werden:`, error);
      const heading = document.createElement("h1");
      heading.textContent = reiter.title;
      const message = document.createElement("p");
      message.className = "empty";
      message.textContent = `Dieser Bereich konnte nicht geladen werden (${error.message}).`;
      panel.replaceChildren(heading, message);
    }
  }

  // --- Umschalten ---------------------------------------------------------------

  // Zeigt den Bereich, dessen Name hinter dem # in der Adresse steht (z. B. #planning).
  // Fehlt der Name oder gibt es ihn nicht, wird "start" gezeigt.
  function showTabFromAddress() {
    const wanted = window.location.hash.slice(1);
    const known = tabs.some((reiter) => reiter.id === wanted);
    const current = known ? wanted : DEFAULT_TAB;

    for (const reiter of tabs) {
      const panel = document.getElementById(reiter.id);
      panel.hidden = reiter.id !== current;
      if (reiter.id === current) {
        renderOnce(reiter, panel);
      }
    }
    for (const link of [brand, ...nav.querySelectorAll("a")]) {
      if (link.getAttribute("href") === `#${current}`) {
        link.setAttribute("aria-current", "page");
      } else {
        link.removeAttribute("aria-current");
      }
    }
  }

  // Ein Klick auf einen Reiter ändert nur das # in der Adresse; der Browser meldet das
  // mit "hashchange". Dasselbe passiert bei Zurück und Vor.
  window.addEventListener("hashchange", showTabFromAddress);
  showTabFromAddress();
}

// --- Textfelder wachsen mit --------------------------------------------------------

// Mehrzeilige Felder (<textarea>) werden so hoch wie ihr Text, damit man alles auf einen Blick
// sieht. Neuere Browser können das selbst (CSS „field-sizing: content“ in style.css); für alle
// anderen passt diese Funktion die Höhe beim Tippen an.
if (!CSS.supports("field-sizing", "content")) {
  document.addEventListener("input", (event) => {
    const field = event.target;
    if (field instanceof HTMLTextAreaElement) {
      field.style.height = "auto";
      field.style.height = `${field.scrollHeight + 2}px`;
    }
  });
}
