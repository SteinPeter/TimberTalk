/**
 * Bausteine der Oberfläche: DOM-Helfer, Tabelle, Blätterleiste, Formular, Fehlerkasten.
 *
 * Dieses Modul kennt die API nicht. Es bekommt fertige Daten und
 * Auswahllisten und gibt DOM-Knoten zurück.
 */

/**
 * Baut einen DOM-Knoten.
 *
 * `text` setzt den Textinhalt, `class` die Klasse, `dataset` die data-Attribute,
 * `on…` hängt einen Zuhörer an. Alles andere wird als Eigenschaft gesetzt, wenn
 * das Element sie kennt, sonst als Attribut. Es gibt bewusst kein `html`:
 * so kann nichts aus den Daten als Markup ausgeführt werden.
 */
export function el(tag, attrs = {}, ...kinder) {
  const knoten = document.createElement(tag);
  for (const [name, wert] of Object.entries(attrs || {})) {
    if (wert === undefined || wert === null || wert === false) {
      continue;
    }
    if (name === "text") {
      knoten.textContent = String(wert);
    } else if (name === "class") {
      knoten.className = String(wert);
    } else if (name === "dataset") {
      Object.assign(knoten.dataset, wert);
    } else if (name.startsWith("on") && typeof wert === "function") {
      knoten.addEventListener(name.slice(2), wert);
    } else if (name in knoten) {
      knoten[name] = wert;
    } else {
      knoten.setAttribute(name, wert === true ? "" : String(wert));
    }
  }
  anhaengen(knoten, kinder);
  return knoten;
}

/** Hängt Kinder an; verschachtelte Felder und `null` sind erlaubt. */
export function anhaengen(knoten, kinder) {
  for (const kind of kinder.flat(4)) {
    if (kind === undefined || kind === null || kind === false || kind === "") {
      continue;
    }
    knoten.append(kind instanceof Node ? kind : document.createTextNode(String(kind)));
  }
  return knoten;
}

/** Leert einen Knoten. */
export function leere(knoten) {
  while (knoten.firstChild) {
    knoten.removeChild(knoten.firstChild);
  }
  return knoten;
}

/** Ein Knopf, der den Klick nicht an die Tabellenzeile weitergibt. */
export function knopf(text, onKlick, { haupt = false, titel = null, aus = false } = {}) {
  return el("button", {
    type: "button",
    text,
    title: titel,
    disabled: aus,
    class: haupt ? "haupt" : null,
    onclick: (ereignis) => {
      ereignis.stopPropagation();
      onKlick(ereignis);
    },
  });
}

/** Macht aus einem Wert etwas Lesbares für eine Tabellenzelle. */
export function textWert(wert) {
  if (wert === undefined || wert === null || wert === "") {
    return "–";
  }
  if (typeof wert === "boolean") {
    return wert ? "ja" : "nein";
  }
  if (typeof wert === "object") {
    return JSON.stringify(wert);
  }
  return String(wert);
}

/* ------------------------------------------------------------------ Meldungen */

let meldungsbereich = null;

/** Legt fest, wohin Meldungen und Fehler gehen. */
export function setzeMeldungsbereich(knoten) {
  meldungsbereich = knoten;
}

/** Zeigt eine kurze Erfolgsmeldung, die von selbst verschwindet. */
export function melde(text) {
  if (!meldungsbereich) {
    return;
  }
  const notiz = el("div", { class: "notiz", text });
  meldungsbereich.append(notiz);
  window.setTimeout(() => notiz.remove(), 4000);
}

/**
 * Zeigt ein Problem-JSON lesbar an: Titel, Statuscode und Fehlercode,
 * den deutschen Satz des Backends, die Feldfehler und weitere Angaben.
 */
export function fehlerKasten(problem, { onSchliessen = null } = {}) {
  const p = problem || {};
  const marke = [p.status, p.code].filter(Boolean).join(" · ");
  const kasten = el(
    "div",
    { class: "fehler" },
    el(
      "div",
      { class: "fehler-kopf" },
      el("strong", { text: p.title || "Fehler" }),
      marke ? el("span", { class: "marke", text: marke }) : null,
      onSchliessen ? el("button", { type: "button", text: "×", title: "schließen", onclick: onSchliessen }) : null,
    ),
    el("p", { class: "fehler-text", text: p.detail || "Keine weitere Beschreibung." }),
  );

  const felder = p.errors && typeof p.errors === "object" ? Object.entries(p.errors) : [];
  if (felder.length) {
    anhaengen(kasten, [
      el(
        "ul",
        { class: "fehler-felder" },
        felder.map(([feld, meldung]) =>
          el("li", {}, el("code", { text: feld }), " ", el("span", { text: String(meldung) })),
        ),
      ),
    ]);
  }

  if (p.context && typeof p.context === "object" && Object.keys(p.context).length) {
    anhaengen(kasten, [
      el(
        "details",
        {},
        el("summary", { text: "Weitere Angaben des Backends" }),
        el("pre", { text: JSON.stringify(p.context, null, 2) }),
      ),
    ]);
  }

  if (p.type) {
    anhaengen(kasten, [el("p", { class: "fehler-typ", text: String(p.type) })]);
  }
  return kasten;
}

