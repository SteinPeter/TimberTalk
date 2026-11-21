# Die Endpunkte des Features „Material, Fahrten und Preise“ unter /api/materials. Noch ohne
# Endpunkte.
# Ein Endpunkt nimmt die Anfrage an, ruft eine Funktion aus service.py auf und gibt das Ergebnis
# zurück – sonst nichts. Die Sitzung kommt aus Depends(get_session).
# Das Objekt `router` muss bleiben: load_features() hängt es an die App.

from fastapi import APIRouter

router = APIRouter(prefix="/api/materials", tags=["Material, Fahrten und Preise"])
