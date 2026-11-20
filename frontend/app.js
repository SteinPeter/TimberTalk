// Baut die Reiterleiste aus reiter.js und schaltet zwischen den Reitern um.
// Was ein Reiter zeigt, steht nicht hier, sondern in seiner Datei unter features/.
// Nur DOM, kein Framework, kein Bauschritt.

import { REITER } from "./reiter.js";

const DEFAULT_TAB = "start";
const nav = document.querySelector(".tabs");
const main = document.querySelector("main");

// --- Gerüst aufbauen ----------------------------------------------------------

// Für jeden Reiter ein Link in der Leiste und ein leerer Bereich in <main>.
for (const reiter of REITER) {
  const link = document.createElement("a");
  link.href = `#${reiter.id}`;
  link.textContent = reiter.title;
  nav.append(link);

  const panel = document.createElement("section");
  panel.id = reiter.id;
  panel.className = "panel";
  panel.hidden = true;
  main.append(panel);
}

// --- Bereich füllen -------------------------------------------------------------

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

// --- Umschalten -----------------------------------------------------------------

// Zeigt den Bereich, dessen Name hinter dem # in der Adresse steht (z. B. #kalender).
// Fehlt der Name oder gibt es ihn nicht, wird "start" gezeigt.
function showTabFromAddress() {
  const wanted = window.location.hash.slice(1);
  const known = REITER.some((reiter) => reiter.id === wanted);
  const current = known ? wanted : DEFAULT_TAB;

  for (const reiter of REITER) {
    const panel = document.getElementById(reiter.id);
    panel.hidden = reiter.id !== current;
    if (reiter.id === current) {
      renderOnce(reiter, panel);
    }
  }
  for (const link of nav.querySelectorAll("a")) {
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
