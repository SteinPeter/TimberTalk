"""Datenzugriff auf Kunden."""

from __future__ import annotations

from sqlalchemy.orm import Session

from timbertalk_core.db.repository import Repository
from timbertalk_core.domain.customers.models import Customer


class CustomerRepository(Repository[Customer]):
    """Datenzugriff auf Kunden."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Customer)
