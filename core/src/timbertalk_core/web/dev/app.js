/**
 * Einstieg der Werkbank: Zustand, Kopfleiste, Reiter und Seiten.
 *
 * Die Seiten entstehen aus den Beschreibungen in `meta.js`. Besondere Logik hat
 * nur, was sie wirklich braucht: Buchungen (Status und Felder je Kostenart),
 * Projekte (Arbeitspakete darunter), Preise (Ziel je Zielart) und der Verbrauch
 * (Übersicht).
 */

import * as api from "./api.js";
import * as ui from "./ui.js";
import { bereich, el, knopf, leere } from "./ui.js";
import {
  ARBEITSPAKETE,
  BUCHUNGEN,
  EINHEITEN,
  KOSTENARTEN,
  KUNDEN,
  MATERIAL,
  MITARBEITER,
  MODELLPREISE,
  NACHSCHLAGEN,
  PREISE,
  PROJEKTE,
  PROTOKOLL,
  VERBRAUCH,
} from "./meta.js";

/** Alles, was mehrere Seiten brauchen. Wird beim Start geladen. */
const zustand = {
  aufzaehlungen: {},
  detailSchemas: {},
  nachschlag: new Map(),
};

/* --------------------------------------------------------------- Hilfsmittel */

function problemVon(fehler) {
  if (fehler && fehler.problem) {
    return fehler.problem;
  }
  console.error(fehler);
  return {
    title: "Fehler in der Werkbank",
    status: 0,
    code: "werkbank",
    detail: String((fehler && fehler.message) || fehler),
  };
}

/**
 * Lädt eine Nachschlageliste (Kunden, Projekte, Einheiten …) und merkt sie.
 *
 * Die API kennt kein Suchen in Auswahlfeldern; `limit=200` ist ihr Höchstwert.
 * Für eine lokale Installation reicht das, für echte Bestände nicht – das steht
 * als Vorschlag im Plan.
 */
async function nachschlag(id) {
  if (zustand.nachschlag.has(id)) {
    return zustand.nachschlag.get(id);
  }
  const beschreibung = NACHSCHLAGEN[id];
  if (!beschreibung) {
    throw new Error(`Unbekannte Nachschlageliste '${id}'`);
  }
  const seite = await api.hole(beschreibung.pfad, { limit: 200 });
  const eintraege = (seite && seite.items) || [];
  const eintrag = {
    beschreibung,
    eintraege,
    optionen: eintraege.map((e) => ({
      wert: e[beschreibung.wert],
      label: beschreibung.anzeige(e),
    })),
    anzeigeKarte: new Map(eintraege.map((e) => [String(e[beschreibung.wert]), beschreibung.anzeige(e)])),
    rohKarte: new Map(eintraege.map((e) => [String(e[beschreibung.wert]), e])),
    unvollstaendig: (seite && seite.total) > eintraege.length,
  };
  zustand.nachschlag.set(id, eintrag);
  return eintrag;
}

/** Nach jedem Schreibvorgang: Auswahllisten können veraltet sein. */
function entwerteNachschlag() {
  zustand.nachschlag.clear();
}

function aufzaehlungsOptionen(name) {
  return (zustand.aufzaehlungen[name] || []).map((wert) => ({ wert, label: wert }));
}

/** Macht aus Feldbeschreibungen fertige Formularfelder samt Auswahllisten. */
async function bereiteFelder(felder, modus) {
  const fertig = [];
  for (const feld of felder) {
    if (modus === "aendern" && feld.nurAnlegen) {
      continue;
    }
    const kopie = { ...feld };
    if (feld.typ === "enum" && feld.aufzaehlung) {
      kopie.optionen = aufzaehlungsOptionen(feld.aufzaehlung);
    } else if (feld.typ === "ref" && feld.bezug) {
      const eintrag = await nachschlag(feld.bezug);
      kopie.optionen = eintrag.optionen;
      if (eintrag.unvollstaendig) {
        kopie.hinweis = [feld.hinweis, "nur die ersten 200 Einträge"].filter(Boolean).join(" – ");
      }
    }
    fertig.push(kopie);
  }
  return fertig;
}

