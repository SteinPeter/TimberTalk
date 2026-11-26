// Kleine Helfer, um Formulare und Tabellen zu bauen – für die Anmeldung und alle Reiter.
// Alles, was aus der API kommt, wird nur mit textContent in die Seite gesetzt, nie mit innerHTML.
// Die CSS-Klassen form-*, button* und table stehen in style.css unter „Formulare“.

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
  const label = el("label", { class: "form-field" }, el("span", {}, labelText), input);
  if (hint) {
    label.append(el("small", { class: "form-hint" }, hint));
  }
  return label;
}

// Eine Meldung unter einem Formular. Wird von Bildschirmsprechern vorgelesen (role="status").
export function messageBox() {
  const box = el("p", { class: "form-message", role: "status", hidden: true });
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

// Zeit aus der API (UTC) in Ortszeit, z. B. „26.11.2026, 14:05“.
export function formatDateTime(iso) {
  if (!iso) {
    return "–";
  }
  return new Date(iso).toLocaleString("de-DE", { dateStyle: "medium", timeStyle: "short" });
}
