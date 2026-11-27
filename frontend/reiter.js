// Die Liste aller Reiter, in der Reihenfolge der Reiterleiste.
// Jeder Reiter ist eine eigene Datei unter features/<id>/<id>.js.
// Einen Reiter ergänzen: eine import-Zeile und einen Eintrag in REITER.

import * as start from "./features/start/start.js";
import * as planning from "./features/planning/planning.js";
import * as projects from "./features/projects/projects.js";
import * as customers from "./features/customers/customers.js";
import * as bookings from "./features/bookings/bookings.js";
import * as employees from "./features/employees/employees.js";
import * as timeaccount from "./features/timeaccount/timeaccount.js";
import * as settings from "./features/settings/settings.js";

export const REITER = [
  start,
  planning,
  projects,
  customers,
  bookings,
  timeaccount,
  employees,
  settings,
];