/** Löst Spalten auf, die eine Kennung über eine Nachschlageliste anzeigen. */
async function bereiteSpalten(spalten) {
  const fertig = [];
  for (const spalte of spalten) {
    if (spalte.art === "bezug") {
      const eintrag = await nachschlag(spalte.bezug);
      fertig.push({
        ...spalte,
        art: null,
        wert: (datensatz) =>
          eintrag.anzeigeKarte.get(String(datensatz[spalte.key])) || datensatz[spalte.key],
      });
    } else {
      fertig.push(spalte);
    }
  }
  return fertig;
}

/** Vorgabewerte eines neuen Datensatzes; `vorgabe` darf eine Funktion sein. */
function vorgabewerte(felder) {
  const werte = {};
  for (const feld of felder) {
    if (feld.vorgabe !== undefined) {
      werte[feld.name] = typeof feld.vorgabe === "function" ? feld.vorgabe() : feld.vorgabe;
    }
  }
  return werte;
}

/** Holt die Werte eines Datensatzes für das Formular, auch aus `details.…`. */
function verflache(datensatz, felder) {
  const werte = {};
  for (const feld of felder) {
    const punkt = feld.name.indexOf(".");
    if (punkt === -1) {
      werte[feld.name] = datensatz[feld.name];
      continue;
    }
    const gruppe = datensatz[feld.name.slice(0, punkt)];
    werte[feld.name] = gruppe ? gruppe[feld.name.slice(punkt + 1)] : undefined;
  }
  return werte;
}

/** Baut aus `details.start_time` wieder `{details: {start_time: …}}`. */
function verschachtle(daten) {
  const ergebnis = {};
  for (const [schluessel, wert] of Object.entries(daten)) {
    const punkt = schluessel.indexOf(".");
    if (punkt === -1) {
      ergebnis[schluessel] = wert;
      continue;
    }
    const gruppe = schluessel.slice(0, punkt);
    if (!ergebnis[gruppe] || typeof ergebnis[gruppe] !== "object") {
      ergebnis[gruppe] = {};
    }
    ergebnis[gruppe][schluessel.slice(punkt + 1)] = wert;
  }
  return ergebnis;
}

function bezeichnung(datensatz) {
  return (
    datensatz.display_name ||
    datensatz.title ||
    datensatz.name ||
    datensatz.name_de ||
    datensatz.label_de ||
    datensatz.code ||
    datensatz.id
  );
}

/* ---------------------------------------------------------------- Listenseite */

/**
 * Eine Liste mit Filter, Blätterleiste und Formular.
 *
 * Die Zusatzpunkte in `optionen` sind alles, was die besonderen Seiten brauchen:
 * `fest` (unveränderliche Filter), `festeFelder` (feste Werte beim Anlegen),
 * `versteckteFelder`, `spalten`, `felder` (eigene Feldliste), `aktionen`
 * (weitere Knöpfe je Zeile), `aufZeile`, `markiert`, `onFeldAenderung`,
 * `nachAenderung`.
 */
