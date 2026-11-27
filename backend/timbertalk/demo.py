# Demo-Daten: ein vollständiger Beispielbetrieb, damit man TimberTalk ohne Einrichtung ausprobieren
# kann – Firma, Stundensätze, Materialkatalog mit Preisen, Fahrzeuge, Konten aller Rollen, Termine,
# Urlaubsanträge, gebuchte Stunden, Material und Fahrten.
#
# Wann es läuft:
# - Von selbst beim Start, wenn die Datenbank noch leer ist und TIMBERTALK_DEMO an ist (Standard).
# - Von Hand für eine bestehende Datenbank (im Ordner backend/):
#       uv run python -m timbertalk.demo
#   Das ist ungefährlich doppelt aufrufbar: Ist der Beispielbetrieb schon da, passiert nichts.
#
# Alles wird über die service.py der Features angelegt – genau wie über die Oberfläche. Termine und
# Buchungen liegen relativ zu heute (diese und nächste Woche), damit Kalender und Dashboard immer
# etwas zeigen. Alle Konten haben das Standardpasswort; im Demo-Modus braucht man keins.

from datetime import date, time, timedelta
from decimal import Decimal

from sqlmodel import Session, select

from timbertalk.features.accounts import service as accounts
from timbertalk.features.accounts.models import Account, Setting
from timbertalk.features.employees import service as employees
from timbertalk.features.employees.models import ContractIn
from timbertalk.features.hours import service as hours
from timbertalk.features.hours.models import HoursIn
from timbertalk.features.materials import service as materials
from timbertalk.features.materials.models import CompanyIn
from timbertalk.features.planning import service as planning
from timbertalk.features.planning.models import EntryIn, RequestIn, ResourceIn

# Merker in accounts_setting: Der Beispielbetrieb ist angelegt.
DEMO_MARKER = "demo_data"

# Projektnummern der Beispielprojekte (die Projekte selbst kommen mit F3).
CARPORT, DACH, GAUBE = 17, 18, 19

COMPANY = CompanyIn(
    company_name="Zimmerei Holzwerk Berger GmbH",
    address="Am Sägewerk 12\n14467 Potsdam",
    bank_name="Mittelbrandenburgische Sparkasse",
    iban="DE89 3704 0044 0532 0130 00",  # die übliche Beispiel-IBAN, kein echtes Konto
    bic="WELADED1PMB",
    vat_rate=Decimal("19"),
)

HOURLY_RATES = {"Meister": "68.00", "Geselle": "55.00", "Azubi": "28.00", "Helfer": "42.00"}

# Name, Kategorie, Einheit, Preis seit Jahresanfang, neuer Preis seit dem 1. des Monats (oder None)
MATERIALS = [
    ("Konstruktionsvollholz C24 60×120", "Bauholz", "m³", "495.00", "520.00"),
    ("Konstruktionsvollholz C24 80×200", "Bauholz", "m³", "505.00", "530.00"),
    ("Brettschichtholz GL24h 120×240", "Bauholz", "m³", "680.00", None),
    ("Dachlatten 30×50 sortiert", "Bauholz", "m", "0.95", None),
    ("Konterlatten 24×48", "Bauholz", "m", "0.80", None),
    ("OSB/3 Verlegeplatte 18 mm", "Platten", "m²", "9.40", "9.90"),
    ("Rauspund Fichte 24 mm", "Platten", "m²", "18.50", None),
    ("Gipsfaserplatte 12,5 mm", "Platten", "m²", "7.20", None),
    ("Holzfaserdämmplatte 60 mm", "Dämmung", "m²", "21.00", None),
    ("Mineralwolle WLG 035, 160 mm", "Dämmung", "m²", "12.80", None),
    ("Unterdeckbahn diffusionsoffen", "Folien", "m²", "1.90", None),
    ("Dampfbremse feuchtevariabel", "Folien", "m²", "1.40", None),
    ("Tellerkopfschrauben 8×200", "Verbinder", "Stk", "0.62", None),
    ("Winkelverbinder 90 mm", "Verbinder", "Stk", "2.40", None),
    ("Balkenschuh 80×160", "Verbinder", "Stk", "3.10", None),
    ("Sparrennägel 6×200 (5 kg)", "Verbinder", "Pak", "34.90", None),
]

