"""Geschäftslogik der Buchungen: Regeln, Statusübergänge und Preisermittlung."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from timbertalk_core.clock import utc_now
from timbertalk_core.context import ServiceContext
from timbertalk_core.db.repository import MAX_LIMIT
from timbertalk_core.domain.bookings.details import validate_details
from timbertalk_core.domain.bookings.models import Booking
from timbertalk_core.domain.bookings.repository import BookingRepository
from timbertalk_core.domain.bookings.schemas import BookingCreate, BookingRead, BookingUpdate
from timbertalk_core.domain.catalog.repository import MaterialItemRepository
from timbertalk_core.domain.catalog.service import find_valid_price
from timbertalk_core.domain.enums import BookingStatus, CostTypeKind, PriceTargetType
from timbertalk_core.domain.people.repository import EmployeeRepository
from timbertalk_core.domain.projects.repository import ProjectRepository, WorkPackageRepository
from timbertalk_core.domain.reference.custom_fields import validate_attributes, validate_decimal_scale
from timbertalk_core.domain.reference.models import CostType, Unit
from timbertalk_core.domain.reference.repository import CostTypeRepository, UnitRepository
from timbertalk_core.errors import InvalidState, ValidationFailed
from timbertalk_core.operations import operation
from timbertalk_core.schemas import Page
from timbertalk_core.service_support import (
    apply_updates,
    check_version,
    require_found,
    resolve_by_code,
)

BOOKING_DE = "Buchung"

MUTABLE_STATES = frozenset({BookingStatus.DRAFT, BookingStatus.CONFIRMED})
"""Status, in denen eine Buchung noch geändert werden darf."""


def _require_mutable(booking: Booking, vorgang_de: str) -> None:
    """Weist Änderungen an gesperrten oder storniertenBuchungen ab."""
    status = BookingStatus(booking.status)
    if status not in MUTABLE_STATES:
        raise InvalidState(
            f"{vorgang_de} ist nicht möglich: die Buchung hat den Status "
            f"'{status.value}' und ist unveränderbar.",
            status=status.value,
        )


def _resolve_unit(ctx: ServiceContext, cost_type: CostType, unit_code: str | None) -> Unit:
    """Ermittelt die Einheit einer Buchung und prüft, dass sie zur Kostenart passt."""
    code = unit_code or cost_type.default_unit_code
    unit = resolve_by_code(UnitRepository(ctx.session), Unit.code, code, "Einheit")
    if code != cost_type.default_unit_code:
        raise ValidationFailed(
            f"Die Einheit '{code}' passt nicht zur Kostenart '{cost_type.code}'; "
            f"erwartet wird '{cost_type.default_unit_code}'.",
            errors={"unit_code": f"erwartet '{cost_type.default_unit_code}'"},
            unit_code=code,
            cost_type_code=cost_type.code,
        )
    return unit


def _check_kind_rules(
    kind: CostTypeKind, employee_id: uuid.UUID | None, material_item_id: uuid.UUID | None
) -> None:
    """Prüft die Regeln, die sich aus der Art der Kostenart ergeben."""
    if kind is CostTypeKind.LABOR and employee_id is None:
        raise ValidationFailed(
            "Für eine Buchung von Arbeitszeit muss ein Mitarbeiter angegeben werden.",
            errors={"employee_id": "Pflichtfeld bei Arbeitszeit"},
        )
    if material_item_id is not None and kind is not CostTypeKind.MATERIAL:
        raise ValidationFailed(
            f"Ein Artikel kann nur bei Materialbuchungen angegeben werden, nicht bei '{kind.value}'.",
            errors={"material_item_id": "nur bei Material erlaubt"},
        )


def _check_references(
    ctx: ServiceContext,
    project_id: uuid.UUID,
    work_package_id: uuid.UUID | None,
    employee_id: uuid.UUID | None,
    material_item_id: uuid.UUID | None,
) -> None:
    """Stellt sicher, dass alle verwiesenen Datensätze existieren und zusammenpassen."""
    require_found(ProjectRepository(ctx.session).get(project_id), "Projekt", project_id)
    if work_package_id is not None:
        work_package = require_found(
            WorkPackageRepository(ctx.session).get(work_package_id), "Arbeitspaket", work_package_id
        )
        if work_package.project_id != project_id:
            raise ValidationFailed(
                "Das Arbeitspaket gehört nicht zum angegebenen Projekt.",
                errors={"work_package_id": "gehört zu einem anderen Projekt"},
            )
    if employee_id is not None:
        require_found(EmployeeRepository(ctx.session).get(employee_id), "Mitarbeiter", employee_id)
    if material_item_id is not None:
        require_found(MaterialItemRepository(ctx.session).get(material_item_id), "Artikel", material_item_id)


def _effective_price(ctx: ServiceContext, booking: Booking) -> tuple[Decimal | None, str | None]:
    """Ermittelt den geltenden Preis einer Buchung und dessen Herkunft.

    Vorrang hat ein abweichender Preis an der Buchung, danach greift die Preisliste
    des Artikels bzw. der Kostenart, zuletzt der Vorgabepreis der Kostenart.
    """
    if booking.unit_price is not None:
        return booking.unit_price, "booking"

    if booking.material_item_id is not None:
        preis = find_valid_price(
            ctx, PriceTargetType.MATERIAL_ITEM, booking.material_item_id, booking.booking_date
        )
        if preis is not None:
            return preis.unit_price, "price_material_item"

    preis = find_valid_price(ctx, PriceTargetType.COST_TYPE, booking.cost_type_id, booking.booking_date)
    if preis is not None:
        return preis.unit_price, "price_cost_type"

    cost_type = CostTypeRepository(ctx.session).get(booking.cost_type_id, include_deleted=True)
    if cost_type is not None and cost_type.default_unit_price is not None:
        return cost_type.default_unit_price, "cost_type_default"
    return None, None


def to_read(ctx: ServiceContext, booking: Booking) -> BookingRead:
    """Baut das Lese-Schema einer Buchung samt Kostenart, geltendem Preis und Betrag.

    Parameter:
        ctx: Aufrufkontext mit offener Session.
        booking: die Buchung aus der Datenbank.
    """
    cost_type = require_found(
        CostTypeRepository(ctx.session).get(booking.cost_type_id, include_deleted=True),
        "Kostenart",
        booking.cost_type_id,
    )
    preis, herkunft = _effective_price(ctx, booking)
    betrag = booking.quantity * preis if preis is not None else None
    return BookingRead.model_validate(
        {
            **{spalte.key: getattr(booking, spalte.key) for spalte in booking.__mapper__.column_attrs},
            "cost_type_code": cost_type.code,
            "cost_type_kind": CostTypeKind(cost_type.kind),
            "effective_unit_price": preis,
            "amount": betrag,
            "price_origin": herkunft,
        }
    )


@operation(name="booking.create", read_only=False, summary_de="Legt eine Buchung an.")
def create_booking(ctx: ServiceContext, data: BookingCreate) -> BookingRead:
    """Legt eine Buchung an; Einträge aus KI, Sprache, Import oder CAD starten als `draft`.

    Die Einheit muss zur Kostenart passen, bei Arbeitszeit ist ein Mitarbeiter Pflicht,
    und die Detailfelder werden gegen das Schema der Buchungsart geprüft.

    Parameter:
        data: Projekt, Kostenart, Tag der Leistung, Menge und art-spezifische Details.
    """
    repository = BookingRepository(ctx.session)
    cost_type = require_found(
        CostTypeRepository(ctx.session).get(data.cost_type_id), "Kostenart", data.cost_type_id
    )
    kind = CostTypeKind(cost_type.kind)

    unit = _resolve_unit(ctx, cost_type, data.unit_code)
    validate_decimal_scale(data.quantity, unit.decimals, "quantity")
    _check_kind_rules(kind, data.employee_id, data.material_item_id)
    _check_references(ctx, data.project_id, data.work_package_id, data.employee_id, data.material_item_id)

    values = data.model_dump()
    values["unit_code"] = unit.code
    values["details"] = validate_details(kind, values["details"])
    values["attributes"] = validate_attributes(ctx, Booking.__tablename__, values["attributes"])
    values["source"] = data.source.value
    # Jede neue Buchung beginnt als Entwurf. Für Einträge aus KI, Sprache, Import
    # oder CAD fordert der Auftrag das ausdrücklich; für Einträge von Hand gilt es
    # ebenso, damit das Bestätigen immer ein eigener, menschlicher Schritt bleibt.
    values["status"] = BookingStatus.DRAFT.value

    booking = repository.add(Booking(**values))
    ctx.flush()
    return to_read(ctx, booking)


@operation(name="booking.get", read_only=True, summary_de="Liest eine Buchung.")
def get_booking(ctx: ServiceContext, booking_id: uuid.UUID) -> BookingRead:
    """Liest eine Buchung anhand ihrer Kennung.

    Parameter:
        booking_id: Kennung der Buchung.
    """
    booking = require_found(BookingRepository(ctx.session).get(booking_id), BOOKING_DE, booking_id)
    return to_read(ctx, booking)


@operation(name="booking.list", read_only=True, summary_de="Listet Buchungen.")
def list_bookings(
    ctx: ServiceContext,
    project_id: uuid.UUID | None = None,
    work_package_id: uuid.UUID | None = None,
    employee_id: uuid.UUID | None = None,
    cost_type_id: uuid.UUID | None = None,
    status: BookingStatus | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[BookingRead]:
    """Listet Buchungen mit Paging und Filtern.

    Parameter:
        project_id: Kennung des Projekts.
        work_package_id: Kennung des Arbeitspakets.
        employee_id: Kennung des Mitarbeiters.
        cost_type_id: Kennung der Kostenart.
        status: Status (`draft`, `confirmed`, `locked`, `cancelled`).
        date_from: frühester Leistungstag.
        date_to: spätester Leistungstag.
        limit: maximale Anzahl Datensätze (höchstens 200).
        offset: Anzahl übersprungener Datensätze.
    """
    filters = []
    if project_id is not None:
        filters.append(Booking.project_id == project_id)
    if work_package_id is not None:
        filters.append(Booking.work_package_id == work_package_id)
    if employee_id is not None:
        filters.append(Booking.employee_id == employee_id)
    if cost_type_id is not None:
        filters.append(Booking.cost_type_id == cost_type_id)
    if status is not None:
        filters.append(Booking.status == status.value)
    if date_from is not None:
        filters.append(Booking.booking_date >= date_from)
    if date_to is not None:
        filters.append(Booking.booking_date <= date_to)

    repository = BookingRepository(ctx.session)
    effektives_limit = max(1, min(limit, MAX_LIMIT))
    rows = repository.list(
        filters=filters,
        order_by=[Booking.booking_date.desc(), Booking.created_at.desc()],
        limit=effektives_limit,
        offset=offset,
    )
    return Page[BookingRead](
        items=[to_read(ctx, row) for row in rows],
        total=repository.count(filters=filters),
        limit=effektives_limit,
        offset=offset,
    )


@operation(name="booking.update", read_only=False, summary_de="Ändert eine Buchung.")
def update_booking(
    ctx: ServiceContext,
    booking_id: uuid.UUID,
    data: BookingUpdate,
    expected_version: int | None = None,
) -> BookingRead:
    """Ändert eine Buchung; `locked` und `cancelled` sind unveränderbar.

    Parameter:
        booking_id: Kennung der Buchung.
        data: zu ändernde Felder.
        expected_version: erwartete Version für optimistisches Sperren.
    """
    repository = BookingRepository(ctx.session)
    booking = require_found(repository.get(booking_id), BOOKING_DE, booking_id)
    check_version(booking, expected_version, BOOKING_DE)
    _require_mutable(booking, "Ändern")

    cost_type = require_found(
        CostTypeRepository(ctx.session).get(booking.cost_type_id, include_deleted=True),
        "Kostenart",
        booking.cost_type_id,
    )
    kind = CostTypeKind(cost_type.kind)
    changes = data.model_dump(exclude_unset=True)

    if "unit_code" in changes and changes["unit_code"] is not None:
        unit = _resolve_unit(ctx, cost_type, changes["unit_code"])
    else:
        unit = resolve_by_code(UnitRepository(ctx.session), Unit.code, booking.unit_code, "Einheit")
    if "quantity" in changes and changes["quantity"] is not None:
        validate_decimal_scale(changes["quantity"], unit.decimals, "quantity")

    neuer_mitarbeiter = changes.get("employee_id", booking.employee_id)
    neuer_artikel = changes.get("material_item_id", booking.material_item_id)
    _check_kind_rules(kind, neuer_mitarbeiter, neuer_artikel)
    _check_references(
        ctx,
        booking.project_id,
        changes.get("work_package_id", booking.work_package_id),
        neuer_mitarbeiter,
        neuer_artikel,
    )

    apply_updates(booking, data, skip=["details", "attributes"])
    if "details" in changes:
        booking.details = validate_details(kind, changes["details"])
    if "attributes" in changes:
        booking.attributes = validate_attributes(ctx, Booking.__tablename__, changes["attributes"])
    ctx.flush()
    return to_read(ctx, booking)


@operation(name="booking.confirm", read_only=False, summary_de="Bestätigt eine Buchung.")
def confirm_booking(
    ctx: ServiceContext, booking_id: uuid.UUID, expected_version: int | None = None
) -> BookingRead:
    """Bestätigt eine Buchung; nur ein menschlicher Akteur darf das.

    Parameter:
        booking_id: Kennung der Buchung.
        expected_version: erwartete Version für optimistisches Sperren.
    """
    ctx.require_human("Das Bestätigen einer Buchung")
    repository = BookingRepository(ctx.session)
    booking = require_found(repository.get(booking_id), BOOKING_DE, booking_id)
    check_version(booking, expected_version, BOOKING_DE)

    status = BookingStatus(booking.status)
    if status is BookingStatus.CONFIRMED:
        return to_read(ctx, booking)
    if status is not BookingStatus.DRAFT:
        raise InvalidState(
            f"Nur Buchungen im Status 'draft' können bestätigt werden, nicht '{status.value}'.",
            status=status.value,
        )

    booking.status = BookingStatus.CONFIRMED.value
    booking.confirmed_by = ctx.actor_id
    booking.confirmed_at = utc_now()
    ctx.with_action("confirm")
    ctx.flush()
    return to_read(ctx, booking)


@operation(name="booking.cancel", read_only=False, summary_de="Storniert eine Buchung.")
def cancel_booking(
    ctx: ServiceContext, booking_id: uuid.UUID, expected_version: int | None = None
) -> BookingRead:
    """Storniert eine Buchung; gesperrte Buchungen können nicht storniert werden.

    Parameter:
        booking_id: Kennung der Buchung.
        expected_version: erwartete Version für optimistisches Sperren.
    """
    repository = BookingRepository(ctx.session)
    booking = require_found(repository.get(booking_id), BOOKING_DE, booking_id)
    check_version(booking, expected_version, BOOKING_DE)

    status = BookingStatus(booking.status)
    if status is BookingStatus.CANCELLED:
        return to_read(ctx, booking)
    if status is BookingStatus.LOCKED:
        raise InvalidState(
            "Eine gesperrte Buchung kann nicht storniert werden; sie gehört zu einer Rechnung.",
            status=status.value,
        )

    booking.status = BookingStatus.CANCELLED.value
    ctx.with_action("cancel")
    ctx.flush()
    return to_read(ctx, booking)


@operation(name="booking.delete", read_only=False, summary_de="Löscht eine Buchung (Soft Delete).")
def delete_booking(
    ctx: ServiceContext, booking_id: uuid.UUID, expected_version: int | None = None
) -> BookingRead:
    """Markiert eine Buchung als gelöscht; gesperrte Buchungen bleiben erhalten.

    Parameter:
        booking_id: Kennung der Buchung.
        expected_version: erwartete Version für optimistisches Sperren.
    """
    repository = BookingRepository(ctx.session)
    booking = require_found(repository.get(booking_id), BOOKING_DE, booking_id)
    check_version(booking, expected_version, BOOKING_DE)
    if BookingStatus(booking.status) is BookingStatus.LOCKED:
        raise InvalidState(
            "Eine gesperrte Buchung kann nicht gelöscht werden; sie gehört zu einer Rechnung.",
            status=BookingStatus.LOCKED.value,
        )
    repository.soft_delete(booking)
    ctx.flush()
    return to_read(ctx, booking)
