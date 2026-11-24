# Die Logik des Features „Material, Fahrten und Preise“ als einfache Funktionen.
# Jede Funktion bekommt als ersten Parameter die Datenbank-Sitzung: session: Session.
# Andere Features benutzen dieses Feature nur über die Funktionen in dieser Datei.
#
# Fehler: ValueError heißt „die Angabe passt nicht“, LookupError heißt „gibt es nicht“. Die
# Meldung ist ein deutscher Satz, den man dem Zimmerer direkt zeigen kann. Wo mehrere Dinge
# zusammen gebucht werden, wird entweder alles gebucht oder nichts.
#
# Das Projekt selbst liegt in F3 (projects). Solange es dessen Service nicht gibt, ist die
# Projektnummer nur eine Zahl und wird nicht geprüft.

from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from sqlmodel import Session, select

from timbertalk.features.materials.models import (
    KIND_MATERIAL,
    KIND_TRAVEL,
    STATUS_CONFIRMED,
    STATUS_DRAFT,
    Booking,
    BookingInfo,
    Company,
    CompanyIn,
    HourlyRate,
    MaterialInfo,
    MaterialItem,
    MaterialPrice,
    ProjectCosts,
)

CENT = Decimal("0.01")
MAX_LOGO_LENGTH = 500_000  # Zeichen, reicht für ein Logo von rund 350 KB
MAX_SEARCH_RESULTS = 10
MAX_AMOUNT = Decimal("1000000")  # größte erlaubte Zahl für Mengen, km, Preise und Sätze