function liste(meta, optionen = {}) {
  const fest = optionen.fest || {};
  const festeFelder = optionen.festeFelder || {};
  const versteckt = new Set(optionen.versteckteFelder || []);
  const wurzel = el("div");
  const formBereich = el("div");

  const anfangsfilter = () => {
    const werte = {};
    for (const feld of meta.filter || []) {
      if (feld.vorgabe !== undefined) {
        werte[feld.name] = feld.vorgabe;
      }
    }
    return { ...werte, ...(optionen.filter || {}) };
  };

  const lz = { filter: anfangsfilter(), limit: 50, offset: 0, form: null };

  const helfer = {
    zustand: lz,
    neuLaden: () => zeichne(),
    oeffneFormular: (modus, datensatz) => oeffneFormular(modus, datensatz),
    formularNeu: () => zeichneFormular(),
  };

  async function felderFuer(modus, datensatz) {
    if (optionen.felder) {
      return optionen.felder(modus, datensatz, lz);
    }
    const grundlage = (meta.felder || []).filter((feld) => !versteckt.has(feld.name));
    return bereiteFelder(grundlage, modus);
  }

  function oeffneFormular(modus, datensatz) {
    lz.form = { modus, datensatz: datensatz || null, werte: null };
    return zeichneFormular();
  }

  async function speichere(daten, griff) {
    const koerper = verschachtle({ ...daten, ...festeFelder });
    try {
      if (lz.form.modus === "anlegen") {
        await api.sende(meta.pfad, koerper);
        ui.melde(`${meta.einzahl} angelegt.`);
      } else {
        await api.aendere(`${meta.pfad}/${lz.form.datensatz.id}`, koerper, {
          expected_version: lz.form.datensatz.version,
        });
        ui.melde(`${meta.einzahl} geändert.`);
      }
      lz.form = null;
      entwerteNachschlag();
      await zeichne();
      if (optionen.nachAenderung) {
        optionen.nachAenderung();
      }
    } catch (fehler) {
      const problem = problemVon(fehler);
      // Beides: die Felder markieren und das Problem-JSON im Klartext zeigen.
      griff.markiereFehler(problem.errors);
      ui.meldeFehler(problem);
    }
  }

  async function loesche(datensatz) {
    const frage = `${meta.einzahl} „${bezeichnung(datensatz)}" löschen (Soft Delete)?`;
    if (!window.confirm(frage)) {
      return;
    }
    try {
      await api.entferne(`${meta.pfad}/${datensatz.id}`, { expected_version: datensatz.version });
      ui.melde(`${meta.einzahl} gelöscht.`);
      entwerteNachschlag();
      await zeichne();
      if (optionen.nachAenderung) {
        optionen.nachAenderung();
      }
    } catch (fehler) {
      ui.meldeFehler(problemVon(fehler));
    }
  }

  async function zeichneFormular() {
    leere(formBereich);
    if (!lz.form) {
      return formBereich;
    }
    const { modus, datensatz } = lz.form;
    const felder = await felderFuer(modus, datensatz);
    const werte =
      lz.form.werte || (datensatz ? verflache(datensatz, felder) : vorgabewerte(felder));
    const griff = ui.formular({
      felder,
      werte,
      absendenLabel: modus === "anlegen" ? "Anlegen" : "Änderung speichern",
      onAbsenden: speichere,
      onAbbrechen: () => {
        lz.form = null;
        leere(formBereich);
      },
      onAendern: optionen.onFeldAenderung
        ? (name, g) => optionen.onFeldAenderung(name, g, helfer)
        : null,
    });
    const titel =
      modus === "anlegen"
        ? `${meta.einzahl} anlegen`
        : `${meta.einzahl} bearbeiten – Version ${datensatz.version}`;
    formBereich.append(bereich(titel, griff.element));
    return formBereich;
  }

  async function zeichne() {
    let seite;
    try {
      seite = await api.hole(meta.pfad, { ...lz.filter, ...fest, limit: lz.limit, offset: lz.offset });
    } catch (fehler) {
      leere(wurzel).append(ui.fehlerKasten(problemVon(fehler)));
      return wurzel;
    }

    const spalten = await bereiteSpalten(optionen.spalten || meta.spalten);
    const sichtbareFilter = (meta.filter || []).filter((feld) => !(feld.name in fest));
    const filterleiste = sichtbareFilter.length
      ? ui.filterleiste({
          felder: await bereiteFelder(sichtbareFilter, "filter"),
          werte: lz.filter,
          onFiltern: (werte) => {
            lz.filter = werte;
            lz.offset = 0;
            zeichne();
          },
          onZuruecksetzen: () => {
            lz.filter = anfangsfilter();
            lz.offset = 0;
            zeichne();
          },
        }).element
      : null;

    const werkzeuge = el(
      "div",
      { class: "werkzeugleiste" },
      meta.caps.anlegen
        ? knopf(`${meta.einzahl} anlegen`, () => oeffneFormular("anlegen"), { haupt: true })
        : null,
      knopf("Neu laden", () => {
        entwerteNachschlag();
        zeichne();
      }),
      !meta.caps.anlegen && !meta.caps.aendern && !meta.caps.loeschen
        ? el("span", { class: "hinweis", text: "Diese Ressource ist über die API nur lesbar." })
        : null,
    );

    // Eine Ressource ohne Knöpfe bekommt auch keine Aktionsspalte.
    const mitAktionen = Boolean(meta.caps.aendern || meta.caps.loeschen || optionen.aktionen);
    const tabelle = ui.tabelle({
      spalten,
      zeilen: (seite && seite.items) || [],
      aufZeile: optionen.aufZeile || null,
      markiert: optionen.markiert || null,
      aktionen: mitAktionen
        ? (datensatz) =>
            [
              ...(optionen.aktionen ? optionen.aktionen(datensatz, helfer) : []),
              meta.caps.aendern
                ? knopf("Bearbeiten", () => oeffneFormular("aendern", datensatz))
                : null,
              meta.caps.loeschen ? knopf("Löschen", () => loesche(datensatz)) : null,
            ].filter(Boolean)
        : null,
    });

    leere(wurzel);
    ui.anhaengen(wurzel, [
      werkzeuge,
      filterleiste,
      tabelle,
      ui.blaetterleiste({
        total: seite.total,
        limit: seite.limit,
        offset: seite.offset,
        onWechsel: ({ offset, limit }) => {
          lz.offset = offset;
          lz.limit = limit;
          zeichne();
        },
      }),
      formBereich,
    ]);
    return wurzel;
  }

  return { element: wurzel, neuLaden: zeichne, oeffneFormular, zustand: lz, helfer };
}

