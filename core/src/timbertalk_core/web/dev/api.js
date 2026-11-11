/**
 * Zugriff auf die REST-API.
 *
 * Die Werkbank ist ein Client wie jeder andere: alles läuft über HTTP, nichts
 * über Datenbank oder Service-Schicht. Alle Eigenheiten der API stehen deshalb
 * genau hier und nicht in den Seiten:
 *
 * - Akteur und Schlüssel gehen als Kopfzeilen mit (siehe `KOPFZEILEN`).
 * - Geld und Mengen werden als Zeichenkette gesendet; Gleitkommazahlen weist
 *   das Backend mit 422 ab.
 * - Leere Felder werden weggelassen, nicht als `null` gesendet: die Schemas
 *   sind `extra="forbid"` und die meisten Felder sind nicht nullbar.
 * - Fehler kommen als Problem-JSON (RFC 9457) und werden zu `ProblemFehler`.
 */

const SPEICHER = "timbertalk.dev.headers";

/** Vorgabe des Zugangs. `system` als Akteur-Art, weil nur ein Mensch bestätigen darf. */
const VORGABE = Object.freeze({
  apiKey: "",
  actorId: "",
  actorType: "system",
  source: "manual",
  correlationId: "",
});

/** Zuordnung der gespeicherten Werte auf die Kopfzeilen der API. */
const KOPFZEILEN = Object.freeze({
  apiKey: "X-API-Key",
  actorId: "X-Actor",
  actorType: "X-Actor-Type",
  source: "X-Source",
  correlationId: "X-Correlation-Id",
});

let zugang = { ...VORGABE };

/** Liest den gemerkten Zugang aus dem localStorage. */
export function ladeZugang() {
  try {
    const roh = window.localStorage.getItem(SPEICHER);
    if (roh) {
      zugang = { ...VORGABE, ...JSON.parse(roh) };
    }
  } catch (fehler) {
    console.warn("Zugang konnte nicht gelesen werden:", fehler);
    zugang = { ...VORGABE };
  }
  return { ...zugang };
}

/** Übernimmt geänderte Zugangswerte und merkt sie im localStorage. */
export function setzeZugang(werte) {
  zugang = { ...zugang, ...werte };
  try {
    window.localStorage.setItem(SPEICHER, JSON.stringify(zugang));
  } catch (fehler) {
    console.warn("Zugang konnte nicht gemerkt werden:", fehler);
  }
  return { ...zugang };
}

/** Liefert den aktuellen Zugang. */
export function holeZugang() {
  return { ...zugang };
}

/** Ein Fehler der API, beschrieben als Problem-JSON. */
export class ProblemFehler extends Error {
  constructor(problem) {
    super(problem.detail || problem.title || "Unbekannter Fehler");
    this.name = "ProblemFehler";
    this.problem = problem;
  }
}

function kopfzeilen(mitInhalt) {
  const kopf = {};
  for (const [name, kopfzeile] of Object.entries(KOPFZEILEN)) {
    const wert = (zugang[name] || "").trim();
    if (wert) {
      kopf[kopfzeile] = wert;
    }
  }
  if (mitInhalt) {
    kopf["Content-Type"] = "application/json";
  }
  return kopf;
}

function baueUrl(pfad, query) {
  const url = new URL(pfad, window.location.origin);
  for (const [name, wert] of Object.entries(query || {})) {
    // `false` und `0` sind echte Werte; nur Leeres fällt weg.
    if (wert === undefined || wert === null || wert === "") {
      continue;
    }
    url.searchParams.set(name, String(wert));
  }
  return url;
}

/**
 * Schickt eine Anfrage an die API und liefert den geparsten Körper.
 *
 * Wirft bei jedem Fehler einen `ProblemFehler`; auch dann, wenn die Antwort
 * kein Problem-JSON ist (etwa der 404 von FastAPI) oder das Backend nicht läuft.
 */
export async function anfrage(methode, pfad, { query, body } = {}) {
  const url = baueUrl(pfad, query);
  let antwort;
  try {
    antwort = await fetch(url, {
      method: methode,
      headers: kopfzeilen(body !== undefined),
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (fehler) {
    throw new ProblemFehler({
      title: "Backend nicht erreichbar",
      status: 0,
      code: "netzwerk",
      detail: `${methode} ${url.pathname} ist fehlgeschlagen: ${fehler.message}`,
    });
  }

  const text = await antwort.text();
  let daten = null;
  if (text) {
    try {
      daten = JSON.parse(text);
    } catch {
      daten = null;
    }
  }

  if (!antwort.ok) {
    if (daten && typeof daten === "object" && typeof daten.code === "string") {
      throw new ProblemFehler(daten);
    }
    throw new ProblemFehler({
      title: `HTTP ${antwort.status}`,
      status: antwort.status,
      code: "http_fehler",
      detail:
        daten && typeof daten.detail === "string"
          ? daten.detail
          : text || antwort.statusText || "Keine Antwort des Backends.",
    });
  }

  return daten;
}

export const hole = (pfad, query) => anfrage("GET", pfad, { query });
export const sende = (pfad, body, query) => anfrage("POST", pfad, { body, query });
export const aendere = (pfad, body, query) => anfrage("PATCH", pfad, { body, query });
export const ersetze = (pfad, body, query) => anfrage("PUT", pfad, { body, query });
export const entferne = (pfad, query) => anfrage("DELETE", pfad, { query });

/**
 * Liest die Wertelisten der API aus ihrer OpenAPI-Beschreibung.
 *
 * So steht keine Werteliste doppelt im Browser: FastAPI legt jede Aufzählung
 * unter dem Namen ihrer Python-Klasse ab, etwa `BookingStatus`.
 */
export async function ladeAufzaehlungen() {
  const beschreibung = await hole("/openapi.json");
  const schemas = beschreibung?.components?.schemas || {};
  const aufzaehlungen = {};
  for (const [name, schema] of Object.entries(schemas)) {
    if (Array.isArray(schema.enum)) {
      aufzaehlungen[name] = schema.enum.map((wert) => String(wert));
    }
  }
  return aufzaehlungen;
}