def to_cents(value: Decimal) -> Decimal:
    """Rundet einen Betrag auf ganze Cent (kaufmännisch)."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _require_text(value: str, label: str) -> str:
    text = value.strip()
    if not text:
        raise ValueError(f"{label} darf nicht leer sein.")
    return text


def _require_amount(value: Decimal, label: str) -> Decimal:
    """Prüft, dass eine Zahl endlich ist und zwischen 0 und MAX_AMOUNT liegt.

    Ohne diese Prüfung kämen `Infinity`, `NaN` oder `1e1000` in die Datenbank, und die Kosten
    des Projekts ließen sich danach nicht mehr berechnen.
    """
    if not value.is_finite() or not 0 <= value <= MAX_AMOUNT:
        limit = f"{MAX_AMOUNT:,.0f}".replace(",", ".")  # deutsch: 1.000.000
        raise ValueError(f"{label} muss eine Zahl zwischen 0 und {limit} sein.")
    return value


def _require_project(project_id: int) -> None:
    if not isinstance(project_id, int) or isinstance(project_id, bool) or project_id < 1:
        raise ValueError("Die Projektnummer muss eine positive Zahl sein.")


# --- Materialstamm --------------------------------------------------------------


def create_material(session: Session, name: str, category: str, unit: str) -> MaterialItem:
    """Legt ein Material im Materialstamm an. Der Preis kommt mit add_price()."""
    material = MaterialItem(
        name=_require_text(name, "Der Name"),
        category=category.strip(),
        unit=_require_text(unit, "Die Einheit"),
    )
    session.add(material)
    session.commit()
    session.refresh(material)
    return material


def get_material(session: Session, material_id: int) -> MaterialItem:
    """Holt ein Material oder meldet, dass es keines mit dieser Nummer gibt."""
    material = session.get(MaterialItem, material_id)
    if material is None:
        raise LookupError(f"Material {material_id} gibt es nicht.")
    return material


def add_price(
    session: Session, material_id: int, unit_price: Decimal, valid_from: date
) -> MaterialPrice:
    """Trägt einen Preis ein, der ab `valid_from` gilt – bis ein neuerer beginnt."""
    get_material(session, material_id)
    _require_amount(unit_price, "Der Preis")
    same_day = session.exec(
        select(MaterialPrice).where(
            MaterialPrice.material_id == material_id, MaterialPrice.valid_from == valid_from
        )
    ).first()
    if same_day is not None:
        raise ValueError(f"Für den {valid_from:%d.%m.%Y} gibt es schon einen Preis.")
    price = MaterialPrice(material_id=material_id, unit_price=unit_price, valid_from=valid_from)
    session.add(price)
    session.commit()
    session.refresh(price)
    return price


def list_prices(session: Session, material_id: int) -> list[MaterialPrice]:
    """Alle Preise eines Materials, der neueste zuerst."""
    get_material(session, material_id)
    statement = (
        select(MaterialPrice)
        .where(MaterialPrice.material_id == material_id)
        .order_by(MaterialPrice.valid_from.desc())
    )
    return list(session.exec(statement))


def current_price(session: Session, material_id: int, on_date: date) -> MaterialPrice | None:
    """Der Preis, der am Tag `on_date` gilt: der mit dem spätesten Beginn bis zu diesem Tag."""
    statement = (
        select(MaterialPrice)
        .where(MaterialPrice.material_id == material_id, MaterialPrice.valid_from <= on_date)
        .order_by(MaterialPrice.valid_from.desc())
    )
    return session.exec(statement).first()


def _info(session: Session, material: MaterialItem, on_date: date) -> MaterialInfo:
    price = current_price(session, material.id, on_date)
    return MaterialInfo(
        id=material.id,
        name=material.name,
        kategorie=material.category,
        einheit=material.unit,
        preis=price.unit_price if price else None,
        gueltig_ab=price.valid_from if price else None,
    )


def list_materials(
    session: Session, category: str | None = None, on_date: date | None = None
) -> list[MaterialInfo]:
    """Die Materialliste mit dem Preis von heute (S-04). Ohne Treffer: eine leere Liste.

    Mit `category` nur diese Kategorie. Mit `on_date` der Preis von einem anderen Tag.
    """
    statement = select(MaterialItem).order_by(MaterialItem.name)
    if category:
        statement = statement.where(MaterialItem.category == category)
    reference_date = on_date or date.today()
    return [_info(session, material, reference_date) for material in session.exec(statement)]


def search_materials(session: Session, text: str) -> list[MaterialInfo]:
    """Sucht im Namen und in der Kategorie, ohne auf Groß und Klein zu achten. Höchstens 10."""
    needle = _require_text(text, "Der Suchtext").lower()
    reference_date = date.today()
    found = []
    for material in session.exec(select(MaterialItem).order_by(MaterialItem.name)):
        if needle in material.name.lower() or needle in material.category.lower():
            found.append(_info(session, material, reference_date))
        if len(found) == MAX_SEARCH_RESULTS:
            break
    return found


# --- Stammdaten der Abrechnung ----------------------------------------------------


def get_company(session: Session) -> Company:
    """Die Stammdaten der Abrechnung. Gibt es noch keine, kommen leere Vorgabewerte zurück."""
    return session.get(Company, 1) or Company()


def save_company(session: Session, data: CompanyIn) -> Company:
    """Speichert die Stammdaten der Abrechnung (Firma, Logo, Bank, Fahrtkosten, USt)."""
    _require_amount(data.travel_rate_per_km, "Der Satz für Fahrten")
    if not data.vat_rate.is_finite() or not Decimal(0) <= data.vat_rate <= Decimal(100):
        raise ValueError("Die Umsatzsteuer muss zwischen 0 und 100 Prozent liegen.")
    if data.logo:
        if not data.logo.startswith("data:image/"):
            raise ValueError("Das Logo muss ein Bild sein.")
        if len(data.logo) > MAX_LOGO_LENGTH:
            raise ValueError("Das Logo ist zu groß (höchstens rund 350 KB).")
    company = session.get(Company, 1) or Company(id=1)
    company.company_name = data.company_name.strip()
    company.address = data.address.strip()
    company.logo = data.logo or None
    company.bank_name = data.bank_name.strip()
    company.iban = data.iban.replace(" ", "").upper()
    company.bic = data.bic.replace(" ", "").upper()
    company.travel_rate_per_km = data.travel_rate_per_km
    company.vat_rate = data.vat_rate
    session.add(company)
    session.commit()
    session.refresh(company)
    return company


def list_hourly_rates(session: Session) -> list[HourlyRate]:
    """Alle Stundensätze, alphabetisch."""
    return list(session.exec(select(HourlyRate).order_by(HourlyRate.name)))


def save_hourly_rate(session: Session, name: str, rate: Decimal) -> HourlyRate:
    """Legt einen Stundensatz an. Gibt es den Namen schon, wird sein Satz geändert."""
    name = _require_text(name, "Der Name")
    _require_amount(rate, "Der Stundensatz")
    hourly_rate = session.exec(select(HourlyRate).where(HourlyRate.name == name)).first()
    if hourly_rate is None:
        hourly_rate = HourlyRate(name=name, rate=rate)
    hourly_rate.rate = rate
    session.add(hourly_rate)
    session.commit()
    session.refresh(hourly_rate)
    return hourly_rate


def delete_hourly_rate(session: Session, hourly_rate_id: int) -> None:
    """Löscht einen Stundensatz."""
    hourly_rate = session.get(HourlyRate, hourly_rate_id)
    if hourly_rate is None:
        raise LookupError(f"Stundensatz {hourly_rate_id} gibt es nicht.")
    session.delete(hourly_rate)
    session.commit()


# --- Buchen -----------------------------------------------------------------------


def _new_material_booking(
    session: Session,
    project_id: int,
    material_id: int,
    quantity: Decimal,
    booking_date: date,
    unit: str | None,
    status: str,
    draft_id: int | None = None,
    design_id: int | None = None,
) -> Booking:
    """Baut eine Materialbuchung und legt sie in die Sitzung – ohne zu speichern."""
    _require_project(project_id)
    material = get_material(session, material_id)
    _require_amount(quantity, "Die Menge")
    if quantity == 0:
        raise ValueError("Die Menge muss größer als 0 sein.")
    if unit is not None and unit.strip().lower() != material.unit.lower():
        raise ValueError(f"{material.name} wird in {material.unit} gebucht, nicht in {unit}.")
    price = current_price(session, material.id, booking_date)
    if price is None:
        raise ValueError(f"Für {material.name} gibt es am {booking_date:%d.%m.%Y} keinen Preis.")
    booking = Booking(
        project_id=project_id,
        kind=KIND_MATERIAL,
        booking_date=booking_date,
        status=status,
        draft_id=draft_id,
        material_id=material.id,
        design_id=design_id,
        quantity=quantity,
        unit=material.unit,
        unit_price=price.unit_price,
    )
    session.add(booking)
    return booking


def _new_travel_booking(
    session: Session,
    project_id: int,
    km: Decimal,
    booking_date: date,
    status: str,
    draft_id: int | None = None,
) -> Booking:
    """Baut eine Fahrtbuchung und legt sie in die Sitzung – ohne zu speichern."""
    _require_project(project_id)
    _require_amount(km, "Die Strecke")
    if km == 0:
        raise ValueError("Die Strecke muss größer als 0 km sein.")
    rate = get_company(session).travel_rate_per_km
    if rate <= 0:
        raise ValueError(
            "Der Satz für Fahrten je km ist noch nicht in den Einstellungen eingetragen."
        )
    booking = Booking(
        project_id=project_id,
        kind=KIND_TRAVEL,
        booking_date=booking_date,
        status=status,
        draft_id=draft_id,
        quantity=km,
        unit="km",
        unit_price=rate,
    )
    session.add(booking)
    return booking


def _save(session: Session, bookings: list[Booking]) -> None:
    session.commit()
    for booking in bookings:
        session.refresh(booking)


def book_material(
    session: Session,
    project_id: int,
    material_id: int,
    quantity: Decimal,
    booking_date: date,
) -> Booking:
    """Bucht Material auf ein Projekt (über die Oberfläche). Es zählt sofort zu den Kosten."""
    booking = _new_material_booking(
        session, project_id, material_id, quantity, booking_date, None, STATUS_CONFIRMED
    )
    _save(session, [booking])
    return booking


def book_travel(session: Session, project_id: int, km: Decimal, booking_date: date) -> Booking:
    """Bucht eine Fahrt (km) auf ein Projekt. Sie zählt sofort zu den Kosten."""
    booking = _new_travel_booking(session, project_id, km, booking_date, STATUS_CONFIRMED)
    _save(session, [booking])
    return booking


def _next_draft_id(session: Session) -> int:
    highest = max((d for d in session.exec(select(Booking.draft_id)) if d is not None), default=0)
    return highest + 1


def _draft_position(
    session: Session, project_id: int, position: dict, booking_date: date, draft_id: int
) -> Booking:
    """Eine Position aus S-05 als Entwurfsbuchung. Fehlt eine Angabe, ist das ein ValueError."""
    try:
        material_id = position["material_id"]
        quantity = Decimal(str(position["menge"]))
    except KeyError:
        raise ValueError("Jede Position braucht material_id und menge.") from None
    except InvalidOperation:
        raise ValueError(f"„{position['menge']}“ ist keine Menge.") from None
    return _new_material_booking(
        session,
        project_id,
        material_id,
        quantity,
        booking_date,
        position.get("einheit"),
        STATUS_DRAFT,
        draft_id=draft_id,
        design_id=position.get("design_id"),
    )


def book_material_draft(
    session: Session, project_id: int, positions: list[dict], booking_date: date | None = None
) -> int:
    """Bucht Materialpositionen als Entwurf (S-05) und gibt die Nummer des Entwurfs zurück.

    `positions`: je Position `material_id`, `menge`, `einheit` und optional `design_id`.
    Ein Entwurf zählt noch nicht zu den Kosten, bis confirm_draft() ihn bestätigt.
    Passt eine Position nicht, wird nichts gebucht.
    """
    if not positions:
        raise ValueError("Es fehlen die Positionen.")
    draft_id = _next_draft_id(session)
    booking_date = booking_date or date.today()
    bookings = []
    try:
        for position in positions:
            bookings.append(_draft_position(session, project_id, position, booking_date, draft_id))
    except Exception:
        session.rollback()
        raise
    _save(session, bookings)
    return draft_id


def book_travel_draft(session: Session, project_id: int, km: Decimal, booking_date: date) -> int:
    """Bucht eine Fahrt als Entwurf und gibt die Nummer des Entwurfs zurück."""
    draft_id = _next_draft_id(session)
    booking = _new_travel_booking(session, project_id, km, booking_date, STATUS_DRAFT, draft_id)
    _save(session, [booking])
    return draft_id


def confirm_draft(session: Session, draft_id: int) -> None:
    """Bestätigt einen Entwurf: seine Buchungen zählen ab jetzt zu den Kosten."""
    bookings = list(session.exec(select(Booking).where(Booking.draft_id == draft_id)))
    if not bookings:
        raise LookupError(f"Entwurf {draft_id} gibt es nicht.")
    for booking in bookings:
        booking.status = STATUS_CONFIRMED
        session.add(booking)
    session.commit()


# --- Anzeigen ---------------------------------------------------------------------


def _booking_info(session: Session, booking: Booking) -> BookingInfo:
    if booking.kind == KIND_MATERIAL:
        description = get_material(session, booking.material_id).name
    else:
        description = "Fahrt"
    return BookingInfo(
        id=booking.id,
        project_id=booking.project_id,
        kind=booking.kind,
        booking_date=booking.booking_date,
        status=booking.status,
        description=description,
        quantity=booking.quantity,
        unit=booking.unit,
        unit_price=booking.unit_price,
        amount=to_cents(booking.quantity * booking.unit_price),
    )


def list_bookings(session: Session, project_id: int) -> list[BookingInfo]:
    """Alle Buchungen eines Projekts, nach Datum sortiert. Entwürfe sind dabei."""
    _require_project(project_id)
    statement = (
        select(Booking)
        .where(Booking.project_id == project_id)
        .order_by(Booking.booking_date, Booking.id)
    )
    return [_booking_info(session, booking) for booking in session.exec(statement)]


def project_costs(session: Session, project_id: int) -> ProjectCosts:
    """Die Kosten eines Projekts in Euro netto. Nur bestätigte Buchungen zählen.

    Die Stunden kommen aus F4 (hours). Solange es dessen Service nicht gibt, sind sie 0.
    """
    _require_project(project_id)
    material = Decimal(0)
    travel = Decimal(0)
    statement = select(Booking).where(
        Booking.project_id == project_id, Booking.status == STATUS_CONFIRMED
    )
    for booking in session.exec(statement):
        amount = to_cents(booking.quantity * booking.unit_price)
        if booking.kind == KIND_MATERIAL:
            material += amount
        else:
            travel += amount
    hours = Decimal(0)
    return ProjectCosts(
        hours=to_cents(hours),
        material=to_cents(material),
        travel=to_cents(travel),
        total_net=to_cents(hours + material + travel),
    )
