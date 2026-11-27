# Die Datei mit den Einstellungen des Betriebs, wie sie exportiert und importiert wird.
# Keine Tabellen: Das Feature speichert nichts selbst, es liest und schreibt über die service.py
# der Features, denen die Daten gehören (materials: Firma, Stundensätze, Materialstamm;
# planning: Fahrzeuge und Maschinen).
#
# Geld und Mengen immer als Decimal, nie als float. In der Datei stehen sie als Text ("0.55"),
# damit beim Hin und Her kein Cent verloren geht.

from datetime import datetime
from decimal import Decimal

from sqlmodel import SQLModel

from timbertalk.features.materials.models import CompanyIn, HourlyRateIn, PriceIn

# Erkennungszeichen und Stand des Formats – ändert sich der Aufbau, steigt die Nummer.
FORMAT = "timbertalk-einstellungen"
VERSION = 1


class MaterialOut(SQLModel):
    """Ein Material mit allen Preisen (ältester zuerst)."""

    name: str
    category: str = ""
    unit: str
    prices: list[PriceIn] = []


class ResourceOut(SQLModel):
    """Ein Fahrzeug oder eine Maschine."""

    name: str
    category: str = "vehicle"
    active: bool = True
    rate_per_km: Decimal | None = None


class SettingsFile(SQLModel):
    """Alle Einstellungen des Betriebs in einer Datei."""

    format: str = FORMAT
    version: int = VERSION
    exported_at: datetime | None = None
    company: CompanyIn | None = None
    hourly_rates: list[HourlyRateIn] = []
    materials: list[MaterialOut] = []
    resources: list[ResourceOut] = []


class ImportResult(SQLModel):
    """Was der Import geändert hat – für die Meldung in der Oberfläche."""

    company: bool  # Firmendaten übernommen?
    hourly_rates: int  # angelegt oder geändert
    materials_new: int
    prices_new: int
    resources_new: int
    resources_changed: int
