"""Datenzugriff auf Buchungen."""

from __future__ import annotations

from sqlalchemy.orm import Session

from timbertalk_core.db.repository import Repository
from timbertalk_core.domain.bookings.models import Booking


class BookingRepository(Repository[Booking]):
    """Datenzugriff auf Buchungen."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Booking)
