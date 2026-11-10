"""Datenzugriff auf Projekte, Arbeitspakete und Abhängigkeiten."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from timbertalk_core.db.repository import Repository
from timbertalk_core.domain.projects.models import Project, WorkPackage, WorkPackageDependency


class ProjectRepository(Repository[Project]):
    """Datenzugriff auf Projekte."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Project)

    def by_number(self, number: str) -> Project | None:
        """Liefert ein Projekt anhand seiner lesbaren Nummer."""
        rows = self.list(filters=[Project.number == number], limit=1)
        return rows[0] if rows else None

    def highest_sequence_for_year(self, year: int) -> int:
        """Liefert die höchste bereits vergebene laufende Nummer eines Jahres.

        Auch gelöschte Projekte zählen mit, damit Nummern nicht doppelt vergeben werden.

        Parameter:
            year: Jahr der Projektnummer, z. B. 2026.
        """
        prefix = f"{year}-"
        numbers = self.session.scalars(select(Project.number).where(Project.number.like(f"{prefix}%")))
        hoechste = 0
        for number in numbers:
            suffix = number.removeprefix(prefix)
            if suffix.isdigit():
                hoechste = max(hoechste, int(suffix))
        return hoechste


class WorkPackageRepository(Repository[WorkPackage]):
    """Datenzugriff auf Arbeitspakete."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, WorkPackage)

    def for_project(self, project_id: uuid.UUID) -> list[WorkPackage]:
        """Liefert alle Arbeitspakete eines Projekts in Sortierreihenfolge."""
        return self.list(
            filters=[WorkPackage.project_id == project_id],
            order_by=[WorkPackage.sort_order, WorkPackage.title],
            limit=200,
        )


class WorkPackageDependencyRepository(Repository[WorkPackageDependency]):
    """Datenzugriff auf Abhängigkeiten zwischen Arbeitspaketen."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, WorkPackageDependency)

    def edges(self) -> list[tuple[uuid.UUID, uuid.UUID]]:
        """Liefert alle aktiven Abhängigkeiten als Kantenliste (Vorgänger, Nachfolger)."""
        rows = self.session.execute(
            select(WorkPackageDependency.predecessor_id, WorkPackageDependency.successor_id).where(
                WorkPackageDependency.deleted_at.is_(None)
            )
        )
        return [(row[0], row[1]) for row in rows]

    def count_for_package(self, work_package_id: uuid.UUID) -> int:
        """Zählt die aktiven Abhängigkeiten, an denen ein Arbeitspaket beteiligt ist."""
        query = (
            select(func.count())
            .select_from(WorkPackageDependency)
            .where(
                WorkPackageDependency.deleted_at.is_(None),
                (WorkPackageDependency.predecessor_id == work_package_id)
                | (WorkPackageDependency.successor_id == work_package_id),
            )
        )
        return int(self.session.scalar(query) or 0)