/** Eine Seite, die aus einer einzigen Liste besteht. */
async function einfacheSeite(wurzel, meta, optionen = {}) {
  const inhalt = liste(meta, optionen);
  wurzel.append(
    bereich(
      meta.label,
      meta.hinweis ? el("p", { class: "hinweis", text: meta.hinweis }) : null,
      inhalt.element,
    ),
  );
  await inhalt.neuLaden();
  return inhalt;
}

/* ------------------------------------------------------ Projekte und Pakete */

async function seiteProjekte(wurzel) {
  const paketBereich = el("div");
  let gewaehlt = null;

  async function zeigePakete(projekt) {
    gewaehlt = projekt;
    await projektListe.neuLaden();
    leere(paketBereich);
    const pakete = liste(ARBEITSPAKETE, {
      fest: { project_id: projekt.id },
      festeFelder: { project_id: projekt.id },
      versteckteFelder: ["project_id"],
    });
    paketBereich.append(
      bereich(`Arbeitspakete zu ${projekt.number} · ${projekt.title}`, pakete.element),
    );
    await pakete.neuLaden();
  }

  const projektListe = liste(PROJEKTE, {
    aufZeile: (projekt) => zeigePakete(projekt),
    markiert: (projekt) => gewaehlt !== null && projekt.id === gewaehlt.id,
    nachAenderung: () => leere(paketBereich),
  });

  wurzel.append(
    bereich(
      PROJEKTE.label,
      el("p", { class: "hinweis", text: PROJEKTE.hinweis }),
      projektListe.element,
    ),
    paketBereich,
  );
  await projektListe.neuLaden();
}

/* --------------------------------------------------------------- Buchungen */

/** Baut aus einem JSON-Schema der API die Felder für die Detailangaben. */
function detailFelder(art) {
  const schema = zustand.detailSchemas[art];
  if (!schema || !schema.properties) {
    return [];
  }
  const pflichtfelder = new Set(schema.required || []);
  return Object.entries(schema.properties).map(([name, eigenschaft]) => ({
    name: `details.${name}`,
    label: eigenschaft.description || eigenschaft.title || name,
    typ: typAusSchema(eigenschaft),
    optionen: optionenAusSchema(eigenschaft, schema),
    pflicht: pflichtfelder.has(name),
  }));
}

function kandidaten(eigenschaft) {
  return Array.isArray(eigenschaft.anyOf)
    ? eigenschaft.anyOf.filter((teil) => teil.type !== "null")
    : [eigenschaft];
}

function typAusSchema(eigenschaft) {
  for (const teil of kandidaten(eigenschaft)) {
    if (teil.$ref || Array.isArray(teil.enum)) {
      return "enum";
    }
    // Geld und Mengen: Pydantic beschreibt sie als `number` oder `string`
    // mit `decimal_places`; sie müssen als Zeichenkette an die API gehen.
    if (teil.decimal_places !== undefined || teil.max_digits !== undefined) {
      return "decimal";
    }
    if (Array.isArray(teil.anyOf)) {
      const typen = teil.anyOf.map((unterteil) => unterteil.type);
      if (typen.includes("number") || typen.includes("string")) {
        return "decimal";
      }
    }
    if (teil.type === "boolean") {
      return "bool";
    }
    if (teil.type === "integer") {
      return "int";
    }
    if (teil.type === "number") {
      return "decimal";
    }
    if (teil.format === "time") {
      return "time";
    }
    if (teil.format === "date") {
      return "date";
    }
    if (teil.type === "string") {
      return "text";
    }
  }
  return "text";
}

