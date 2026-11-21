// Kleine Helfer für die Oberfläche von „Material, Fahrten und Preise“ (F5).
// Sie werden vom Reiter „Buchungen“ und vom Reiter „Einstellungen“ benutzt.
// Alles, was aus der API kommt, wird nur mit textContent in die Seite gesetzt, nie mit innerHTML.
// Zum Anzeigen werden Zahlen mit Intl formatiert; gerechnet wird im Backend mit Decimal.

import { API_BASE } from "../../config.js";

// Baut ein Element: el("button", { class: "x", onclick: fn }, "Text", weitereKinder).
export function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "class") {
      node.className = value;
    } else if (key.startsWith("on")) {
      node.addEventListener(key.slice(2), value);
    } else if (["value", "disabled", "checked", "hidden", "textContent"].includes(key)) {
      node[key] = value;
    } else {
      node.setAttribute(key, value);
    }
  }
  node.append(...children);
  return node;
}

// Ein Eingabefeld mit Beschriftung darüber und, wenn angegeben, einem kleinen Hinweis darunter.
export function field(labelText, input, hint) {
  const label = el("label", { class: "materials-field" }, el("span", {}, labelText), input);
  if (hint) {
    label.append(el("small", { class: "materials-hint" }, hint));
  }
  return label;
}

// Schickt Daten an die API (POST, PUT, DELETE). Lesen geht weiter über getJson aus shared/api.js.
// Antwortet die API mit einem Fehler, steht deren deutscher Text in der Ausnahme.
export async function sendJson(method, path, body) {
  const options = { method };
  if (body !== undefined) {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(body);
  }
  const response = await fetch(`${API_BASE}${path}`, options);
  if (!response.ok) {
    let message = `Antwort ${response.status}`;
    try {
      const data = await response.json();
      if (typeof data.detail === "string") {
        message = data.detail;
      } else if (Array.isArray(data.detail)) {
        message = "Bitte die Eingaben prüfen.";
      }
    } catch {
      // Keine lesbare Fehlermeldung: es bleibt beim Statuscode.
    }
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}

// Eine Meldung unter einem Formular. Wird von Bildschirmsprechern vorgelesen (role="status").
export function messageBox() {
  const box = el("p", { class: "materials-message", role: "status", hidden: true });
  box.show = (text, isError = false) => {
    box.textContent = isError ? `Das hat nicht geklappt: ${text}` : text;
    box.dataset.kind = isError ? "error" : "ok";
    box.hidden = false;
  };
  box.clear = () => {
    box.hidden = true;
  };
  return box;
}

const euro = new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" });
const number = new Intl.NumberFormat("de-DE", { maximumFractionDigits: 4 });

export const formatEuro = (value) => euro.format(Number(value));
export const formatNumber = (value) => number.format(Number(value));
export const formatDate = (iso) => iso.split("-").reverse().join(".");

// Das heutige Datum als JJJJ-MM-TT, wie es ein Datumsfeld und die API erwarten.
export const today = () => new Date().toLocaleDateString("sv-SE");

// Macht aus „2,5“ oder „2.5“ den Dezimal-Text „2.5“. Ist es keine Zahl, kommt null zurück.
export function toDecimalText(input) {
  const text = input.trim().replace(",", ".");
  return /^\d+(\.\d+)?$/.test(text) ? text : null;
}
