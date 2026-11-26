// Die Liste aller Abschnitte im Reiter "Einstellungen", in der Reihenfolge der Seitenleiste.
// Jeder Abschnitt ist eine eigene Datei sections/<feature>.js oder sections/<feature>-<thema>.js.
// Einen Abschnitt ergänzen: eine import-Zeile und einen Eintrag in SECTIONS.
// Ein Abschnitt mit `permission` erscheint nur für Konten mit diesem Recht (F10).

import * as accountsManage from "./sections/accounts-manage.js";
import * as accountsOwn from "./sections/accounts-own.js";
import * as accountsRoles from "./sections/accounts-roles.js";
import * as audit from "./sections/audit.js";
import * as materialsCompany from "./sections/materials-company.js";
import * as materialsMaster from "./sections/materials-master.js";
import * as planningResources from "./sections/planning-resources.js";

export const SECTIONS = [
  accountsOwn,
  materialsCompany,
  materialsMaster,
  planningResources,
  accountsManage,
  accountsRoles,
  audit,
];