function optionenAusSchema(eigenschaft, schema) {
  for (const teil of kandidaten(eigenschaft)) {
    if (Array.isArray(teil.enum)) {
      return teil.enum.map((wert) => ({ wert, label: String(wert) }));
    }
    if (typeof teil.$ref === "string") {
      const name = teil.$ref.split("/").pop();
      const definition = (schema.$defs || {})[name];
      if (definition && Array.isArray(definition.enum)) {
        return definition.enum.map((wert) => ({ wert, label: String(wert) }));
      }
    }
  }
  return [];
}

async function seiteBuchungen(wurzel) {
  async function kostenartVon(werte, datensatz) {
    const kennung = (werte && werte.cost_type_id) || (datensatz && datensatz.cost_type_id) || "";
    if (!kennung) {
      return null;
    }
    const eintrag = await nachschlag("kostenarten");
    return eintrag.rohKarte.get(String(kennung)) || null;
  }

  const buchungen = liste(BUCHUNGEN, {
    felder: async (modus, datensatz, lz) => {
      const werte = lz.form ? lz.form.werte : null;
      const kostenart = await kostenartVon(werte, datensatz);
      const art = (kostenart && kostenart.kind) || (datensatz && datensatz.cost_type_kind) || null;

      const grundlage = BUCHUNGEN.felder.filter((feld) => {
        // Einen Artikel nimmt der Service nur bei Material an.
        if (feld.name === "material_item_id") {
          return art === "material";
        }
        return true;
      });

      const felder = await bereiteFelder(grundlage, modus);
      for (const feld of felder) {
        // Bei Arbeitszeit ist der Mitarbeiter Pflicht; das prüft auch der Service.
        if (feld.name === "employee_id" && art === "labor") {
          feld.pflicht = true;
        }
        if (feld.name === "unit_code" && kostenart) {
          feld.hinweis = `Kostenart erwartet '${kostenart.default_unit_code}'`;
        }
      }

      if (!art) {
        return [...felder, { gruppe: "Detailfelder erscheinen, sobald eine Kostenart gewählt ist" }];
      }
      const details = detailFelder(art);
      if (!details.length) {
        return [...felder, { gruppe: `Art '${art}' hat keine Detailfelder` }];
      }
      return [...felder, { gruppe: `Detailfelder der Art '${art}'` }, ...details];
    },

    onFeldAenderung: async (name, griff, helfer) => {
      if (name !== "cost_type_id") {
        return;
      }
      const werte = griff.werteRoh();
      const kostenart = await kostenartVon(werte, helfer.zustand.form.datensatz);
      if (kostenart) {
        // Der Service verlangt die Einheit der Kostenart; also gleich vorbelegen.
        werte.unit_code = kostenart.default_unit_code;
      }
      helfer.zustand.form.werte = werte;
      await helfer.formularNeu();
    },

    aktionen: (datensatz, helfer) => [
      datensatz.status === "draft"
        ? knopf("Bestätigen", () => statusWechsel(datensatz, "confirm", helfer), { haupt: true })
        : null,
      datensatz.status === "draft" || datensatz.status === "confirmed"
        ? knopf("Stornieren", () => statusWechsel(datensatz, "cancel", helfer))
        : null,
      knopf("Protokoll", () => {
        window.location.hash = `#/protokoll?entity_id=${datensatz.id}`;
      }),
    ],
  });

  async function statusWechsel(datensatz, vorgang, helfer) {
    try {
      const neu = await api.sende(`/bookings/${datensatz.id}/${vorgang}`, undefined, {
        expected_version: datensatz.version,
      });
      ui.melde(`Buchung ist jetzt '${neu.status}'.`);
      await helfer.neuLaden();
    } catch (fehler) {
      ui.meldeFehler(problemVon(fehler));
      await helfer.neuLaden();
    }
  }

  wurzel.append(
    bereich(
      BUCHUNGEN.label,
      el("p", {
        class: "hinweis",
        text:
          "Jede neue Buchung beginnt als 'draft'. Bestätigen darf nur ein Akteur der " +
          "Art 'user' – mit 'agent' in der Kopfleiste antwortet die API mit 403. " +
          "'locked' und 'cancelled' sind unveränderbar.",
      }),
      buchungen.element,
    ),
  );
  await buchungen.neuLaden();
}