# Anmeldename, Name, Rolle, Personalnummer
PEOPLE = [
    ("k.schulz", "Klaus Schulz", "owner", "001"),
    ("s.wolf", "Sabine Wolf", "master", "002"),
    ("p.lange", "Petra Lange", "office", "003"),
    ("m.berger", "Max Berger", "journeyman", "017"),
    ("t.adler", "Tom Adler", "journeyman", "021"),
    ("j.krause", "Jonas Krause", "journeyman", "024"),
    ("l.kim", "Lena Kim", "apprentice", "030"),
]


def already_seeded(session: Session) -> bool:
    return session.get(Setting, DEMO_MARKER) is not None


def seed(session: Session, today: date | None = None) -> bool:
    """Legt den Beispielbetrieb an. Gibt False zurück, wenn er schon da war."""
    if already_seeded(session):
        return False
    today = today or date.today()
    monday = today - timedelta(days=today.weekday())
    # Preise gelten ab Jahresanfang – spätestens aber eine Woche vor diesem Montag, damit auch
    # Buchungen der Vorwoche einen Preis haben (wichtig in der ersten Januarwoche).
    year_start = min(date(today.year, 1, 1), monday - timedelta(days=7))
    month_start = today.replace(day=1)

    def day(offset: int) -> date:
        return monday + timedelta(days=offset)

    # --- Konten -------------------------------------------------------------------
    accounts.ensure_initial_admin(session)
    ids = {}
    for username, name, role, number in PEOPLE:
        existing = session.exec(select(Account).where(Account.username == username)).first()
        if existing is None:
            existing, _ = accounts.create_account(session, username, name, role, number)
        ids[username] = existing.id
    chef, meisterin = ids["k.schulz"], ids["s.wolf"]
    max_, tom, jonas, lena = ids["m.berger"], ids["t.adler"], ids["j.krause"], ids["l.kim"]

    # --- Firma, Stundensätze, Materialkatalog -------------------------------------
    materials.save_company(session, COMPANY)
    for name, rate in HOURLY_RATES.items():
        materials.save_hourly_rate(session, name, Decimal(rate))
    material_ids = {}
    for name, category, unit, price, new_price in MATERIALS:
        item = materials.create_material(session, name, category, unit)
        materials.add_price(session, item.id, Decimal(price), year_start)
        if new_price and month_start > year_start:
            materials.add_price(session, item.id, Decimal(new_price), month_start)
        material_ids[name] = item.id

    # --- Fahrzeuge und Maschinen --------------------------------------------------
    def resource(name: str, category: str, rate: str | None = None) -> int:
        created = planning.create_resource(session, ResourceIn(name=name, category=category))
        if rate:
            planning.set_vehicle_rate(session, created.id, Decimal(rate))
        return created.id

    transporter = resource("Transporter B-HW 123", "vehicle", "0.55")
    pritsche = resource("Pritschenwagen B-HW 456", "vehicle", "0.70")
    kran = resource("Autokran 30 t", "machine")
    resource("Abbundmaschine", "machine")

    # --- Termine diese und nächste Woche ------------------------------------------
    def entry(title, start, end, people, *, kind="job", times=None, where="", project=None, res=()):
        planning.create_entry(
            session,
            EntryIn(
                title=title,
                kind=kind,
                start_date=day(start),
                end_date=day(end),
                start_time=times[0] if times else None,
                end_time=times[1] if times else None,
                location=where,
                project_id=project,
                people=people,
                resources=list(res),
            ),
            created_by=chef,
            notify=False,  # Demo: keine Flut an Mitteilungen
        )

    work = (time(7, 0), time(16, 0))
    entry(
        "Carport Familie Berger",
        0,
        2,
        [max_, tom],
        times=work,
        where="Potsdam, Lindenstraße 4",
        project=CARPORT,
        res=[transporter],
    )
    entry(
        "Dachsanierung Schulz",
        0,
        4,
        [meisterin, jonas],
        times=work,
        where="Werder, Seestraße 9",
        project=DACH,
        res=[pritsche],
    )
    entry(
        "Kran stellen: Dachstuhl Schulz",
        3,
        3,
        [meisterin, jonas, max_],
        times=(time(7, 0), time(12, 0)),
        where="Werder, Seestraße 9",
        project=DACH,
        res=[kran],
    )
    entry(
        "Abbund Dachgaube Weber",
        3,
        4,
        [max_, tom, lena],
        kind="workshop",
        times=work,
        project=GAUBE,
    )
    entry("Berufsschule", 1, 1, [lena], kind="school")
    entry(
        "Aufmaß Gaube Weber",
        1,
        1,
        [chef],
        kind="appointment",
        times=(time(9, 0), time(10, 30)),
        where="Potsdam, Am Park 3",
        project=GAUBE,
    )
    entry(
        "Dachgaube Weber montieren",
        7,
        9,
        [max_, tom, lena],
        times=work,
        where="Potsdam, Am Park 3",
        project=GAUBE,
        res=[transporter, kran],
    )
    entry(
        "Dachsanierung Schulz",
        7,
        8,
        [meisterin, jonas],
        times=work,
        where="Werder, Seestraße 9",
        project=DACH,
        res=[pritsche],
    )
    entry("Berufsschule", 8, 8, [lena], kind="school")
    entry(
        "Baubesprechung Dachsanierung Schulz",
        4,
        4,
        [chef, meisterin],
        kind="appointment",
        times=(time(14, 0), time(15, 0)),
        where="Werder, Seestraße 9",
        project=DACH,
    )
    entry(
        "Abnahme Carport Familie Berger",
        9,
        9,
        [chef, max_],
        kind="appointment",
        times=(time(10, 0), time(11, 0)),
        where="Potsdam, Lindenstraße 4",
        project=CARPORT,
    )

    # --- Urlaub: einer genehmigt, einer offen (steht beim Chef auf dem Dashboard) --
    tom_frei = planning.request_absence(
        session, tom, RequestIn(start_date=day(11), end_date=day(11))
    )
    planning.decide_request(session, tom_frei.id, True, chef, "Viel Spaß!")
    planning.request_absence(
        session,
        max_,
        RequestIn(start_date=day(14), end_date=day(18), note="Familienurlaub an der Ostsee"),
    )

    # --- Gebuchte Stunden, Material und Fahrten (die Tage vor heute) ----------------
    past = [d for d in range(0, 3) if day(d) < today] or [-3, -2]
    for d in past:
        for person in (max_, tom):
            hours.book(
                session,
                HoursIn(
                    work_date=day(d),
                    hours=Decimal("8.5"),
                    project_id=CARPORT,
                    title="Carport Familie Berger",
                    account_id=person,
                ),
                chef,
                may_manage=True,
            )
    first = day(past[0])
    for name, quantity in [
        ("Konstruktionsvollholz C24 60×120", "1.8"),
        ("Brettschichtholz GL24h 120×240", "0.9"),
        ("Rauspund Fichte 24 mm", "32"),
        ("Tellerkopfschrauben 8×200", "120"),
        ("Winkelverbinder 90 mm", "24"),
    ]:
        materials.book_material(session, CARPORT, material_ids[name], Decimal(quantity), first)
    materials.book_travel(session, CARPORT, Decimal("38"), first, transporter)
    materials.book_material(
        session, DACH, material_ids["Mineralwolle WLG 035, 160 mm"], Decimal("85"), first
    )
    materials.book_travel(session, DACH, Decimal("52"), first, pritsche)

    # --- Stunden- und Urlaubskonten (F14) --------------------------------------------
    # Eintritt diesen Montag: So passt das Soll zu den Stunden, die oben gebucht sind.
    # Petra arbeitet Teilzeit, Lena hat als Azubi weniger Urlaub; Max und Tom haben Rest aus dem
    # Vorjahr.
    contracts = {chef: ("40", 30), meisterin: ("40", 30), ids["p.lange"]: ("30", 30)}
    contracts |= {max_: ("40", 30), tom: ("40", 30), jonas: ("40", 28), lena: ("40", 25)}
    for person, (weekly, vacation) in contracts.items():
        employees.save_contract(
            session,
            person,
            ContractIn(weekly_hours=Decimal(weekly), vacation_days=vacation, start_date=monday),
        )
    employees.set_carryover(session, max_, today.year, 3)
    employees.set_carryover(session, tom, today.year, 2)

    # --- Demo-Modus an, automatisch als Chef ----------------------------------------
    accounts.set_demo_mode(session, True, chef)
    session.add(Setting(key=DEMO_MARKER, value=today.isoformat()))
    session.commit()
    return True


def main() -> None:
    """Befehl: uv run python -m timbertalk.demo – legt den Beispielbetrieb in der Datenbank an."""
    from timbertalk.db import create_tables, get_engine
    from timbertalk.features import load_features

    load_features()
    create_tables()
    with Session(get_engine()) as session:
        if seed(session):
            print(
                "Beispielbetrieb angelegt. Der Demo-Modus ist an: Beim Öffnen ist man als Chef "
                "Klaus Schulz angemeldet; nach „Abmelden“ kann man jedes Konto wählen."
            )
        else:
            print("Der Beispielbetrieb ist schon da – nichts geändert.")


if __name__ == "__main__":
    main()
