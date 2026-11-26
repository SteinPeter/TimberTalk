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

// --- Personen: Foto oder Initialen, Nachname ----------------------------------------

// Der Nachname: das letzte Wort des Namens („Max Berger“ → „Berger“).
export function lastName(displayName) {
  const words = displayName.trim().split(/\s+/);
  return words[words.length - 1];
}

// Ein rundes Bild der Person: ihr Foto oder – ohne Foto – ihre Initialen („MB“).
// Das Foto ist ein data:-Text aus der API und kommt nur als src in ein <img>, nie als HTML.
export function avatar(person, size = "medium") {
  if (person.photo) {
    return el("img", { class: `avatar avatar-${size}`, src: person.photo, alt: "" });
  }
  const initials = person.display_name
    .trim()
    .split(/\s+/)
    .map((word) => word[0])
    .filter(Boolean);
  const text = (initials.length > 1 ? initials[0] + initials[initials.length - 1] : initials[0] ?? "?").toUpperCase();
  return el("span", { class: `avatar avatar-${size}`, "aria-hidden": "true" }, text);
}

// Macht aus einer Bilddatei ein quadratisches JPEG mit 256 × 256 Pixeln (Mitte ausgeschnitten)
// als data:-Text – klein genug für die Datenbank, scharf genug für die Leiste.
export function photoFromFile(file, size = 256) {
  return new Promise((resolve, reject) => {
    if (!file.type.startsWith("image/")) {
      reject(new Error("Bitte ein Bild auswählen (z. B. JPEG oder PNG)."));
      return;
    }
    const image = new Image();
    const url = URL.createObjectURL(file);
    image.onload = () => {
      const side = Math.min(image.width, image.height);
      const canvas = document.createElement("canvas");
      canvas.width = size;
      canvas.height = size;
      canvas
        .getContext("2d")
        .drawImage(image, (image.width - side) / 2, (image.height - side) / 2, side, side, 0, 0, size, size);
      URL.revokeObjectURL(url);
      resolve(canvas.toDataURL("image/jpeg", 0.85));
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Das Bild ließ sich nicht öffnen."));
    };
    image.src = url;
  });
}

// --- Kleines Menü unter einem Knopf (z. B. Konto oben rechts, „Mehr“ im Kalender) ------

// items: [{ label, onSelect }] – oder ein Element (z. B. eine Überschrift) für Text ohne Aktion.
// Öffnet mit Klick, schließt mit Escape, Klick daneben oder nach der Auswahl.
export function menuButton(button, items) {
  const menu = el("div", { class: "menu", role: "menu", hidden: true });
  for (const item of items) {
    if (item instanceof Node) {
      menu.append(item);
      continue;
    }
    menu.append(
      el(
        "button",
        {
          type: "button",
          role: "menuitem",
          class: "menu-item",
          onclick: () => {
            close();
            item.onSelect();
          },
        },
        item.label,
      ),
    );
  }
  button.setAttribute("aria-haspopup", "menu");
  button.setAttribute("aria-expanded", "false");
  const box = el("div", { class: "menu-box" }, button, menu);

  function close() {
    menu.hidden = true;
    button.setAttribute("aria-expanded", "false");
  }
  button.addEventListener("click", () => {
    const opening = menu.hidden;
    menu.hidden = !opening;
    button.setAttribute("aria-expanded", String(opening));
    if (opening) {
      menu.querySelector(".menu-item")?.focus();
    }
  });
  document.addEventListener("click", (event) => {
    if (!box.contains(event.target)) {
      close();
    }
  });
  menu.addEventListener("keydown", (event) => {
    const entries = [...menu.querySelectorAll(".menu-item")];
    const index = entries.indexOf(document.activeElement);
    if (event.key === "Escape") {
      close();
      button.focus();
    } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const step = event.key === "ArrowDown" ? 1 : -1;
      entries[(index + step + entries.length) % entries.length]?.focus();
    }
  });
  return box;
}

// Öffnet einen Abschnitt im Reiter „Einstellungen“, z. B. openSettings("accounts-own").
export function openSettings(sectionId) {
  try {
    localStorage.setItem("timbertalk.settings.section", sectionId);
  } catch {
    // Merken geht nicht – dann öffnet sich eben der erste Abschnitt.
  }
  window.location.hash = "#settings";
  // Ist der Reiter schon aufgebaut, den Abschnitt direkt anklicken.
  requestAnimationFrame(() => document.getElementById(`settings-tab-${sectionId}`)?.click());
}
