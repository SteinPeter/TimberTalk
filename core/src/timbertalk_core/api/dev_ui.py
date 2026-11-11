"""Auslieferung der Entwickler-Oberfläche („Werkbank“) unter `/dev`.

Die Werkbank ist ein Client wie jeder andere: statische Dateien, die ausschließlich
über die REST-API sprechen. Sie kennt weder Datenbank noch Service-Schicht.

Sie wird nur in der lokalen Installation ausgeliefert. In allen anderen Umgebungen
wird nichts eingehängt, `/dev` antwortet dann mit dem gewöhnlichen 404.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from timbertalk_core.config import Settings

DEV_UI_PREFIX = "/dev"
"""Pfad, unter dem die Werkbank erreichbar ist."""

DEV_UI_NAME = "dev"
"""Name des Mounts; über ihn lässt sich der Pfad in Tests nachschlagen."""


def dev_ui_dir() -> Path:
    """Liefert das Verzeichnis mit den Dateien der Werkbank.

    Die Dateien liegen innerhalb des Pakets, damit sie mit einer Installation
    mitkommen und nicht vom Arbeitsverzeichnis abhängen.
    """
    return Path(__file__).resolve().parent.parent / "web" / "dev"


def mount_dev_ui(app: FastAPI, settings: Settings) -> bool:
    """Hängt die Werkbank unter `/dev` ein, wenn die Einstellungen es erlauben.

    Ein Mount und keine Route: ausgelieferte Dateien gehören nicht in die
    OpenAPI-Beschreibung der API.

    Parameter:
        app: die Anwendung, an die die Werkbank gehängt wird.
        settings: Einstellungen dieser Installation; `dev_ui_enabled` entscheidet.
    """
    if not settings.dev_ui_enabled:
        return False
    verzeichnis = dev_ui_dir()
    if not verzeichnis.is_dir():
        # Fehlt das Verzeichnis, ist die Installation unvollständig. Das darf den
        # Start des Backends nicht verhindern: die API ist die Hauptsache.
        return False
    app.mount(
        DEV_UI_PREFIX,
        StaticFiles(directory=verzeichnis, html=True),
        name=DEV_UI_NAME,
    )
    return True
