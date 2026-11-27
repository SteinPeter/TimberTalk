# Die Logik des Features „Datensicherung, Wiederherstellung und Export“ als einfache Funktionen.
#
# Heute: alle Einstellungen des Betriebs als eine Datei exportieren und wieder importieren –
# Firmendaten, Stundensätze, Materialstamm mit Preisen, Fahrzeuge und Maschinen. So zieht man
# die Einstellungen auf einen neuen Rechner um oder übernimmt sie aus einem anderen Betrieb.
# Konten und Passwörter gehören nicht dazu.
#
# Der Import ergänzt nur und löscht nie: Was es schon gibt (gleicher Name), wird aktualisiert,
# was fehlt, wird angelegt. Vorhandene Preise bleiben, neue Preise kommen dazu.
# Die Daten gehören anderen Features; gelesen und geschrieben wird nur über deren service.py.

from datetime import UTC, datetime

from sqlmodel import Session

from timbertalk.features.backup.models import (
    FORMAT,
    VERSION,
    ImportResult,
    MaterialOut,
    ResourceOut,
    SettingsFile,
)
from timbertalk.features.materials import service as materials
from timbertalk.features.materials.models import CompanyIn, HourlyRateIn, PriceIn
from timbertalk.features.planning import service as planning
from timbertalk.features.planning.models import ResourceIn


def export_settings(session: Session) -> SettingsFile:
    """Alle Einstellungen des Betriebs als eine Datei."""
    company = materials.get_company(session)
    material_list = []
    for info in materials.list_materials(session):
        prices = sorted(materials.list_prices(session, info.id), key=lambda p: p.valid_from)
        material_list.append(
            MaterialOut(
                name=info.name,
                category=info.kategorie,
                unit=info.einheit,
                prices=[PriceIn(unit_price=p.unit_price, valid_from=p.valid_from) for p in prices],
            )
        )
    return SettingsFile(
        exported_at=datetime.now(UTC),
        company=CompanyIn.model_validate(company.model_dump()),
        hourly_rates=[
            HourlyRateIn(name=rate.name, rate=rate.rate)
            for rate in materials.list_hourly_rates(session)
        ],
        materials=material_list,
        resources=[
            ResourceOut(
                name=r.name, category=r.category, active=r.active, rate_per_km=r.rate_per_km
            )
            for r in planning.list_resources(session, include_inactive=True)
        ],
    )


def import_settings(session: Session, data: SettingsFile) -> ImportResult:
    """Übernimmt die Einstellungen aus einer exportierten Datei. Ergänzt nur, löscht nichts.

    Eine falsche Angabe (z. B. ein negativer Preis) bricht mit ValueError ab; was bis dahin
    übernommen ist, bleibt – ein zweiter Import mit der berichtigten Datei ergänzt den Rest.
    """
    if data.format != FORMAT:
        raise ValueError("Das ist keine Einstellungs-Datei von TimberTalk.")
    if data.version > VERSION:
        raise ValueError("Die Datei stammt aus einer neueren TimberTalk-Version.")

    if data.company is not None:
        materials.save_company(session, data.company)
    for rate in data.hourly_rates:
        materials.save_hourly_rate(session, rate.name, rate.rate)

    materials_new = prices_new = 0
    known = {
        (m.name, m.einheit): m.id for m in materials.list_materials(session, show_prices=False)
    }
    for material in data.materials:
        material_id = known.get((material.name.strip(), material.unit.strip()))
        if material_id is None:
            created = materials.create_material(
                session, material.name, material.category, material.unit
            )
            material_id = known[(created.name, created.unit)] = created.id
            materials_new += 1
        have = {p.valid_from for p in materials.list_prices(session, material_id)}
        for price in material.prices:
            if price.valid_from not in have:
                materials.add_price(session, material_id, price.unit_price, price.valid_from)
                have.add(price.valid_from)
                prices_new += 1

    resources_new = resources_changed = 0
    existing = {r.name: r for r in planning.list_resources(session, include_inactive=True)}
    for resource in data.resources:
        wanted = ResourceIn(name=resource.name, category=resource.category, active=resource.active)
        current = existing.get(resource.name.strip())
        if current is None:
            current = planning.create_resource(session, wanted)
            resources_new += 1
        elif (current.category, current.active) != (resource.category, resource.active):
            current = planning.update_resource(session, current.id, wanted)
            resources_changed += 1
        rate = resource.rate_per_km
        if current.category == "vehicle" and rate is not None and rate != current.rate_per_km:
            planning.set_vehicle_rate(session, current.id, rate)

    return ImportResult(
        company=data.company is not None,
        hourly_rates=len(data.hourly_rates),
        materials_new=materials_new,
        prices_new=prices_new,
        resources_new=resources_new,
        resources_changed=resources_changed,
    )
