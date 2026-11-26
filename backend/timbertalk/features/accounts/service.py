# Die Logik des Features „Benutzerkonten und Rechte“ als einfache Funktionen:
# Konten anlegen und ändern, anmelden und abmelden, Passwörter ändern und zurücksetzen,
# Rechte je Rolle nachschlagen und ändern.
#
# Jede Funktion bekommt als ersten Parameter die Datenbank-Sitzung: session: Session.
# Fehler meldet der Service so, dass api.py daraus eine Antwort mit deutschem Text machen kann:
#   ValueError     – die Angabe passt nicht (422)
#   LookupError    – das Konto gibt es nicht (404)
#   PermissionError – das darf diese Person nicht (403)
#   LoginFailed    – Anmeldung nicht möglich (401)
# Andere Features benutzen dieses Feature über deps.py (wer ist angemeldet, darf er das?).

import re
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, col, delete, select

from timbertalk.features.accounts import security
from timbertalk.features.accounts.models import (
    Account,
    AccountInfo,
    AccountSession,
    Me,
    PermissionInfo,
    Person,
    RoleInfo,
    RoleMatrix,
    RolePermission,
)
from timbertalk.features.accounts.permissions import ADMIN_ROLE, DEFAULTS, PERMISSIONS, ROLES

# So lange bleibt man auf einem Gerät angemeldet (z. B. auf dem Handy auf der Baustelle).
SESSION_DAYS = 30

# Das erste Konto beim allerersten Start. Das Passwort wird bei der ersten Anmeldung ersetzt.
INITIAL_ADMIN_USERNAME = "admin"
INITIAL_ADMIN_PASSWORD = "admin"

MIN_PASSWORD_LENGTH = 8

# Nach so vielen falschen Passwörtern hintereinander ist das Konto so lange gesperrt. Das bremst
# jemanden, der Passwörter durchprobiert. Der Admin kann die Sperre durch Zurücksetzen aufheben.
MAX_FAILED_LOGINS = 5
LOCK_MINUTES = 15

# Erlaubte Zeichen im Anmeldenamen: Kleinbuchstaben, Ziffern, Punkt, Bindestrich, Unterstrich.
_USERNAME_PATTERN = re.compile(r"[a-z0-9._-]+")

# Wird geprüft, wenn es den Anmeldenamen gar nicht gibt – damit die Antwort genauso lange dauert
# und man an der Zeit nicht erkennt, ob ein Name existiert.
_DUMMY_HASH = security.hash_password("timbertalk")

LOGIN_FAILED_TEXT = "Anmeldename, Personalnummer oder Passwort stimmen nicht."


class LoginFailed(Exception):
    """Die Anmeldung hat nicht geklappt. Der Text sagt, warum – ohne zu viel zu verraten."""


def _now() -> datetime:
    """Die aktuelle Zeit in UTC."""
    return datetime.now(UTC)


# --- Eingaben prüfen --------------------------------------------------------------


def _clean_username(username: str) -> str:
    cleaned = username.strip().lower()
    if not cleaned:
        raise ValueError("Bitte einen Anmeldenamen angeben.")
    if not _USERNAME_PATTERN.fullmatch(cleaned):
        raise ValueError(
            "Der Anmeldename darf nur Buchstaben a–z, Ziffern, Punkt, Bindestrich und "
            "Unterstrich enthalten, ohne Leerzeichen."
        )
    return cleaned


def _clean_personnel_number(personnel_number: str | None) -> str | None:
    if personnel_number is None:
        return None
    cleaned = personnel_number.strip()
    return cleaned or None


def _clean_display_name(display_name: str) -> str:
    cleaned = display_name.strip()
    if not cleaned:
        raise ValueError("Bitte einen Namen angeben.")
    return cleaned


def _check_role(role: str) -> None:
    if role not in ROLES:
        raise ValueError(f"Die Rolle „{role}“ gibt es nicht.")


def _check_permission(permission: str) -> None:
    if permission not in PERMISSIONS:
        raise ValueError(f"Das Recht „{permission}“ gibt es nicht.")


