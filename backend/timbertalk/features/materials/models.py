# Tabellen des Features „Material, Fahrten und Preise“ als SQLModel-Klassen, dazu die kleinen
# Antwortklassen, die Service und API zurückgeben.
# Geld und Mengen immer als Decimal, nie als float. SQLite kennt kein Decimal und würde die Zahl
# als float speichern – deshalb speichert `DecimalText` sie als Text und gibt sie als Decimal
# zurück. Alle Tabellennamen beginnen mit `materials_`, damit sie sich nicht mit den Tabellen
# anderer Features überschneiden.

from datetime import date
from decimal import Decimal

from sqlalchemy import Column, String
from sqlalchemy.types import TypeDecorator
from sqlmodel import Field, SQLModel

# Art und Status einer Buchung.
KIND_MATERIAL = "material"
KIND_TRAVEL = "travel"
STATUS_DRAFT = "draft"  # Entwurf: wartet auf die Bestätigung, zählt noch nicht zu den Kosten
STATUS_CONFIRMED = "confirmed"  # gebucht: zählt zu den Projektkosten


class DecimalText(TypeDecorator):
    """Speichert ein Decimal als Text und liest es als Decimal – ohne Umweg über float."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else str(Decimal(value))

    def process_result_value(self, value, dialect):
        return None if value is None else Decimal(value)


def decimal_column(default: str | None = None) -> Column:
    """Eine Spalte für Geld oder Mengen."""
    return Column(DecimalText, nullable=False, default=default)


# --- Tabellen -------------------------------------------------------------------


class MaterialItem(SQLModel, table=True):
    """Ein Eintrag im Materialstamm, z. B. „Konstruktionsvollholz C24“ in m³."""

    __tablename__ = "materials_item"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    category: str = ""  # z. B. „Bauholz“ oder „Kleinteile“
    unit: str  # z. B. „m³“, „Stk“, „m“


class MaterialPrice(SQLModel, table=True):
    """Ein Preis eines Materials, gültig ab einem Datum, bis ein neuerer Preis beginnt."""

    __tablename__ = "materials_price"

    id: int | None = Field(default=None, primary_key=True)
    material_id: int = Field(foreign_key="materials_item.id", index=True)
    unit_price: Decimal = Field(sa_column=decimal_column())  # Euro netto je Einheit
    valid_from: date


class Company(SQLModel, table=True):
    """Die Stammdaten der Abrechnung. Es gibt genau eine Zeile (id = 1)."""

    __tablename__ = "materials_company"

    id: int = Field(default=1, primary_key=True)
    company_name: str = ""
    address: str = ""
    logo: str | None = None  # das Bild als „data:image/…“-Text
    bank_name: str = ""
    iban: str = ""
    bic: str = ""
    travel_rate_per_km: Decimal = Field(default=Decimal("0"), sa_column=decimal_column("0"))
    vat_rate: Decimal = Field(default=Decimal("19"), sa_column=decimal_column("19"))  # Prozent


class HourlyRate(SQLModel, table=True):
    """Ein Stundensatz, z. B. „Geselle“ mit 55 Euro je Stunde."""

    __tablename__ = "materials_hourly_rate"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    rate: Decimal = Field(sa_column=decimal_column())  # Euro netto je Stunde


class Booking(SQLModel, table=True):
    """Eine Buchung von Material oder einer Fahrt auf ein Projekt.

    Der Preis wird beim Buchen festgehalten: Ändert sich der Preis später, bleibt die Buchung
    wie sie war. Bei einer Fahrt ist `quantity` die Strecke in km und `unit_price` der Satz je km.
    """

    __tablename__ = "materials_booking"

    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)  # Nummer des Projekts; das Projekt selbst liegt in F3
    kind: str  # KIND_MATERIAL oder KIND_TRAVEL
    booking_date: date
    status: str = STATUS_CONFIRMED
    draft_id: int | None = Field(default=None, index=True)  # gleiche Nummer = ein Entwurf
    material_id: int | None = Field(default=None, foreign_key="materials_item.id")
    design_id: int | None = None  # Verweis auf den CAD-Entwurf, aus dem die Buchung stammt (S-05)
    quantity: Decimal = Field(sa_column=decimal_column())
    unit: str
    unit_price: Decimal = Field(sa_column=decimal_column())


# --- Antworten und Eingaben (keine Tabellen) -------------------------------------


class MaterialInfo(SQLModel):
    """Ein Material mit dem Preis, der am Stichtag gilt (S-04). Die Namen stehen so in S-04."""

    id: int
    name: str
    kategorie: str
    einheit: str
    preis: Decimal | None  # None: kein Preis für den Stichtag – oder das Konto darf ihn nicht sehen
    gueltig_ab: date | None


class BookingInfo(SQLModel):
    """Eine Buchung, wie die Oberfläche sie anzeigt, mit Beschreibung und Betrag."""

    id: int
    project_id: int
    kind: str
    booking_date: date
    status: str
    description: str
    quantity: Decimal
    unit: str
    unit_price: Decimal | None  # None: das Konto darf keine Preise sehen (F10)
    amount: Decimal | None  # Menge mal Preis, auf Cent gerundet; None wie unit_price


class ProjectCosts(SQLModel):
    """Die Kosten eines Projekts in Euro netto. Nur bestätigte Buchungen zählen."""

    hours: Decimal  # kommt mit F4 (Stunden); bis dahin 0
    material: Decimal
    travel: Decimal
    total_net: Decimal


class MaterialIn(SQLModel):
    """Eingabe: ein neues Material."""

    name: str
    category: str = ""
    unit: str


class PriceIn(SQLModel):
    """Eingabe: ein neuer Preis für ein Material."""

    unit_price: Decimal
    valid_from: date


class CompanyIn(SQLModel):
    """Eingabe: die Stammdaten der Abrechnung."""

    company_name: str = ""
    address: str = ""
    logo: str | None = None
    bank_name: str = ""
    iban: str = ""
    bic: str = ""
    travel_rate_per_km: Decimal = Decimal("0")
    vat_rate: Decimal = Decimal("19")


class HourlyRateIn(SQLModel):
    """Eingabe: ein Stundensatz. Gibt es den Namen schon, wird sein Satz geändert."""

    name: str
    rate: Decimal


class MaterialBookingIn(SQLModel):
    """Eingabe: Material auf ein Projekt buchen."""

    project_id: int
    material_id: int
    quantity: Decimal
    booking_date: date


class TravelBookingIn(SQLModel):
    """Eingabe: eine Fahrt auf ein Projekt buchen."""

    project_id: int
    km: Decimal
    booking_date: date