/** Zeigt einen Fehler im Meldungsbereich; er bleibt stehen, bis er geschlossen wird. */
export function meldeFehler(problem) {
  console.warn("Fehler der API:", problem);
  if (!meldungsbereich) {
    return;
  }
  const kasten = fehlerKasten(problem, { onSchliessen: () => kasten.remove() });
  meldungsbereich.append(kasten);
}

/* -------------------------------------------------------------------- Tabelle */

function zelle(spalte, datensatz) {
  const wert = spalte.wert ? spalte.wert(datensatz) : datensatz[spalte.key];
  if (spalte.art === "status") {
    return el("td", {}, el("span", { class: `status status-${wert}`, text: textWert(wert) }));
  }
  if (spalte.art === "json") {
    const inhalt = wert && Object.keys(wert).length ? JSON.stringify(wert, null, 1) : "–";
    return el("td", {}, el("pre", { class: "json", text: inhalt }));
  }
  const klasse = spalte.art === "zahl" ? "zahl" : spalte.art === "kennung" ? "kennung" : null;
  return el("td", { class: klasse, text: textWert(wert) });
}

/**
 * Baut eine Tabelle.
 *
 * `aktionen` liefert je Datensatz die Knöpfe der letzten Spalte, `aufZeile`
 * macht die Zeilen anklickbar, `markiert` hebt eine Zeile hervor.
 */
export function tabelle({ spalten, zeilen, aktionen = null, aufZeile = null, markiert = null }) {
  const breite = spalten.length + (aktionen ? 1 : 0);
  const koerper = el("tbody");
  if (!zeilen.length) {
    koerper.append(el("tr", {}, el("td", { class: "leer", colspan: breite, text: "Keine Einträge." })));
  }
  for (const datensatz of zeilen) {
    const zeile = el("tr", {
      class: [aufZeile ? "anklickbar" : null, markiert && markiert(datensatz) ? "markiert" : null]
        .filter(Boolean)
        .join(" "),
      onclick: aufZeile ? () => aufZeile(datensatz) : null,
    });
    anhaengen(
      zeile,
      spalten.map((spalte) => zelle(spalte, datensatz)),
    );
    if (aktionen) {
      zeile.append(el("td", { class: "aktionen" }, aktionen(datensatz)));
    }
    koerper.append(zeile);
  }
  return el(
    "table",
    { class: "liste" },
    el(
      "thead",
      {},
      el(
        "tr",
        {},
        spalten.map((spalte) => el("th", { text: spalte.label })),
        aktionen ? el("th", { text: "Aktionen" }) : null,
      ),
    ),
    koerper,
  );
}

/** Blätterleiste für `limit`/`offset`; die API kennt keine Seitennummern. */
export function blaetterleiste({ total, limit, offset, onWechsel }) {
  const von = total === 0 ? 0 : offset + 1;
  const bis = Math.min(offset + limit, total);
  return el(
    "div",
    { class: "blaettern" },
    el("span", { text: `${von}–${bis} von ${total}` }),
    knopf("zurück", () => onWechsel({ offset: Math.max(0, offset - limit), limit }), { aus: offset <= 0 }),
    knopf("weiter", () => onWechsel({ offset: offset + limit, limit }), { aus: bis >= total }),
    el(
      "label",
      {},
      "je Seite ",
      el(
        "select",
        { onchange: (e) => onWechsel({ offset: 0, limit: Number(e.target.value) }) },
        [10, 25, 50, 100, 200].map((n) =>
          el("option", { value: String(n), text: String(n), selected: n === limit }),
        ),
      ),
    ),
  );
}

/* ------------------------------------------------------------------- Formular */

/** Ein Fehler in einem einzelnen Feld, noch vor dem Absenden. */
class FeldFehler extends Error {
  constructor(feld, meldung) {
    super(meldung);
    this.feld = feld;
    this.meldung = meldung;
  }
}