/* --------------------------------------------------------- Material und Preise */

async function seiteMaterialPreise(wurzel) {
  await einfacheSeite(wurzel, MATERIAL);

  const zielSpalte = {
    key: "target_id",
    label: "Ziel",
    art: null,
    wert: null,
  };

  const artikel = await nachschlag("artikel");
  const kostenarten = await nachschlag("kostenarten");
  zielSpalte.wert = (preis) => {
    const karte = preis.target_type === "material_item" ? artikel.anzeigeKarte : kostenarten.anzeigeKarte;
    return karte.get(String(preis.target_id)) || preis.target_id;
  };

  const preise = liste(PREISE, {
    spalten: PREISE.spalten.map((spalte) => (spalte.key === "target_id" ? zielSpalte : spalte)),
    felder: async (modus, datensatz, lz) => {
      const werte = lz.form ? lz.form.werte : null;
      const zielart =
        (werte && werte.target_type) || (datensatz && datensatz.target_type) || "cost_type";
      const bezug = zielart === "material_item" ? "artikel" : "kostenarten";
      const grundlage = PREISE.felder.map((feld) =>
        feld.name === "target_id" ? { ...feld, bezug } : feld,
      );
      return bereiteFelder(grundlage, modus);
    },
    onFeldAenderung: async (name, griff, helfer) => {
      if (name !== "target_type") {
        return;
      }
      const werte = griff.werteRoh();
      werte.target_id = "";
      helfer.zustand.form.werte = werte;
      await helfer.formularNeu();
    },
  });

  wurzel.append(
    bereich(PREISE.label, el("p", { class: "hinweis", text: PREISE.hinweis }), preise.element),
  );
  await preise.neuLaden();

  wurzel.append(await preisErmitteln());
}

/** Kleines Formular auf `GET /prices/resolve`: zeigt Preis und Herkunft. */
async function preisErmitteln() {
  const ergebnis = el("div");
  const felder = await bereiteFelder(
    [
      {
        name: "target_type",
        label: "Zielart",
        typ: "enum",
        aufzaehlung: "PriceTargetType",
        pflicht: true,
      },
      { name: "target_id", label: "Ziel", typ: "ref", bezug: "kostenarten", pflicht: true },
      { name: "on_date", label: "Stichtag", typ: "date", hinweis: "leer = heute" },
    ],
    "anlegen",
  );

  const griff = ui.formular({
    felder,
    absendenLabel: "Preis ermitteln",
    onAendern: async (name, g) => {
      if (name !== "target_type") {
        return;
      }
      const bezug = g.werteRoh().target_type === "material_item" ? "artikel" : "kostenarten";
      const eintrag = await nachschlag(bezug);
      const auswahl = g.steuerung("target_id");
      leere(auswahl);
      auswahl.append(el("option", { value: "", text: "– bitte wählen –" }));
      for (const option of eintrag.optionen) {
        auswahl.append(el("option", { value: String(option.wert), text: option.label }));
      }
    },
    onAbsenden: async (daten) => {
      leere(ergebnis);
      try {
        const preis = await api.hole("/prices/resolve", daten);
        ergebnis.append(
          ui.tabelle({
            spalten: [
              { key: "unit_price", label: "Preis", art: "zahl" },
              { key: "currency", label: "Währung" },
              { key: "origin", label: "Herkunft" },
              { key: "on_date", label: "Stichtag" },
              { key: "price_id", label: "Preis-Kennung", art: "kennung" },
            ],
            zeilen: [preis],
          }),
        );
      } catch (fehler) {
        const problem = problemVon(fehler);
        ergebnis.append(ui.fehlerKasten(problem));
      }
    },
  });

  return bereich(
    "Preis am Stichtag ermitteln",
    el("p", {
      class: "hinweis",
      text: "Zeigt denselben Preis, den eine Buchung bekommt – samt Herkunft (price_material_item, price_cost_type, cost_type_default).",
    }),
    griff.element,
    ergebnis,
  );
}

