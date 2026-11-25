# Tabellen des Features „Projekte“ (F3) als SQLModel-Klassen sowie die Antwort- und
# Eingabeklassen für Service und API.
# Alle Tabellennamen beginnen mit `projects_`, damit sie sich nicht mit den Tabellen anderer
# Features überschneiden.

from datetime import date

from sqlmodel import Field, SQLModel

# Erlaubte Statuswerte eines Projekts (Lastenheft LA-04, Schnittstelle S-12).
STATUS_ANGEFRAGT = "angefragt"
STATUS_GEPLANT = "geplant"
STATUS_IN_ARBEIT = "in_arbeit"
STATUS_ABGESCHLOSSEN = "abgeschlossen"
STATUS_ABGERECHNET = "abgerechnet"

PROJECT_STATUSES: tuple[str, ...] = (
    STATUS_ANGEFRAGT,
    STATUS_GEPLANT,
    STATUS_IN_ARBEIT,
    STATUS_ABGESCHLOSSEN,
    STATUS_ABGERECHNET,
)

# Statuswerte für Entwürfe der KI-Werkzeuge (S-09 / S-10, Übergang bis F7).
DRAFT_STATUS_OPEN = "draft"
DRAFT_STATUS_CONFIRMED = "confirmed"
DRAFT_STATUS_REJECTED = "rejected"


# --- Tabellen -------------------------------------------------------------------


class Project(SQLModel, table=True):
    """Ein Bauprojekt eines Kunden mit Baustelle, Zeitraum, Status und Archiv-Kennzeichen."""

    __tablename__ = "projects_project"

    id: int | None = Field(default=None, primary_key=True)
    customer_id: int = Field(index=True)  # Pflichtfeld: Verweis auf den Kunden (F2)
    customer_name: str = ""  # Anzeigename des Kunden, falls F2 noch nicht aktiv ist
    name: str  # z. B. „Carport“ oder „Dachstuhl Sanierung“
    site_address: str = ""  # Baustelle / Ort
    status: str = Field(default=STATUS_ANGEFRAGT, index=True)
    start_date: date | None = None
    duration_days: int | None = None
    end_date: date | None = None
    notes: str = ""
    archived: bool = Field(default=False, index=True)


class ProjectDraft(SQLModel, table=True):
    """Ein noch nicht bestätigter Änderungsentwurf eines KI-Werkzeugs (S-09 / S-10).

    Bis Feature F7 eine gemeinsame Entwurfstabelle mitbringt, hält F3 seine Entwürfe hier
    und führt sie über `confirm_draft()` aus.
    """

    __tablename__ = "projects_draft"

    id: int | None = Field(default=None, primary_key=True)
    action: str  # create, update, set_status, archive
    project_id: int | None = Field(default=None, index=True)
    payload_json: str
    status: str = Field(default=DRAFT_STATUS_OPEN, index=True)


# --- Antworten und Eingaben (keine Tabellen) ------------------------------------


class CustomerInfo(SQLModel):
    """Ein Kunde im Format der Schnittstelle S-03 (`get_customer`)."""

    id: int
    name: str


class ProjectInfo(SQLModel):
    """Ein Projekt im Format für Oberfläche, API und Schnittstelle S-03 (`get_project`).

    Die Feldnamen `id`, `name`, `customer_id`, `baustelle` und `status` entsprechen S-03.
    """

    id: int
    name: str
    customer_id: int
    customer_name: str
    baustelle: str
    status: str
    start_date: date | None = None
    duration_days: int | None = None
    end_date: date | None = None
    notes: str = ""
    archived: bool = False


class CustomerLookupResponse(SQLModel):
    """Kundenauswahl für die Projekt-Oberfläche samt Herkunft (`customers` = F2, sonst Übergang)."""

    source: str
    customers: list[CustomerInfo]


class CustomerProjects(SQLModel):
    """Ein Kunde mit allen seinen Projekten (für die Kunden-Projekt-Ansicht und F2)."""

    customer: CustomerInfo
    projects: list[ProjectInfo]


class ProjectCreate(SQLModel):
    """Eingabe: ein neues Projekt anlegen."""

    customer_id: int
    name: str
    baustelle: str = ""
    status: str = STATUS_ANGEFRAGT
    start_date: date | None = None
    duration_days: int | None = None
    end_date: date | None = None
    notes: str = ""
    customer_name: str = ""


class ProjectUpdate(SQLModel):
    """Eingabe: Felder eines bestehenden Projekts ändern (nur gesetzte Felder werden geändert)."""

    customer_id: int | None = None
    name: str | None = None
    baustelle: str | None = None
    status: str | None = None
    start_date: date | None = None
    duration_days: int | None = None
    end_date: date | None = None
    notes: str | None = None
    customer_name: str | None = None
    archived: bool | None = None


class ProjectStatusIn(SQLModel):
    """Eingabe: Status eines Projekts ändern."""

    status: str


class ProjectArchiveIn(SQLModel):
    """Eingabe: Projekt archivieren oder wiederherstellen."""

    archived: bool = True
