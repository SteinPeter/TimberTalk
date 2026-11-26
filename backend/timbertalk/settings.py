# Einstellungen des Backends. Die Werte kommen aus der Umgebung oder aus backend/.env.

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Der Ordner backend/. Davon ausgehend liegt die Datenbank immer am selben Platz,
# egal aus welchem Ordner der Server gestartet wird.
BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"


class Settings(BaseSettings):
    """Einstellungen dieser Installation; jeder Wert hat einen brauchbaren Standard."""

    model_config = SettingsConfigDict(
        env_prefix="TIMBERTALK_",
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Adresse der Datenbank. Standard: die SQLite-Datei backend/data/timbertalk.db
    database_url: str = f"sqlite:///{DATA_DIR / 'timbertalk.db'}"

    # Adresse, auf der der Server lauscht.
    host: str = "127.0.0.1"
    port: int = 8000

    # Während der Entwicklung: Vor der ersten Anmeldung zeigt die Anmeldeseite ein Fenster mit den
    # Anmeldedaten (Erst-Konto admin/admin, Standardpasswort). Im Betrieb ausschalten:
    # TIMBERTALK_DEV_LOGIN_HINT=false in backend/.env.
    dev_login_hint: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Liest die Einstellungen einmal und merkt sie sich."""
    return Settings()
