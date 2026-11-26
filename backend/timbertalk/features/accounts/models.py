# Tabellen des Features „Benutzerkonten und Rechte“ als SQLModel-Klassen, dazu die kleinen
# Antwort- und Eingabeklassen der API. Alle Tabellennamen beginnen mit `accounts_`.
#
# Zeiten sind immer UTC mit Zeitzone; die Oberfläche zeigt sie in Ortszeit an.

from datetime import datetime

from sqlmodel import Field, SQLModel

# --- Tabellen -------------------------------------------------------------------


class Account(SQLModel, table=True):
    """Ein Benutzerkonto. Angemeldet wird mit Anmeldename oder Personalnummer."""

    __tablename__ = "accounts_account"

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)  # immer klein geschrieben, z. B. „m.berger“
    personnel_number: str | None = Field(default=None, unique=True, index=True)  # z. B. „017“
    display_name: str  # z. B. „Max Berger“
    role: str  # Schlüssel aus permissions.ROLES, z. B. „journeyman“
    password_hash: str  # nie das Passwort selbst, siehe security.py
    must_change_password: bool = True  # True: bei der nächsten Anmeldung eigenes Passwort setzen
    active: bool = True  # False: gesperrt, Anmeldung nicht möglich
    failed_logins: int = 0  # falsche Passwörter hintereinander, siehe service.MAX_FAILED_LOGINS
    locked_until: datetime | None = None  # nach zu vielen Fehlversuchen kurz gesperrt bis dahin
    photo: str | None = None  # Foto als „data:image/jpeg;base64,…“-Text, klein (256 × 256)
    created_at: datetime
    last_login_at: datetime | None = None


class AccountSession(SQLModel, table=True):
    """Eine Anmeldung auf einem Gerät. Der Browser hält den Schlüssel, hier steht sein Hash."""

    __tablename__ = "accounts_session"

    id: int | None = Field(default=None, primary_key=True)
    token_hash: str = Field(unique=True, index=True)
    account_id: int = Field(foreign_key="accounts_account.id", index=True)
    created_at: datetime
    expires_at: datetime


class Setting(SQLModel, table=True):
    """Eine Einstellung der Kontenverwaltung, z. B. das Standardpasswort für neue Konten."""

    __tablename__ = "accounts_setting"

    key: str = Field(primary_key=True)
    value: str


class UserPermission(SQLModel, table=True):
    """Eine Ausnahme für ein einzelnes Konto: dieses Recht ja oder nein, egal was die Rolle sagt."""

    __tablename__ = "accounts_user_permission"

    account_id: int = Field(foreign_key="accounts_account.id", primary_key=True)
    permission: str = Field(primary_key=True)
    allowed: bool


class RolePermission(SQLModel, table=True):
    """Ein geändertes Häkchen in „Rollen und Rechte“. Fehlt die Zeile, gilt die Voreinstellung."""

    __tablename__ = "accounts_role_permission"

    role: str = Field(primary_key=True)
    permission: str = Field(primary_key=True)
    allowed: bool


# --- Antworten und Eingaben (keine Tabellen) -------------------------------------


class AccountInfo(SQLModel):
    """Ein Konto, wie die Oberfläche es sieht – ohne Passwort-Hash."""

    id: int
    username: str
    personnel_number: str | None
    display_name: str
    role: str
    role_label: str
    active: bool
    must_change_password: bool
    locked_until: datetime | None  # gesetzt und in der Zukunft: wegen Fehlversuchen kurz gesperrt
    last_login_at: datetime | None
    photo: str | None


class Person(SQLModel):
    """Eine Person für Listen anderer Features (z. B. Zeilen im Kalender): nur Nummer und Name.

    Die Rolle steht absichtlich nicht dabei – sie sieht nur der Admin in der Kontenverwaltung.
    """

    id: int
    display_name: str


class Me(AccountInfo):
    """Das eigene Konto mit der Liste der Rechte, nach denen die Oberfläche sich richtet."""

    permissions: list[str]


class CreatedAccount(SQLModel):
    """Antwort nach dem Anlegen: das Konto und sein Startpasswort (das Standardpasswort)."""

    account: AccountInfo
    start_password: str


