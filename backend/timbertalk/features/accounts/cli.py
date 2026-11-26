# Notfall-Befehl für den Rechner im Betrieb: ein Passwort zurücksetzen, ohne angemeldet zu sein.
#
# Wofür: Hat das einzige Admin-Konto sein Passwort vergessen, kann es in TimberTalk niemand mehr
# zurücksetzen. Wer direkt am Rechner mit der Datenbank sitzt, darf das hier:
#
#     uv run python -m timbertalk.features.accounts.cli admin
#
# Das Konto bekommt das Standardpasswort, eine Sperre nach Fehlversuchen wird aufgehoben, alle
# Anmeldungen enden. Bei der nächsten Anmeldung muss ein eigenes Passwort festgelegt werden.
# Das Passwort selbst wird nicht ausgegeben – es ist das Standardpasswort aus den Einstellungen.

import sys

from sqlmodel import Session, select

from timbertalk.db import create_tables, get_engine
from timbertalk.features import load_features
from timbertalk.features.accounts import service
from timbertalk.features.accounts.models import Account


def reset(identifier: str) -> str:
    """Setzt das Konto (Anmeldename oder Personalnummer) auf das Standardpasswort zurück."""
    load_features()
    create_tables()
    with Session(get_engine()) as session:
        text = identifier.strip()
        account = session.exec(select(Account).where(Account.username == text.lower())).first()
        if account is None:
            account = session.exec(select(Account).where(Account.personnel_number == text)).first()
        if account is None:
            raise LookupError(f"Ein Konto „{identifier}“ gibt es nicht.")
        account.active = True  # auch ein versehentlich gesperrtes Konto kommt wieder rein
        session.add(account)
        session.commit()
        # acting=None: Der Befehl am Rechner selbst darf auch Admin-Konten zurücksetzen.
        service.reset_password(session, account.id, None, acting=None)
        return account.username


def main() -> None:
    if len(sys.argv) != 2:
        print("Aufruf: uv run python -m timbertalk.features.accounts.cli <anmeldename>")
        sys.exit(2)
    try:
        username = reset(sys.argv[1])
    except LookupError as error:
        print(error)
        sys.exit(1)
    print(
        f"Das Konto „{username}“ hat wieder das Standardpasswort (siehe Anmeldeseite → "
        "„Anmeldedaten für die Entwicklung anzeigen“ oder Einstellungen → Benutzerkonten). "
        "Bei der nächsten Anmeldung muss ein eigenes Passwort festgelegt werden."
    )


if __name__ == "__main__":
    main()
