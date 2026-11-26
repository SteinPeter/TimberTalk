# Passwörter und Sitzungsschlüssel – alles, was mit Geheimnissen zu tun hat, steht nur hier.
#
# Passwörter werden nie im Klartext gespeichert, sondern nur als Hash: eine Prüfsumme, aus der
# man das Passwort nicht zurückrechnen kann. Wir nehmen scrypt aus der Python-Standardbibliothek;
# es ist absichtlich langsam, damit Raten teuer wird. Jedes Passwort bekommt ein eigenes Salz
# (Zufallswert), damit zwei gleiche Passwörter verschiedene Hashes ergeben.
#
# Sitzungsschlüssel sind lange Zufallstexte. In der Datenbank steht auch von ihnen nur ein Hash –
# wer die Datenbank-Datei kopiert, kann sich damit nicht anmelden.

import hashlib
import hmac
import secrets

# Kosten für scrypt: n=2**14, r=8, p=1 ist die übliche Empfehlung für Anmeldungen.
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1

# Startpasswörter ohne leicht verwechselbare Zeichen (0/O, 1/l/I), damit man sie gut diktieren kann.
_START_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


def hash_password(password: str) -> str:
    """Macht aus einem Passwort den Text, der in der Datenbank steht."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Prüft, ob password zum gespeicherten Hash passt."""
    try:
        method, n, r, p, salt, digest = stored.split("$")
    except ValueError:
        return False
    if method != "scrypt":
        return False
    candidate = hashlib.scrypt(
        password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p)
    )
    # compare_digest braucht immer gleich lang – so verrät die Zeit nicht, wie viel gestimmt hat.
    return hmac.compare_digest(candidate.hex(), digest)


def new_start_password() -> str:
    """Ein zufälliges Startpasswort wie „k7mq-x2pd“, das man vorlesen und abtippen kann."""
    chars = [secrets.choice(_START_ALPHABET) for _ in range(8)]
    return "".join(chars[:4]) + "-" + "".join(chars[4:])


def new_session_token() -> str:
    """Ein neuer Sitzungsschlüssel für den Browser (43 Zeichen Zufall)."""
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    """Der Hash eines Sitzungsschlüssels, so wie er in der Datenbank steht."""
    return hashlib.sha256(token.encode()).hexdigest()
