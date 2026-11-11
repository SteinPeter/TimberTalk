"""Konfiguration des Backends, gelesen aus Umgebung und `.env`."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Einstellungen der lokalen Installation; Quelle ist die Umgebung bzw. `.env`."""

    model_config = SettingsConfigDict(
        env_prefix="TIMBERTALK_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["local", "test", "production"] = "local"
    """Betriebsart der Installation."""

    data_dir: Path = Path("data")
    """Datenverzeichnis für Datenbank und Belege, relativ zum Arbeitsverzeichnis erlaubt."""

    database_url: str = "sqlite+pysqlite:///data/timbertalk.db"
    """SQLAlchemy-URL der Datenbank; SQLite ist Standard, Postgres wird unterstützt."""

    api_key: str = Field(default="change-me")
    """Platzhalter-API-Schlüssel; echte Benutzeranmeldung kommt später."""

    sql_echo: bool = False
    """Wenn wahr, werden SQL-Anweisungen protokolliert (nur zur Fehlersuche)."""

    dev_ui: bool | None = None
    """Entwickler-Oberfläche erzwingen (wahr) oder abschalten (falsch); ohne Angabe nur in `local`."""

    @property
    def attachments_dir(self) -> Path:
        """Verzeichnis für Belege und Fotos, immer unterhalb des Datenverzeichnisses."""
        return self.data_dir / "attachments"

    @property
    def dev_ui_enabled(self) -> bool:
        """Sagt, ob die Entwickler-Oberfläche unter `/dev` ausgeliefert wird.

        Vorgabe ist die Betriebsart: nur die lokale Installation zeigt sie. `dev_ui`
        übersteuert das in beide Richtungen, damit sie sich auch lokal abschalten lässt.
        """
        if self.dev_ui is not None:
            return self.dev_ui
        return self.environment == "local"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Liefert die zwischengespeicherten Einstellungen des Prozesses."""
    return Settings()
