# Die Endpunkte des Features „Datensicherung, Wiederherstellung und Export“ unter /api/backup.
# Noch ohne Endpunkte.
# Ein Endpunkt nimmt die Anfrage an, ruft eine Funktion aus service.py auf und gibt das Ergebnis
# zurück – sonst nichts. Die Sitzung kommt aus Depends(get_session).
# Das Objekt `router` muss bleiben: load_features() hängt es an die App.

from fastapi import APIRouter

router = APIRouter(prefix="/api/backup", tags=["Datensicherung, Wiederherstellung und Export"])
