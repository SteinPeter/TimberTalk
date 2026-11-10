"""Fachliche Wertelisten; in der Datenbank als Zeichenketten, geprüft in Pydantic."""

from __future__ import annotations

from enum import StrEnum


class CostTypeKind(StrEnum):
    """Art einer Kostenart; bestimmt, welche Detailfelder einer Buchung gelten."""

    LABOR = "labor"
    MATERIAL = "material"
    TRAVEL = "travel"
    EQUIPMENT = "equipment"
    OTHER = "other"


class CustomFieldDataType(StrEnum):
    """Datentyp eines Zusatzfeldes in `attributes`."""

    TEXT = "text"
    INT = "int"
    DECIMAL = "decimal"
    DATE = "date"
    BOOL = "bool"
    ENUM = "enum"


class EmployeeRole(StrEnum):
    """Rolle eines Mitarbeiters im Betrieb."""

    OWNER = "owner"
    MASTER = "master"
    JOURNEYMAN = "journeyman"
    APPRENTICE = "apprentice"
    OFFICE = "office"


class CustomerType(StrEnum):
    """Art eines Kunden; steuert später die Rechnungsregeln."""

    PRIVATE = "private"
    BUSINESS = "business"


class ProjectStatus(StrEnum):
    """Status eines Projekts von der Anfrage bis zum Abschluss."""

    INQUIRY = "inquiry"
    PLANNED = "planned"
    ACTIVE = "active"
    DONE = "done"
    CANCELLED = "cancelled"


class WorkPackageStatus(StrEnum):
    """Status eines Arbeitspakets."""

    PLANNED = "planned"
    ACTIVE = "active"
    DONE = "done"
    CANCELLED = "cancelled"


class DependencyType(StrEnum):
    """Art einer Abhängigkeit zwischen Arbeitspaketen (Gantt)."""

    FINISH_TO_START = "finish_to_start"


class MaterialCategory(StrEnum):
    """Kategorie eines Artikels im Materialkatalog."""

    TIMBER = "timber"
    FASTENERS = "fasteners"
    INSULATION = "insulation"
    MEMBRANE = "membrane"
    OTHER = "other"


class PriceTargetType(StrEnum):
    """Worauf sich ein Preis bezieht."""

    MATERIAL_ITEM = "material_item"
    COST_TYPE = "cost_type"


class PriceSource(StrEnum):
    """Herkunft eines Preises."""

    MANUAL = "manual"
    IMPORT = "import"
    SUPPLIER = "supplier"


class BookingStatus(StrEnum):
    """Status einer Buchung; `locked` setzt erst die Rechnung (Block 3)."""

    DRAFT = "draft"
    CONFIRMED = "confirmed"
    LOCKED = "locked"
    CANCELLED = "cancelled"


class DistanceMethod(StrEnum):
    """Wie eine Fahrtstrecke ermittelt wurde."""

    MANUAL = "manual"
    ROUTE = "route"
