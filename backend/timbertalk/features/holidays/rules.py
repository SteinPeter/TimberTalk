# Gesetzliche Feiertage je Bundesland und die Zuordnung Postleitzahl → Bundesland.
# Reine Rechenregeln ohne Datenbank – die Funktionen mit Datenbank stehen in service.py.
#
# Feste Feiertage stehen als Datum da, die beweglichen hängen an Ostern. Feiertage, die nur in
# einzelnen Gemeinden gelten (z. B. Mariä Himmelfahrt in katholischen Gemeinden Bayerns,
# Fronleichnam in Teilen Sachsens und Thüringens, Augsburger Friedensfest), sind nicht dabei.

import re
from datetime import date, timedelta

# Kürzel → Name. Die Kürzel sind die üblichen zwei Buchstaben (ISO 3166-2:DE ohne „DE-“).
STATES: dict[str, str] = {
    "BW": "Baden-Württemberg",
    "BY": "Bayern",
    "BE": "Berlin",
    "BB": "Brandenburg",
    "HB": "Bremen",
    "HH": "Hamburg",
    "HE": "Hessen",
    "MV": "Mecklenburg-Vorpommern",
    "NI": "Niedersachsen",
    "NW": "Nordrhein-Westfalen",
    "RP": "Rheinland-Pfalz",
    "SL": "Saarland",
    "SN": "Sachsen",
    "ST": "Sachsen-Anhalt",
    "SH": "Schleswig-Holstein",
    "TH": "Thüringen",
}


