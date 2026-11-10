"""Datenzugriff auf Mitarbeiter."""

from __future__ import annotations

from sqlalchemy.orm import Session

from timbertalk_core.db.repository import Repository
from timbertalk_core.domain.people.models import Employee


class EmployeeRepository(Repository[Employee]):
    """Datenzugriff auf Mitarbeiter."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Employee)
