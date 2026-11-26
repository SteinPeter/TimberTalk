# Tests für das Feature „Dashboard“ (F12).
# Fixtures aus backend/conftest.py: `session`, `client_as`.

import re
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from timbertalk.features.dashboard import service


def test_widgets_werden_in_den_feature_ordnern_gefunden() -> None:
    ids = [widget.id for widget in service.available_widgets()]
    assert "planning/absence-requests" in ids
    assert "start/status" in ids
    for widget in service.available_widgets():
        assert widget.path == f"/features/{widget.id.replace('/', '/widgets/')}.js"


@pytest.mark.parametrize("widget", service.available_widgets(), ids=lambda w: w.id)
def test_jedes_widget_hat_titel_und_render(widget) -> None:
    # Der Vertrag aus frontend/features/start/start.js: title und render(container).
    text = (service.FEATURES_DIR.parent / widget.path.lstrip("/")).read_text()
    assert re.search(r"export const title = ", text), widget.id
    assert re.search(r"export (async )?function render\(", text), widget.id


def test_eigene_auswahl_speichern_und_zuruecksetzen(session: Session) -> None:
    assert service.get_layout(session, 1).widgets is None
    saved = service.save_layout(session, 1, ["start/status", "planning/my-week", "start/status"])
    assert saved.widgets == ["start/status", "planning/my-week"]
    assert service.get_layout(session, 2).widgets is None  # jede Person für sich
    with pytest.raises(ValueError, match="gibt es nicht"):
        service.save_layout(session, 1, ["gibt/es-nicht"])
    assert service.save_layout(session, 1, None).widgets is None


def test_api_dashboard(client_as: Callable[[str], TestClient]) -> None:
    geselle = client_as("journeyman")
    assert len(geselle.get("/api/dashboard/widgets").json()) >= 2
    assert geselle.put("/api/dashboard/layout", json={"widgets": ["start/status"]}).json() == {
        "widgets": ["start/status"]
    }
    assert geselle.get("/api/dashboard/layout").json() == {"widgets": ["start/status"]}