/* ------------------------------------------------------------- KI-Verbrauch */

async function seiteVerbrauch(wurzel) {
  await einfacheSeite(wurzel, VERBRAUCH);
  wurzel.append(await verbrauchsUebersicht());
  await einfacheSeite(wurzel, MODELLPREISE);
}

async function verbrauchsUebersicht() {
  const ergebnis = el("div");
  const felder = await bereiteFelder(
    [
      { name: "period", label: "Zeitraster", typ: "enum", aufzaehlung: "UsagePeriod" },
      { name: "group_by", label: "Gruppierung", typ: "enum", aufzaehlung: "UsageGrouping" },
      { name: "date_from", label: "von", typ: "date" },
      { name: "date_to", label: "bis", typ: "date" },
    ],
    "anlegen",
  );

  const leiste = ui.filterleiste({
    felder,
    werte: { period: "month", group_by: "model" },
    knopfText: "Übersicht holen",
    onFiltern: async (werte) => {
      leere(ergebnis);
      try {
        const uebersicht = await api.hole("/usage/summary", werte);
        ergebnis.append(
          ui.tabelle({
            spalten: [
              { key: "period", label: "Zeitraum" },
              { key: "group", label: "Gruppe" },
              { key: "calls", label: "Aufrufe", art: "zahl" },
              { key: "input_tokens", label: "Eingabe", art: "zahl" },
              { key: "output_tokens", label: "Ausgabe", art: "zahl" },
              { key: "cost", label: "Kosten", art: "zahl" },
              { key: "currency", label: "Währung" },
            ],
            zeilen: uebersicht.rows || [],
          }),
          el("p", {
            class: "hinweis",
            text: `Summe: ${uebersicht.total_cost} ${uebersicht.currency}`,
          }),
        );
      } catch (fehler) {
        ergebnis.append(ui.fehlerKasten(problemVon(fehler)));
      }
    },
  });

  return bereich("Verbrauchsübersicht", leiste.element, ergebnis);
}

/* -------------------------------------------------------- Änderungsprotokoll */

async function seiteProtokoll(wurzel, params) {
  // Aus einer Buchung heraus springt die Oberfläche hierher, vorgefiltert.
  const vorfilter = {};
  for (const feld of PROTOKOLL.filter) {
    if (params[feld.name]) {
      vorfilter[feld.name] = params[feld.name];
    }
  }
  await einfacheSeite(wurzel, PROTOKOLL, { filter: vorfilter });
}

/* ------------------------------------------------------------------ Stammdaten */

async function seiteStammdaten(wurzel) {
  await einfacheSeite(wurzel, EINHEITEN);
  await einfacheSeite(wurzel, MITARBEITER);
}

/* ----------------------------------------------------------- Reiter und Route */

const SEITEN = [
  { id: "kunden", label: "Kunden", zeichne: (wurzel) => einfacheSeite(wurzel, KUNDEN) },
  { id: "projekte", label: "Projekte", zeichne: seiteProjekte },
  { id: "buchungen", label: "Buchungen", zeichne: seiteBuchungen },
  { id: "kostenarten", label: "Kostenarten", zeichne: (wurzel) => einfacheSeite(wurzel, KOSTENARTEN) },
  { id: "material", label: "Material und Preise", zeichne: seiteMaterialPreise },
  { id: "verbrauch", label: "KI-Verbrauch", zeichne: seiteVerbrauch },
  { id: "protokoll", label: "Änderungsprotokoll", zeichne: seiteProtokoll },
  { id: "stammdaten", label: "Stammdaten", zeichne: seiteStammdaten },
];