function auswahl(feld, wert) {
  const optionen = feld.optionen || [];
  const steuerung = el("select", { name: feld.name });
  if (!feld.pflicht || wert === undefined || wert === null) {
    steuerung.append(el("option", { value: "", text: feld.leerText || "– bitte wählen –" }));
  }
  for (const option of optionen) {
    steuerung.append(
      el("option", {
        value: String(option.wert),
        text: option.label,
        selected: String(option.wert) === String(wert ?? ""),
      }),
    );
  }
  if (!optionen.length) {
    steuerung.append(el("option", { value: "", text: "(keine Einträge vorhanden)" }));
  }
  return steuerung;
}

function baueSteuerung(feld, wert) {
  switch (feld.typ) {
    case "textarea":
      return el("textarea", { name: feld.name, value: wert ?? "", rows: 3 });
    case "json":
      return el("textarea", {
        name: feld.name,
        rows: 3,
        value: wert === undefined || wert === null ? "" : JSON.stringify(wert, null, 2),
      });
    case "bool":
      return el("input", { type: "checkbox", name: feld.name, checked: Boolean(wert) });
    case "int":
      return el("input", { type: "number", step: "1", name: feld.name, value: wert ?? "" });
    case "decimal":
      // Bewusst `text`: Geld und Mengen gehen als Zeichenkette an die API,
      // damit keine Gleitkommazahl entsteht.
      return el("input", { type: "text", inputMode: "decimal", name: feld.name, value: wert ?? "" });
    case "date":
      return el("input", { type: "date", name: feld.name, value: wert ?? "" });
    case "time":
      return el("input", { type: "time", name: feld.name, value: wert ?? "" });
    case "enum":
    case "ref":
      return auswahl(feld, wert);
    default:
      return el("input", {
        type: "text",
        name: feld.name,
        value: wert ?? "",
        placeholder: feld.platzhalter || "",
      });
  }
}

function leseWert(feld, steuerung) {
  if (feld.typ === "bool") {
    return steuerung.checked;
  }
  const roh = String(steuerung.value ?? "").trim();
  if (roh === "") {
    // Leer heißt „nicht senden": die Schemas verbieten unbekannte Felder und
    // die meisten Felder sind nicht nullbar.
    return undefined;
  }
  if (feld.typ === "int") {
    const zahl = Number(roh);
    if (!Number.isInteger(zahl)) {
      throw new FeldFehler(feld.name, "ganze Zahl erwartet");
    }
    return zahl;
  }
  if (feld.typ === "json") {
    try {
      return JSON.parse(roh);
    } catch (fehler) {
      throw new FeldFehler(feld.name, `kein gültiges JSON: ${fehler.message}`);
    }
  }
  // decimal bleibt eine Zeichenkette, alles andere ebenso.
  return roh;
}

/**
 * Baut ein Formular aus Feldbeschreibungen.
 *
 * Pflichtfelder sind mit `*` markiert, aber nicht im Browser erzwungen: die
 * Prüfung gehört in die Service-Schicht, und die Werkbank soll ihre Fehler
 * absichtlich auslösen können.
 *
 * Gibt einen Griff zurück: `element`, `werte()`, `markiereFehler(errors)`,
 * `steuerung(name)` und `setzeWert(name, wert)`.
 */
