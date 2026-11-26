# Die Rollen und Rechte von TimberTalk an einer Stelle.
#
# Eine Rolle ist die Art des Kontos (Admin, Meister, Geselle …). Ein Recht ist eine Sache, die man
# tun oder sehen darf (z. B. „Preise sehen“). Welche Rolle welches Recht hat, steht hier als
# Voreinstellung. Wer „accounts.manage“ hat (Admin und Chef), ändert das je Rolle in den
# Einstellungen („Rollen und Rechte“, Tabelle accounts_role_permission) und für einzelne Konten
# („Benutzerkonten → Bearbeiten“, Tabelle accounts_user_permission). Für ein Konto gilt:
# Voreinstellung der Rolle → geänderte Häkchen der Rolle → Ausnahmen für dieses Konto.
#
# Ein neues Recht für ein Feature: eine Zeile in PERMISSIONS und das Recht in DEFAULTS bei den
# Rollen eintragen, die es von Anfang an haben sollen.

# Rollen: Schlüssel im Code → Name auf dem Bildschirm. Die Reihenfolge ist die der Anzeige.
ROLES: dict[str, str] = {
    "admin": "Admin",
    "owner": "Chef",
    "master": "Meister",
    "office": "Verwaltung",
    "journeyman": "Geselle",
    "apprentice": "Azubi",
}

# Der Admin ist das technische Konto (Einrichtung, Konten). Das Recht, Konten zu verwalten, kann
# man ihm nie nehmen – so sperrt sich der Betrieb nie selbst aus. Alles andere ist änderbar.
ADMIN_ROLE = "admin"

# Rechte, die eine Rolle immer hat – weder für die Rolle noch für ein einzelnes Konto abwählbar.
LOCKED: dict[str, set[str]] = {"admin": {"accounts.manage"}}

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
    "audit.view": "Änderungsprotokoll sehen",  # F11
    "hours.book_own": "Eigene Stunden buchen",  # F4
    "hours.view_all": "Stunden aller Mitarbeitenden sehen",  # F4
    "hours.manage": "Stunden für andere buchen und löschen",  # F4
}

# Voreinstellung: welche Rolle welches Recht hat, solange niemand etwas ändert.
# Urlaubsanträge entscheidet in der Voreinstellung nur der Chef.
DEFAULTS: dict[str, set[str]] = {
    "admin": set(PERMISSIONS) - {"calendar.approve_absence"},
    "owner": set(PERMISSIONS),
    "master": {
        "finance.view",
        "materials.edit",
        "bookings.create",
        "calendar.view_all",
        "calendar.dispatch",
        "calendar.request_absence",
        "hours.book_own",
        "hours.view_all",
    },
    "office": {
        "finance.view",
        "finance.edit",
        "materials.edit",
        "bookings.create",
        "calendar.view_all",
        "calendar.dispatch",
        "calendar.request_absence",
        "hours.book_own",
        "hours.view_all",
        "hours.manage",
    },
    "journeyman": {
        "bookings.create",
        "calendar.view_all",
        "calendar.request_absence",
        "hours.book_own",
    },
    "apprentice": {
        "bookings.create",
        "calendar.view_all",
        "calendar.request_absence",
        "hours.book_own",
    },
}