function routeLesen() {
  const roh = window.location.hash.replace(/^#\/?/, "");
  const [pfad, abfrage] = roh.split("?");
  return {
    id: pfad || SEITEN[0].id,
    params: Object.fromEntries(new URLSearchParams(abfrage || "")),
  };
}

function zeichneReiter(aktiv) {
  const leiste = leere(document.getElementById("reiter"));
  for (const seite of SEITEN) {
    leiste.append(
      el("a", {
        href: `#/${seite.id}`,
        text: seite.label,
        class: seite.id === aktiv ? "aktiv" : null,
      }),
    );
  }
}

async function zeichneSeite() {
  const { id, params } = routeLesen();
  const seite = SEITEN.find((kandidat) => kandidat.id === id) || SEITEN[0];
  zeichneReiter(seite.id);
  const inhalt = leere(document.getElementById("inhalt"));
  const wurzel = el("div");
  inhalt.append(wurzel);
  try {
    await seite.zeichne(wurzel, params);
  } catch (fehler) {
    wurzel.append(ui.fehlerKasten(problemVon(fehler)));
  }
}

/* ---------------------------------------------------------------- Kopfleiste */

const ZUGANGSFELDER = {
  "z-api-key": "apiKey",
  "z-actor": "actorId",
  "z-actor-type": "actorType",
  "z-source": "source",
  "z-correlation": "correlationId",
};

function neueUuid() {
  if (window.crypto && typeof window.crypto.randomUUID === "function") {
    return window.crypto.randomUUID();
  }
  return "00000000-0000-4000-8000-" + String(Date.now()).padStart(12, "0").slice(-12);
}

async function pruefeZugang() {
  const anzeige = document.getElementById("z-stand");
  anzeige.className = "zugang-stand";
  anzeige.textContent = "prüfe …";
  try {
    const gesundheit = await api.hole("/health");
    await api.hole("/customers", { limit: 1 });
    anzeige.classList.add("gut");
    anzeige.textContent = `verbunden · Backend ${gesundheit.version} · ${api.holeZugang().actorType}`;
  } catch (fehler) {
    const problem = problemVon(fehler);
    anzeige.classList.add("schlecht");
    anzeige.textContent = `${problem.status || ""} ${problem.code || "Fehler"}`.trim();
  }
}

function kopfleisteAufbauen() {
  const gemerkt = api.ladeZugang();
  if (!gemerkt.actorId) {
    // Ohne Akteur bleibt das Änderungsprotokoll anonym; einen zu würfeln ist
    // für eine Entwickler-Oberfläche die freundlichste Vorgabe.
    api.setzeZugang({ actorId: neueUuid() });
  }

  const quelle = document.getElementById("z-source");
  const quellen = zustand.aufzaehlungen.Source || ["manual", "agent", "voice", "import", "cad", "system"];
  for (const wert of quellen) {
    quelle.append(el("option", { value: wert, text: wert }));
  }

  const zugang = api.holeZugang();
  for (const [kennung, name] of Object.entries(ZUGANGSFELDER)) {
    const knoten = document.getElementById(kennung);
    knoten.value = zugang[name] || "";
    knoten.addEventListener("input", () => api.setzeZugang({ [name]: knoten.value }));
    knoten.addEventListener("change", () => {
      api.setzeZugang({ [name]: knoten.value });
      pruefeZugang();
    });
  }

  document.getElementById("z-actor-neu").addEventListener("click", () => {
    const feld = document.getElementById("z-actor");
    feld.value = neueUuid();
    api.setzeZugang({ actorId: feld.value });
  });

  document.getElementById("zugang").addEventListener("submit", (ereignis) => {
    ereignis.preventDefault();
    pruefeZugang();
  });
}

/* ---------------------------------------------------------------------- Start */

async function start() {
  api.ladeZugang();
  ui.setzeMeldungsbereich(document.getElementById("meldungen"));

  // Wertelisten und Detailfelder kommen aus der API, nicht aus diesem Code.
  try {
    zustand.aufzaehlungen = await api.ladeAufzaehlungen();
  } catch (fehler) {
    ui.meldeFehler(problemVon(fehler));
  }
  try {
    zustand.detailSchemas = await api.hole("/bookings/detail-schemas");
  } catch (fehler) {
    // Ohne Schlüssel schlägt das fehl; nach Eingabe des Schlüssels klappt es.
    console.warn("Detailfelder der Buchungsarten noch nicht geladen:", fehler);
  }

  kopfleisteAufbauen();
  window.addEventListener("hashchange", zeichneSeite);
  await zeichneSeite();
  await pruefeZugang();
}

start();
