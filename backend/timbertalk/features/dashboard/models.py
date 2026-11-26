# Tabelle des Features „Dashboard“: welche Widgets eine Person in welcher Reihenfolge sehen will.

import json

from sqlmodel import Field, SQLModel


class DashboardLayout(SQLModel, table=True):
    """Die eigene Auswahl einer Person. Ohne Zeile gilt die Voreinstellung der Widgets."""

    __tablename__ = "dashboard_layout"

    account_id: int = Field(primary_key=True)
    widgets: str  # JSON-Liste der Widget-Namen, z. B. ["planning/my-week", "start/status"]

    def widget_ids(self) -> list[str]:
        return json.loads(self.widgets)


class WidgetInfo(SQLModel):
    """Ein Widget, das es gibt: Name und Adresse der Datei, die das Dashboard lädt."""

    id: str  # „<ordner>/<datei ohne .js>“, z. B. „planning/absence-requests“
    path: str  # z. B. „/features/planning/widgets/absence-requests.js“


class LayoutInfo(SQLModel):
    """Die Auswahl einer Person – None: noch nichts gewählt, es gilt die Voreinstellung."""

    widgets: list[str] | None
