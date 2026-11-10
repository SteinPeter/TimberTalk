"""Datenzugriff auf Modellpreise und KI-Verbrauch."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from timbertalk_core.db.repository import Repository
from timbertalk_core.domain.usage.models import LlmUsage, ModelPrice


class ModelPriceRepository(Repository[ModelPrice]):
    """Datenzugriff auf Modellpreise."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, ModelPrice)

    def valid_on(self, provider: str, model: str, on_date: date) -> ModelPrice | None:
        """Liefert den an einem Tag gültigen Preis eines Modells.

        Gültig ist der jüngste Preis, dessen `valid_from` nicht in der Zukunft liegt.

        Parameter:
            provider: Anbieter des Modells.
            model: Modellkennung.
            on_date: Stichtag.
        """
        rows = self.list(
            filters=[
                ModelPrice.provider == provider,
                ModelPrice.model == model,
                ModelPrice.valid_from <= on_date,
            ],
            order_by=[ModelPrice.valid_from.desc()],
            limit=1,
        )
        return rows[0] if rows else None


class LlmUsageRepository(Repository[LlmUsage]):
    """Datenzugriff auf den KI-Verbrauch."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, LlmUsage)

    def in_period(self, start: datetime, end: datetime) -> Sequence[LlmUsage]:
        """Liefert alle Aufrufe eines Zeitraums (einschließlich Beginn, ausschließlich Ende).

        Diese Abfrage ist für die Verbrauchsübersicht gedacht und kennt deshalb keine
        Seitengröße. Die Gruppierung erfolgt in Python, damit sie auf SQLite und
        Postgres gleich arbeitet.

        Parameter:
            start: Beginn des Zeitraums (UTC).
            end: Ende des Zeitraums (UTC).
        """
        query = (
            select(LlmUsage)
            .where(
                LlmUsage.deleted_at.is_(None),
                LlmUsage.occurred_at >= start,
                LlmUsage.occurred_at < end,
            )
            .order_by(LlmUsage.occurred_at)
        )
        return self.session.scalars(query).all()
