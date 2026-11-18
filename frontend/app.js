// Schaltet zwischen den Reitern um und holt den Status bei der API.
// Nur fetch und DOM, kein Framework, kein Bauschritt.

import { API_BASE } from "./config.js";

// --- Reiter -----------------------------------------------------------------

const DEFAULT_TAB = "start";
const tabLinks = document.querySelectorAll(".tabs a");
const panels = document.querySelectorAll(".panel");

// Zeigt den Bereich, dessen Name hinter dem # in der Adresse steht (z. B. #kalender).
// Fehlt der Name oder gibt es ihn nicht, wird "start" gezeigt.
function showTabFromAddress() {
  const wanted = window.location.hash.slice(1);
  const known = [...panels].some((panel) => panel.id === wanted);
  const current = known ? wanted : DEFAULT_TAB;

  for (const panel of panels) {
    panel.hidden = panel.id !== current;
  }
  for (const link of tabLinks) {
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

// --- Status auf dem Reiter "Start" -------------------------------------------

const backendStatus = document.getElementById("backend-status");
const databaseStatus = document.getElementById("database-status");

async function showHealth() {
  try {
    const response = await fetch(`${API_BASE}/api/health`);
    if (!response.ok) {
      throw new Error(`Antwort ${response.status}`);
    }
    const health = await response.json();
    backendStatus.textContent = health.status === "ok" ? "antwortet" : health.status;
    databaseStatus.textContent = health.database === "ok" ? "antwortet" : "antwortet nicht";
  } catch (error) {
    backendStatus.textContent = `nicht erreichbar (${error.message})`;
    databaseStatus.textContent = "unbekannt";
  }
}

showHealth();
