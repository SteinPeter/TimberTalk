# Hier liegt je Feature ein eigener Ordner mit models.py, service.py, api.py und test_<name>.py.
# Diese Datei findet die Feature-Ordner selbst. Ein neues Feature muss sich deshalb nirgends
# eintragen – weder in main.py noch hier. Es braucht nur eine (leere) __init__.py im Ordner.

import importlib
import pkgutil
from types import ModuleType

from fastapi import APIRouter


def feature_names(package: str = __name__) -> list[str]:
    """Die Namen aller Feature-Ordner, alphabetisch. Ordner ohne __init__.py zählen nicht."""
    path = importlib.import_module(package).__path__
    return sorted(module.name for module in pkgutil.iter_modules(path) if module.ispkg)


def _import_if_present(module_name: str) -> ModuleType | None:
    """Importiert module_name. Gibt es die Datei nicht, kommt None zurück."""
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as error:
        # Nur die fehlende Datei selbst ist in Ordnung. Fehlt etwas, das sie importiert,
        # soll der Fehler sichtbar bleiben.
        if error.name == module_name:
            return None
        raise


def load_features(package: str = __name__) -> list[APIRouter]:
    """Lädt jedes Feature und gibt die Router aller api.py-Dateien zurück.

    Je Feature-Ordner:
    - models.py wird importiert, damit seine Tabellen beim Start angelegt werden.
    - api.py wird importiert; ihr Objekt `router` hängt main.py an die App.
    """
    routers = []
    for name in feature_names(package):
        _import_if_present(f"{package}.{name}.models")
        api = _import_if_present(f"{package}.{name}.api")
        if api is None:
            continue
        router = getattr(api, "router", None)
        if not isinstance(router, APIRouter):
            raise RuntimeError(
                f"{package}.{name}.api braucht ein Objekt `router = APIRouter(...)`."
            )
        routers.append(router)
    return routers
