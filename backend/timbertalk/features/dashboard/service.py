# Die Logik des Features „Dashboard“ (F12) als einfache Funktionen.
#
# available_widgets() sucht alle Dateien frontend/features/*/widgets/*.js. Was ein Widget zeigt,
# welches Recht es braucht und ob es von Anfang an zu sehen ist, steht in der Datei selbst
# (siehe frontend/features/start/start.js); das Backend kennt nur Namen und Adresse.

import json

from sqlmodel import Session

from timbertalk.features.dashboard.models import DashboardLayout, LayoutInfo, WidgetInfo
from timbertalk.settings import BACKEND_DIR

FEATURES_DIR = BACKEND_DIR.parent / "frontend" / "features"


def available_widgets() -> list[WidgetInfo]:
    """Alle Widgets aller Features, nach Name sortiert."""
    widgets = []
    for path in sorted(FEATURES_DIR.glob("*/widgets/*.js")):
        folder = path.parent.parent.name
        widgets.append(
            WidgetInfo(
                id=f"{folder}/{path.stem}",
                path=f"/features/{folder}/widgets/{path.name}",
            )
        )
    return widgets


def get_layout(session: Session, account_id: int) -> LayoutInfo:
    """Die eigene Auswahl – oder None, wenn die Person noch nichts angepasst hat."""
    stored = session.get(DashboardLayout, account_id)
    return LayoutInfo(widgets=stored.widget_ids() if stored else None)


def save_layout(session: Session, account_id: int, widget_ids: list[str] | None) -> LayoutInfo:
    """Speichert Auswahl und Reihenfolge. None: zurück zur Voreinstellung."""
    stored = session.get(DashboardLayout, account_id)
    if widget_ids is None:
        if stored is not None:
            session.delete(stored)
            session.commit()
        return LayoutInfo(widgets=None)
    known = {widget.id for widget in available_widgets()}
    unknown = [widget_id for widget_id in widget_ids if widget_id not in known]
    if unknown:
        raise ValueError(f"Das Widget „{unknown[0]}“ gibt es nicht.")
    ids = list(dict.fromkeys(widget_ids))  # doppelte nur einmal
    stored = stored or DashboardLayout(account_id=account_id, widgets="[]")
    stored.widgets = json.dumps(ids)
    session.add(stored)
    session.commit()
    return LayoutInfo(widgets=ids)