export function formular({
  felder,
  werte = {},
  absendenLabel = "Speichern",
  onAbsenden,
  onAbbrechen = null,
  onAendern = null,
}) {
  const form = el("form", { class: "formular" });
  const bereich = el("div", { class: "felder" });
  const steuerungen = new Map();
  const huellen = new Map();

  for (const feld of felder) {
    if (feld.gruppe) {
      bereich.append(el("div", { class: "formular-gruppe", text: feld.gruppe }));
      continue;
    }
    const kennung = `feld-${feld.name.replace(/[^\w-]/g, "-")}`;
    const steuerung = baueSteuerung(feld, werte[feld.name]);
    steuerung.id = kennung;
    if (onAendern) {
      steuerung.addEventListener("change", () => onAendern(feld.name, griff));
    }
    steuerungen.set(feld.name, { feld, steuerung });
    const huelle = el(
      "div",
      { class: "feld", dataset: { feld: feld.name } },
      el("label", { for: kennung }, feld.label, feld.pflicht ? el("span", { class: "pflicht", text: "*" }) : null),
      steuerung,
      feld.hinweis ? el("small", { class: "hinweis", text: feld.hinweis }) : null,
      el("small", { class: "feldfehler" }),
    );
    huellen.set(feld.name, huelle);
    bereich.append(huelle);
  }

  const absenden = el("button", { type: "submit", class: "haupt", text: absendenLabel });
  const knoepfe = el(
    "div",
    { class: "formular-knoepfe" },
    absenden,
    onAbbrechen ? knopf("Abbrechen", onAbbrechen) : null,
  );
  anhaengen(form, [bereich, knoepfe]);

  function loescheFehler() {
    for (const huelle of huellen.values()) {
      huelle.classList.remove("fehlerhaft");
      const anzeige = huelle.querySelector(".feldfehler");
      if (anzeige) {
        anzeige.textContent = "";
      }
    }
  }

  function markiereFehler(errors) {
    loescheFehler();
    const uebrig = {};
    for (const [pfad, meldung] of Object.entries(errors || {})) {
      // Das Backend meldet Feldfehler teils mit Punktpfad (`details.start_time`).
      const name = huellen.has(pfad) ? pfad : pfad.split(".").pop();
      const huelle = huellen.get(name) || huellen.get(pfad);
      if (!huelle) {
        uebrig[pfad] = meldung;
        continue;
      }
      huelle.classList.add("fehlerhaft");
      const anzeige = huelle.querySelector(".feldfehler");
      if (anzeige) {
        anzeige.textContent = String(meldung);
      }
    }
    return uebrig;
  }

  function sammle() {
    const daten = {};
    for (const { feld, steuerung } of steuerungen.values()) {
      const wert = leseWert(feld, steuerung);
      if (wert !== undefined) {
        daten[feld.name] = wert;
      }
    }
    return daten;
  }

  function sammleRoh() {
    // Beim Umbauen des Formulars (etwa nach einem Wechsel der Kostenart) darf eine
    // halbfertige Eingabe nicht alles abbrechen: fehlerhafte Felder fallen weg.
    const daten = {};
    for (const { feld, steuerung } of steuerungen.values()) {
      try {
        const wert = leseWert(feld, steuerung);
        if (wert !== undefined) {
          daten[feld.name] = wert;
        }
      } catch {
        continue;
      }
    }
    return daten;
  }

  const griff = {
    element: form,
    werte: sammle,
    werteRoh: sammleRoh,
    markiereFehler,
    loescheFehler,
    steuerung: (name) => steuerungen.get(name)?.steuerung || null,
    setzeWert(name, wert) {
      const eintrag = steuerungen.get(name);
      if (!eintrag) {
        return;
      }
      if (eintrag.feld.typ === "bool") {
        eintrag.steuerung.checked = Boolean(wert);
      } else {
        eintrag.steuerung.value = wert === undefined || wert === null ? "" : String(wert);
      }
    },
  };

  form.addEventListener("submit", async (ereignis) => {
    ereignis.preventDefault();
    loescheFehler();
    let daten;
    try {
      daten = sammle();
    } catch (fehler) {
      if (fehler instanceof FeldFehler) {
        markiereFehler({ [fehler.feld]: fehler.meldung });
        return;
      }
      throw fehler;
    }
    absenden.disabled = true;
    try {
      await onAbsenden(daten, griff);
    } finally {
      absenden.disabled = false;
    }
  });

  return griff;
}

/**
 * Filterzeile über einer Liste.
 *
 * Nutzt die gleichen Steuerelemente wie das Formular. Leere Felder werden nicht
 * gesendet; ein Häkchen dagegen schon, damit `active_only=false` möglich ist.
 */
export function filterleiste({
  felder,
  werte = {},
  onFiltern,
  onZuruecksetzen = null,
  knopfText = "Filtern",
}) {
  const leiste = el("div", { class: "werkzeugleiste" });
  const steuerungen = new Map();

  for (const feld of felder) {
    const steuerung = baueSteuerung(feld, werte[feld.name]);
    steuerungen.set(feld.name, { feld, steuerung });
    leiste.append(el("label", {}, feld.label, steuerung));
  }

  function sammle() {
    const daten = {};
    for (const { feld, steuerung } of steuerungen.values()) {
      try {
        const wert = leseWert(feld, steuerung);
        if (wert !== undefined) {
          daten[feld.name] = wert;
        }
      } catch {
        continue;
      }
    }
    return daten;
  }

  anhaengen(leiste, [
    knopf(knopfText, () => onFiltern(sammle()), { haupt: true }),
    onZuruecksetzen ? knopf("Zurücksetzen", onZuruecksetzen) : null,
  ]);

  leiste.addEventListener("keydown", (ereignis) => {
    if (ereignis.key === "Enter") {
      ereignis.preventDefault();
      onFiltern(sammle());
    }
  });

  return { element: leiste, werte: sammle };
}

/** Ein abgegrenzter Bereich mit Überschrift. */
export function bereich(titel, ...kinder) {
  return el("section", { class: "bereich" }, titel ? el("h2", { text: titel }) : null, kinder);
}