class StartPassword(SQLModel):
    """Antwort nach dem Zurücksetzen – und beim Lesen oder Ändern des Standardpassworts."""

    start_password: str


class RoleInfo(SQLModel):
    """Eine Rolle mit ihren Rechten, für die Tabelle „Rollen und Rechte“."""

    role: str
    label: str
    editable: bool  # ob sich Häkchen dieser Rolle ändern lassen
    permissions: list[str]
    locked: list[str]  # Rechte, die diese Rolle immer hat (z. B. Admin: Konten verwalten)


class AccountPermission(SQLModel):
    """Ein Recht eines Kontos: was die Rolle sagt, was gilt, und ob es eine Ausnahme ist."""

    permission: str
    label: str
    from_role: bool  # hätte die Person es über ihre Rolle?
    allowed: bool  # gilt jetzt für sie
    overridden: bool  # Ausnahme nur für dieses Konto
    locked: bool  # nicht abwählbar


class DemoPerson(SQLModel):
    """Ein Konto, als das man sich im Demo-Modus mit einem Klick anmelden kann."""

    id: int
    display_name: str
    role_label: str


class LoginHint(SQLModel):
    """Anmeldedaten für die Entwicklung – nur mit TIMBERTALK_DEV_LOGIN_HINT."""

    initial_admin: bool  # gilt noch admin / admin?
    standard_password: str  # damit melden sich neue Konten das erste Mal an


class LoginInfo(SQLModel):
    """Was die Anmeldeseite vorher wissen muss (ohne Anmeldung abrufbar)."""

    demo_mode: bool
    demo_account_id: int | None  # als wer man automatisch angemeldet wird
    demo_people: list[DemoPerson]  # nur im Demo-Modus gefüllt
    hint: LoginHint | None  # nur während der Entwicklung


class DemoModeIn(SQLModel):
    """Eingabe und Antwort: Demo-Modus an/aus und als wen automatisch angemeldet wird."""

    enabled: bool
    account_id: int | None = None


class DemoLoginIn(SQLModel):
    """Eingabe: im Demo-Modus anmelden – ohne account_id als das voreingestellte Konto."""

    account_id: int | None = None


class UserPermissionIn(SQLModel):
    """Eingabe: Ausnahme setzen (True/False) oder entfernen (None = wie die Rolle)."""

    allowed: bool | None


class PermissionInfo(SQLModel):
    """Ein Recht mit seiner Beschreibung."""

    permission: str
    label: str


class RoleMatrix(SQLModel):
    """Alle Rollen und alle Rechte – daraus baut die Oberfläche die Tabelle mit Häkchen."""

    roles: list[RoleInfo]
    permissions: list[PermissionInfo]


class LoginIn(SQLModel):
    """Eingabe: Anmeldename oder Personalnummer und Passwort."""

    identifier: str
    password: str


class PasswordChangeIn(SQLModel):
    """Eingabe: das bisherige und das neue eigene Passwort."""

    old_password: str
    new_password: str


class AccountIn(SQLModel):
    """Eingabe: ein neues Konto. Ohne Startpasswort bekommt es das Standardpasswort."""

    username: str
    display_name: str
    role: str
    personnel_number: str | None = None
    start_password: str | None = None


class AccountUpdateIn(SQLModel):
    """Eingabe: geänderte Angaben eines Kontos. Anmeldename und Passwort ändern sich hier nicht."""

    display_name: str
    role: str
    personnel_number: str | None = None
    active: bool = True


class ResetPasswordIn(SQLModel):
    """Eingabe: Passwort zurücksetzen. Ohne Startpasswort gilt wieder das Standardpasswort."""

    start_password: str | None = None


class PhotoIn(SQLModel):
    """Eingabe: ein Foto als „data:image/…;base64,…“-Text – oder None, um es zu entfernen."""

    photo: str | None


class PermissionIn(SQLModel):
    """Eingabe: ein Häkchen in „Rollen und Rechte“ setzen oder entfernen."""

    allowed: bool
