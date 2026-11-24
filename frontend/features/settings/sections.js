// Die Liste aller Abschnitte im Reiter "Einstellungen", in der Reihenfolge der Seitenleiste.
// Jeder Abschnitt ist eine eigene Datei sections/<feature>.js oder sections/<feature>-<thema>.js.
// Einen Abschnitt ergänzen: eine import-Zeile und einen Eintrag in SECTIONS.

import * as materialsCompany from "./sections/materials-company.js";
import * as materialsMaster from "./sections/materials-master.js";

export const SECTIONS = [materialsCompany, materialsMaster];
