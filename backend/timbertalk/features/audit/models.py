# Tabelle des Features „Änderungsprotokoll“ als SQLModel-Klasse. Der Name beginnt mit `audit_`.

from datetime import datetime

from sqlmodel import Field, SQLModel


class AuditEvent(SQLModel, table=True):
    """Eine Änderung: wer hat wann was gemacht. Einträge werden nie geändert oder gelöscht."""

    __tablename__ = "audit_event"

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(index=True)
    account_id: int | None = Field(default=None, index=True)
    account_name: str  # der Name zu diesem Zeitpunkt – bleibt, auch wenn das Konto umbenannt wird
    area: str = Field(index=True)  # Bereich, z. B. „Material, Fahrten und Preise“
    action: str  # was, z. B. „Preis eintragen“
    target: str = ""  # welcher Datensatz, z. B. „Nr. 3“
    details: str = ""  # die Angaben, z. B. „unit_price: 13.00 · valid_from: 2026-02-01“
    method: str  # POST, PUT oder DELETE
    path: str  # die Adresse, z. B. /api/materials/items/3/prices