def _check_new_password(password: str, username: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Das Passwort braucht mindestens {MIN_PASSWORD_LENGTH} Zeichen.")
    if password.strip().lower() == username:
        raise ValueError("Das Passwort darf nicht der Anmeldename sein.")


def _check_unique(
    session: Session, username: str, personnel_number: str | None, except_id: int | None = None
) -> None:
    """Anmeldename und Personalnummer müssen eindeutig sein – auch untereinander, denn beim
    Anmelden kann man beides ins selbe Feld tippen."""
    for account in session.exec(select(Account)):
        if account.id == except_id:
            continue
        taken = {account.username, account.personnel_number} - {None}
        if username in taken:
            raise ValueError(f"Der Anmeldename „{username}“ ist schon vergeben.")
        if personnel_number is not None and personnel_number in taken:
            raise ValueError(f"Die Personalnummer „{personnel_number}“ ist schon vergeben.")


# --- Konten -----------------------------------------------------------------------


def info(account: Account) -> AccountInfo:
    """Ein Konto für die Anzeige – ohne Passwort-Hash."""
    return AccountInfo(
        id=account.id,
        username=account.username,
        personnel_number=account.personnel_number,
        display_name=account.display_name,
        role=account.role,
        role_label=ROLES.get(account.role, account.role),
        active=account.active,
        must_change_password=account.must_change_password,
        locked_until=account.locked_until,
        last_login_at=account.last_login_at,
    )


def me(session: Session, account: Account) -> Me:
    """Das eigene Konto mit allen Rechten, die es gerade hat."""
    permissions = sorted(role_permissions(session, account.role))
    return Me(**info(account).model_dump(), permissions=permissions)


def list_accounts(session: Session) -> list[AccountInfo]:
    """Alle Konten, nach Namen sortiert – gesperrte stehen mit in der Liste."""
    statement = select(Account).order_by(Account.display_name)
    return [info(account) for account in session.exec(statement)]


def list_people(session: Session) -> list[Person]:
    """Alle aktiven Konten mit Nummer und Name, nach Namen sortiert – für andere Features,
    z. B. die Plantafel im Kalender (F8). Ohne Rolle, Anmeldename, Personalnummer und Rechte."""
    statement = select(Account).where(col(Account.active).is_(True)).order_by(Account.display_name)
    return [
        Person(id=account.id, display_name=account.display_name)
        for account in session.exec(statement)
    ]


def get_account(session: Session, account_id: int) -> Account:
    account = session.get(Account, account_id)
    if account is None:
        raise LookupError(f"Das Konto {account_id} gibt es nicht.")
    return account


def create_account(
    session: Session,
    username: str,
    display_name: str,
    role: str,
    personnel_number: str | None = None,
    start_password: str | None = None,
    acting: Account | None = None,
) -> tuple[Account, str]:
    """Legt ein Konto an. Gibt das Konto und sein Startpasswort zurück.

    Ohne start_password denkt sich TimberTalk eines aus. Bei der ersten Anmeldung muss die
    Person es durch ein eigenes ersetzen. acting ist das Konto, das gerade anlegt.
    """
    username = _clean_username(username)
    personnel_number = _clean_personnel_number(personnel_number)
    display_name = _clean_display_name(display_name)
    _check_role(role)
    _check_admin_change(acting, role)
    _check_unique(session, username, personnel_number)
    start_password = (start_password or "").strip() or security.new_start_password()
    _check_new_password(start_password, username)

    account = Account(
        username=username,
        personnel_number=personnel_number,
        display_name=display_name,
        role=role,
        password_hash=security.hash_password(start_password),
        must_change_password=True,
        created_at=_now(),
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account, start_password


def update_account(
    session: Session,
    account_id: int,
    display_name: str,
    role: str,
    personnel_number: str | None,
    active: bool,
    acting: Account,
) -> Account:
    """Ändert Name, Rolle, Personalnummer und ob das Konto gesperrt ist."""
    account = get_account(session, account_id)
    display_name = _clean_display_name(display_name)
    personnel_number = _clean_personnel_number(personnel_number)
    _check_role(role)
    _check_admin_change(acting, account.role)
    _check_admin_change(acting, role)
    _check_unique(session, account.username, personnel_number, except_id=account.id)
    if account.id == acting.id and not active:
        raise ValueError("Das eigene Konto kann man nicht sperren.")
    if account.id == acting.id and role != account.role:
        raise ValueError("Die eigene Rolle kann man nicht ändern.")
    if account.role == ADMIN_ROLE and (role != ADMIN_ROLE or not active):
        _check_not_last_admin(session, account)

    account.display_name = display_name
    account.role = role
    account.personnel_number = personnel_number
    account.active = active
    session.add(account)
    if not active:
        _end_sessions(session, account.id)
    session.commit()
    session.refresh(account)
    return account


def reset_password(
    session: Session, account_id: int, start_password: str | None, acting: Account
) -> str:
    """Vergibt ein neues Startpasswort (z. B. wenn jemand seines vergessen hat).

    Alle Anmeldungen des Kontos enden; bei der nächsten Anmeldung muss die Person ein eigenes
    Passwort festlegen. Gibt das Startpasswort zurück.
    """
    account = get_account(session, account_id)
    _check_admin_change(acting, account.role)
    start_password = (start_password or "").strip() or security.new_start_password()
    _check_new_password(start_password, account.username)
    account.password_hash = security.hash_password(start_password)
    account.must_change_password = True
    account.failed_logins = 0
    account.locked_until = None  # Zurücksetzen hebt auch eine Sperre wegen Fehlversuchen auf
    session.add(account)
    _end_sessions(session, account.id)
    session.commit()
    return start_password


def _check_admin_change(acting: Account | None, role: str) -> None:
    """Admin-Konten anlegen, ändern oder zurücksetzen darf nur ein Admin."""
    if role == ADMIN_ROLE and acting is not None and acting.role != ADMIN_ROLE:
        raise PermissionError("Admin-Konten kann nur ein Admin anlegen oder ändern.")


def _check_not_last_admin(session: Session, account: Account) -> None:
    statement = select(Account).where(
        Account.role == ADMIN_ROLE, col(Account.active).is_(True), Account.id != account.id
    )
    if session.exec(statement).first() is None:
        raise ValueError("Es muss immer mindestens ein aktives Admin-Konto geben.")


def ensure_initial_admin(session: Session) -> bool:
    """Legt beim allerersten Start das Konto „admin“ mit dem Passwort „admin“ an.

    Gibt True zurück, wenn es angelegt wurde. Gibt es schon ein Konto, passiert nichts.
    """
    if session.exec(select(Account)).first() is not None:
        return False
    session.add(
        Account(
            username=INITIAL_ADMIN_USERNAME,
            display_name="Admin",
            role=ADMIN_ROLE,
            password_hash=security.hash_password(INITIAL_ADMIN_PASSWORD),
            must_change_password=True,
            created_at=_now(),
        )
    )
    session.commit()
    return True


# --- Anmelden und Passwort ----------------------------------------------------------


def _find_for_login(session: Session, identifier: str) -> Account | None:
    text = identifier.strip()
    if not text:
        return None
    by_name = select(Account).where(Account.username == text.lower())
    account = session.exec(by_name).first()
    if account is None:
        by_number = select(Account).where(Account.personnel_number == text)
        account = session.exec(by_number).first()
    return account


def login(session: Session, identifier: str, password: str) -> tuple[Account, str]:
    """Meldet mit Anmeldename oder Personalnummer an. Gibt Konto und Sitzungsschlüssel zurück."""
    account = _find_for_login(session, identifier)
    if account is None:
        security.verify_password(password, _DUMMY_HASH)  # gleich lange rechnen, siehe oben
        raise LoginFailed(LOGIN_FAILED_TEXT)
    now = _now()
    password_ok = security.verify_password(password, account.password_hash)
    if _is_locked(account, now):
        raise LoginFailed(_locked_text(account))
    if not password_ok:
        _count_failed_login(session, account, now)
        if _is_locked(account, now):
            raise LoginFailed(_locked_text(account))
        raise LoginFailed(LOGIN_FAILED_TEXT)
    if not account.active:
        raise LoginFailed("Dieses Konto ist gesperrt. Bitte beim Admin melden.")

    token = security.new_session_token()
    account.failed_logins = 0
    account.locked_until = None
    session.add(
        AccountSession(
            token_hash=security.token_hash(token),
            account_id=account.id,
            created_at=now,
            expires_at=now + timedelta(days=SESSION_DAYS),
        )
    )
    account.last_login_at = now
    session.add(account)
    session.commit()
    session.refresh(account)
    return account, token


def _is_locked(account: Account, now: datetime) -> bool:
    return account.locked_until is not None and _aware(account.locked_until) > now


def _aware(moment: datetime) -> datetime:
    """SQLite liefert Zeiten je nach Weg mit oder ohne Zeitzone; gespeichert ist immer UTC."""
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def _locked_text(account: Account) -> str:
    until = _aware(account.locked_until).astimezone().strftime("%H:%M")
    return (
        f"Zu viele falsche Passwörter. Das Konto ist bis {until} Uhr gesperrt – "
        "oder der Admin setzt das Passwort zurück."
    )


def _count_failed_login(session: Session, account: Account, now: datetime) -> None:
    """Zählt ein falsches Passwort. Beim MAX_FAILED_LOGINS-ten wird das Konto kurz gesperrt."""
    account.failed_logins += 1
    if account.failed_logins >= MAX_FAILED_LOGINS:
        account.locked_until = now + timedelta(minutes=LOCK_MINUTES)
        account.failed_logins = 0
    session.add(account)
    session.commit()
    session.refresh(account)


def logout(session: Session, token: str) -> None:
    """Beendet die Anmeldung, zu der dieser Schlüssel gehört."""
    statement = delete(AccountSession).where(
        AccountSession.token_hash == security.token_hash(token)
    )
    session.exec(statement)
    session.commit()


def account_for_token(session: Session, token: str) -> Account | None:
    """Das angemeldete Konto zu einem Sitzungsschlüssel – oder None, wenn er nicht (mehr) gilt."""
    statement = select(AccountSession).where(
        AccountSession.token_hash == security.token_hash(token)
    )
    stored = session.exec(statement).first()
    if stored is None:
        return None
    if stored.expires_at <= _now():
        session.delete(stored)
        session.commit()
        return None
    account = session.get(Account, stored.account_id)
    if account is None or not account.active:
        return None
    return account


def change_own_password(
    session: Session, account: Account, old_password: str, new_password: str, keep_token: str
) -> None:
    """Setzt ein neues eigenes Passwort. Alle anderen Anmeldungen dieses Kontos enden."""
    if not security.verify_password(old_password, account.password_hash):
        raise ValueError("Das bisherige Passwort stimmt nicht.")
    _check_new_password(new_password, account.username)
    if security.verify_password(new_password, account.password_hash):
        raise ValueError("Das neue Passwort muss sich vom bisherigen unterscheiden.")
    account.password_hash = security.hash_password(new_password)
    account.must_change_password = False
    session.add(account)
    session.exec(
        delete(AccountSession).where(
            AccountSession.account_id == account.id,
            AccountSession.token_hash != security.token_hash(keep_token),
        )
    )
    session.commit()
    session.refresh(account)


def _end_sessions(session: Session, account_id: int) -> None:
    session.exec(delete(AccountSession).where(AccountSession.account_id == account_id))


# --- Rechte -------------------------------------------------------------------------


def role_permissions(session: Session, role: str) -> set[str]:
    """Alle Rechte einer Rolle: die Voreinstellung, darauf die geänderten Häkchen."""
    if role == ADMIN_ROLE:
        return set(PERMISSIONS)
    allowed = set(DEFAULTS.get(role, set()))
    for change in session.exec(select(RolePermission).where(RolePermission.role == role)):
        if change.allowed:
            allowed.add(change.permission)
        else:
            allowed.discard(change.permission)
    return allowed & set(PERMISSIONS)


def has_permission(session: Session, account: Account, permission: str) -> bool:
    """Darf dieses Konto das? permission ist ein Schlüssel aus permissions.PERMISSIONS."""
    return permission in role_permissions(session, account.role)


def role_matrix(session: Session) -> RoleMatrix:
    """Alle Rollen mit ihren Rechten – für die Tabelle „Rollen und Rechte“."""
    return RoleMatrix(
        roles=[
            RoleInfo(
                role=role,
                label=label,
                editable=role != ADMIN_ROLE,
                permissions=sorted(role_permissions(session, role)),
            )
            for role, label in ROLES.items()
        ],
        permissions=[
            PermissionInfo(permission=key, label=text) for key, text in PERMISSIONS.items()
        ],
    )


def set_role_permission(
    session: Session, role: str, permission: str, allowed: bool, acting: Account
) -> RoleMatrix:
    """Setzt oder entfernt ein Häkchen. Gibt die ganze Tabelle neu zurück."""
    _check_role(role)
    _check_permission(permission)
    if role == ADMIN_ROLE:
        raise ValueError("Der Admin hat immer alle Rechte.")
    if role == acting.role and permission == "accounts.manage" and not allowed:
        raise ValueError("Das Recht, Konten zu verwalten, kann man der eigenen Rolle nicht nehmen.")
    change = session.get(RolePermission, (role, permission))
    if change is None:
        change = RolePermission(role=role, permission=permission, allowed=allowed)
    change.allowed = allowed
    session.add(change)
    session.commit()
    return role_matrix(session)
