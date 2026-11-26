# Die Rollen und Rechte von TimberTalk an einer Stelle.
#
# Eine Rolle ist die Art des Kontos (Admin, Meister, Geselle …). Ein Recht ist eine Sache, die man
# tun oder sehen darf (z. B. „Preise sehen“). Welche Rolle welches Recht hat, steht hier als
# Voreinstellung. Der Admin (in der Regel der Chef) kann das in den Einstellungen ändern
# („Rollen und Rechte“) – ebenso jede Rolle, der er das Recht „accounts.manage“ gibt;
# geänderte Häkchen speichert service.py in der Tabelle accounts_role_permission.
#
# Ein neues Recht für ein Feature: eine Zeile in PERMISSIONS und das Recht in DEFAULTS bei den
# Rollen eintragen, die es von Anfang an haben sollen.

# Rollen: Schlüssel im Code → Name auf dem Bildschirm. Die Reihenfolge ist die der Anzeige.
ROLES: dict[str, str] = {
    "admin": "Admin",
    "master": "Meister",
    "office": "Verwaltung",
    "journeyman": "Geselle",
    "apprentice": "Azubi",
}

# Der Admin hat immer alle Rechte. Seine Häkchen lassen sich nicht abwählen – so kann sich der
# Betrieb nie selbst aus der Kontenverwaltung aussperren.
ADMIN_ROLE = "admin"

# Rechte: Schlüssel im Code → Beschreibung auf dem Bildschirm.
PERMISSIONS: dict[str, str] = {
    "accounts.manage": "Konten verwalten, Passwörter zurücksetzen, Rechte ändern",
    "finance.view": "Preise, Stundensätze und Projektkosten sehen",
    "finance.edit": "Preise, Stundensätze und Firmendaten ändern",
    "materials.edit": "Materialstamm pflegen",
    "bookings.create": "Material und Fahrten buchen",
    "calendar.view_all": "Kalender aller Mitarbeitenden sehen",  # F8; ohne: nur den eigenen
    "calendar.dispatch": "Termine für alle planen und ändern",  # F8
    "calendar.request_absence": "Urlaub beantragen",  # F8
    "calendar.approve_absence": "Urlaubsanträge genehmigen oder ablehnen",  # F8
}

# Voreinstellung: welche Rolle welches Recht hat, solange niemand etwas ändert.
DEFAULTS: dict[str, set[str]] = {
    "admin": set(PERMISSIONS),
    "master": {
        "finance.view",
        "materials.edit",
        "bookings.create",
        "calendar.view_all",
        "calendar.dispatch",
        "calendar.request_absence",
    },
    "office": {
        "finance.view",
        "finance.edit",
        "materials.edit",
        "bookings.create",
        "calendar.view_all",
        "calendar.dispatch",
        "calendar.request_absence",
    },
    "journeyman": {"bookings.create", "calendar.view_all", "calendar.request_absence"},
    "apprentice": {"bookings.create", "calendar.view_all", "calendar.request_absence"},
}