def easter_sunday(year: int) -> date:
    """Ostersonntag im gregorianischen Kalender (Rechenweg nach Gauß, „anonymer Algorithmus“)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    weekday_shift = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * weekday_shift) // 451
    month, day = divmod(h + weekday_shift - 7 * m + 114, 31)
    return date(year, month, day + 1)


def _repentance_day(year: int) -> date:
    """Buß- und Bettag: der Mittwoch vor dem 23. November."""
    day = date(year, 11, 22)
    return day - timedelta(days=(day.weekday() - 2) % 7)


def holidays(year: int, state: str | None) -> dict[date, str]:
    """Die gesetzlichen Feiertage eines Jahres: Datum → Name.

    state: Kürzel aus STATES. None: nur die Feiertage, die in ganz Deutschland gelten.
    """
    easter = easter_sunday(year)

    def after_easter(days: int) -> date:
        return easter + timedelta(days=days)

    days = {
        date(year, 1, 1): "Neujahr",
        after_easter(-2): "Karfreitag",
        after_easter(1): "Ostermontag",
        date(year, 5, 1): "Tag der Arbeit",
        after_easter(39): "Christi Himmelfahrt",
        after_easter(50): "Pfingstmontag",
        date(year, 10, 3): "Tag der Deutschen Einheit",
        date(year, 12, 25): "1. Weihnachtstag",
        date(year, 12, 26): "2. Weihnachtstag",
    }
    # Feiertage nur in einzelnen Ländern: Datum, Name, in welchen Ländern, ab welchem Jahr.
    regional = [
        (date(year, 1, 6), "Heilige Drei Könige", {"BW", "BY", "ST"}, 0),
        (date(year, 3, 8), "Internationaler Frauentag", {"BE"}, 2019),
        (date(year, 3, 8), "Internationaler Frauentag", {"MV"}, 2023),
        (after_easter(0), "Ostersonntag", {"BB"}, 0),
        (after_easter(49), "Pfingstsonntag", {"BB"}, 0),
        (after_easter(60), "Fronleichnam", {"BW", "BY", "HE", "NW", "RP", "SL"}, 0),
        (date(year, 8, 15), "Mariä Himmelfahrt", {"SL"}, 0),
        (date(year, 9, 20), "Weltkindertag", {"TH"}, 2019),
        (date(year, 10, 31), "Reformationstag", {"BB", "MV", "SN", "ST", "TH"}, 0),
        (date(year, 10, 31), "Reformationstag", {"HB", "HH", "NI", "SH"}, 2018),
        (date(year, 11, 1), "Allerheiligen", {"BW", "BY", "NW", "RP", "SL"}, 0),
        (_repentance_day(year), "Buß- und Bettag", {"SN"}, 0),
    ]
    for day, name, states, since in regional:
        if state in states and year >= since:
            days[day] = name
    return days


def workdays(start: date, end: date, state: str | None) -> list[date]:
    """Alle Arbeitstage von start bis end: Montag bis Freitag, ohne Feiertage."""
    free: dict[date, str] = {}
    for year in range(start.year, end.year + 1):
        free |= holidays(year, state)
    days = []
    day = start
    while day <= end:
        if day.weekday() < 5 and day not in free:
            days.append(day)
        day += timedelta(days=1)
    return days


# --- Postleitzahl → Bundesland -------------------------------------------------------
#
# Postleitzahlen folgen nicht genau den Landesgrenzen. Darum zuerst die Leitregion (die ersten
# zwei Ziffern), dann Ausnahmen für Bereiche, die in einem anderen Land liegen. Das trifft für
# fast alle Orte; an Landesgrenzen kann es danebenliegen – dann legt man das Bundesland unter
# Einstellungen → Feiertage selbst fest.

LEAD_REGIONS: dict[str, str] = {
    "01": "SN", "02": "SN", "03": "BB", "04": "SN", "06": "ST", "07": "TH", "08": "SN",
    "09": "SN", "10": "BE", "12": "BE", "13": "BE", "14": "BB", "15": "BB", "16": "BB",
    "17": "MV", "18": "MV", "19": "MV", "20": "HH", "21": "NI", "22": "HH", "23": "SH",
    "24": "SH", "25": "SH", "26": "NI", "27": "NI", "28": "NI", "29": "NI", "30": "NI",
    "31": "NI", "32": "NW", "33": "NW", "34": "HE", "35": "HE", "36": "HE", "37": "NI",
    "38": "NI", "39": "ST", "40": "NW", "41": "NW", "42": "NW", "44": "NW", "45": "NW",
    "46": "NW", "47": "NW", "48": "NW", "49": "NI", "50": "NW", "51": "NW", "52": "NW",
    "53": "NW", "54": "RP", "55": "RP", "56": "RP", "57": "NW", "58": "NW", "59": "NW",
    "60": "HE", "61": "HE", "63": "HE", "64": "HE", "65": "HE", "66": "SL", "67": "RP",
    "68": "BW", "69": "BW", "70": "BW", "71": "BW", "72": "BW", "73": "BW", "74": "BW",
    "75": "BW", "76": "BW", "77": "BW", "78": "BW", "79": "BW", "80": "BY", "81": "BY",
    "82": "BY", "83": "BY", "84": "BY", "85": "BY", "86": "BY", "87": "BY", "88": "BW",
    "89": "BW", "90": "BY", "91": "BY", "92": "BY", "93": "BY", "94": "BY", "95": "BY",
    "96": "BY", "97": "BY", "98": "TH", "99": "TH",
}  # fmt: skip

# Von–bis (beide eingeschlossen) → Bundesland, abweichend von der Leitregion.
EXCEPTIONS: list[tuple[int, int, str]] = [
    (1941, 1998, "BB"),  # Elbe-Elster, Oberspreewald-Lausitz
    (4600, 4639, "TH"),  # Altenburger Land
    (4895, 4938, "BB"),  # Elbe-Elster
    (6556, 6578, "TH"),  # Kyffhäuserkreis
    (14000, 14199, "BE"),  # Berlin-Steglitz, -Zehlendorf, -Wannsee
    (17258, 17291, "BB"),  # Uckermark
    (17326, 17337, "BB"),  # Uckermark
    (19322, 19357, "BB"),  # Prignitz
    (21000, 21149, "HH"),  # Hamburg-Bergedorf, -Harburg
    (22844, 22969, "SH"),  # Norderstedt, Stormarn
    (23919, 23999, "MV"),  # Nordwestmecklenburg
    (27568, 27580, "HB"),  # Bremerhaven
    (28000, 28359, "HB"),  # Bremen
    (28717, 28779, "HB"),  # Bremen-Nord
    (36404, 36469, "TH"),  # Wartburgkreis
    (37201, 37299, "HE"),  # Werra-Meißner-Kreis
    (37300, 37359, "TH"),  # Eichsfeld
    (38820, 38899, "ST"),  # Harz
    (49477, 49479, "NW"),  # Ibbenbüren
    (53400, 53579, "RP"),  # Ahrweiler, Neuwied
    (57500, 57648, "RP"),  # Altenkirchen, Westerwald
    (63700, 63939, "BY"),  # Aschaffenburg, Miltenberg
    (65550, 65629, "RP"),  # Rhein-Lahn-Kreis
    (66480, 66509, "RP"),  # Zweibrücken
    (66840, 66999, "RP"),  # Kaiserslautern, Pirmasens
    (68501, 68649, "HE"),  # Viernheim, Lampertheim
    (69430, 69439, "HE"),  # Hirschhorn
    (88131, 88179, "BY"),  # Lindau
    (89231, 89299, "BY"),  # Neu-Ulm
    (97877, 97900, "BW"),  # Wertheim
]

POSTCODE = re.compile(r"(?<!\d)(\d{5})(?!\d)")


def postcode_in(address: str) -> str | None:
    """Die erste fünfstellige Zahl in einer Adresse, z. B. „14467“ aus „14467 Potsdam“."""
    found = POSTCODE.search(address or "")
    return found.group(1) if found else None


def state_for_postcode(postcode: str) -> str | None:
    """Das Bundesland zu einer Postleitzahl (Kürzel) – oder None, wenn sie unbekannt ist."""
    number = int(postcode)
    for low, high, state in EXCEPTIONS:
        if low <= number <= high:
            return state
    return LEAD_REGIONS.get(postcode[:2])
