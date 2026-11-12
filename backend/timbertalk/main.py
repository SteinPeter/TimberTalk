# Die Web-Anwendung: die API liegt unter /api, das Frontend unter /.

import threading
import webbrowser
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from timbertalk.db import create_tables, database_ok
from timbertalk.settings import BACKEND_DIR, get_settings

# Der Ordner frontend/ liegt neben backend/ im Hauptordner des Projekts.
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Beim Start der Anwendung werden fehlende Tabellen angelegt."""
    create_tables()
    yield


app = FastAPI(title="TimberTalk", lifespan=lifespan)


@app.get("/api/health")
def health() -> dict[str, str]:
    """Meldet, ob das Backend erreichbar ist und ob die Datenbank antwortet."""
    return {"status": "ok", "database": "ok" if database_ok() else "fehler"}


# Das Frontend sind einfache Dateien. Diese Zeile steht hinter der API,
# damit /api/health zuerst gefunden wird.
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


def run() -> None:
    """Startet den Server und öffnet die Seite im Browser (Befehl: uv run timbertalk)."""
    settings = get_settings()
    url = f"http://{settings.host}:{settings.port}"
    # Kurz warten, damit der Server schon antwortet, wenn der Browser die Seite holt.
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host=settings.host, port=settings.port)
