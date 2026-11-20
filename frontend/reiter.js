// Die Liste aller Reiter, in der Reihenfolge der Reiterleiste.
// Jeder Reiter ist eine eigene Datei unter features/<id>/<id>.js.
// Einen Reiter ergänzen: eine import-Zeile und einen Eintrag in REITER.

import * as start from "./features/start/start.js";
import * as kalender from "./features/kalender/kalender.js";
import * as projekte from "./features/projekte/projekte.js";
import * as kunden from "./features/kunden/kunden.js";
import * as buchungen from "./features/buchungen/buchungen.js";
import * as einstellungen from "./features/einstellungen/einstellungen.js";

export const REITER = [
  start,
  kalender,
  projekte,
  kunden,
  buchungen,
  einstellungen,
];
