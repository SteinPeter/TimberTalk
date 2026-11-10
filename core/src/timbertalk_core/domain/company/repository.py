"""Datenzugriff auf Firmendaten, Einstellungen und Steuersätze."""

from __future__ import annotations

from sqlalchemy.orm import Session

from timbertalk_core.db.repository import Repository
from timbertalk_core.domain.company.models import Company, Setting, TaxRate


class CompanyRepository(Repository[Company]):
    """Datenzugriff auf die Firmendaten; es gibt genau einen aktiven Datensatz."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Company)

    def current(self) -> Company | None:
        """Liefert den aktiven Firmendatensatz, falls vorhanden."""
        rows = self.list(order_by=[Company.created_at], limit=1)
        return rows[0] if rows else None


class SettingRepository(Repository[Setting]):
    """Datenzugriff auf Einstellungen."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Setting)

    def by_key(self, key: str) -> Setting | None:
        """Liefert eine Einstellung anhand ihres Schlüssels."""
        rows = self.list(filters=[Setting.key == key], limit=1)
        return rows[0] if rows else None


class TaxRateRepository(Repository[TaxRate]):
    """Datenzugriff auf Steuersätze."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, TaxRate)

    def by_code(self, code: str) -> list[TaxRate]:
        """Liefert alle Gültigkeitszeiträume eines Steuersatz-Codes."""
        return self.list(filters=[TaxRate.code == code], order_by=[TaxRate.valid_from], limit=200)
