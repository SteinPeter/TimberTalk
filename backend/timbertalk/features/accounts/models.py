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
    last_login_at: datetime | None


class Me(AccountInfo):
    """Das eigene Konto mit der Liste der Rechte, nach denen die Oberfläche sich richtet."""

    permissions: list[str]


class CreatedAccount(SQLModel):
    """Antwort nach dem Anlegen: das Konto und sein Startpasswort (wird nur dieses Mal gezeigt)."""

    account: AccountInfo
    start_password: str


class StartPassword(SQLModel):
    """Antwort nach dem Zurücksetzen: das neue Startpasswort (wird nur dieses Mal gezeigt)."""

    start_password: str


class RoleInfo(SQLModel):
    """Eine Rolle mit ihren Rechten, für die Tabelle „Rollen und Rechte“."""

    role: str
    label: str
    editable: bool  # False beim Admin: er hat immer alle Rechte
    permissions: list[str]


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
    """Eingabe: ein neues Konto. Ohne Startpasswort denkt sich TimberTalk eines aus."""

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
    """Eingabe: Passwort zurücksetzen. Ohne Startpasswort denkt sich TimberTalk eines aus."""

    start_password: str | None = None


class PermissionIn(SQLModel):
    """Eingabe: ein Häkchen in „Rollen und Rechte“ setzen oder entfernen."""

    allowed: bool
