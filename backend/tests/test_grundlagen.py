# Prüft die Grundlagen, auf die sich alle Features verlassen: die Datenbank im Arbeitsspeicher
# für Tests und das selbstständige Finden der Feature-Ordner.

import importlib
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import APIRouter
from sqlalchemy import Engine, text

from timbertalk.features import feature_names, load_features


def test_datenbank_im_speicher_ist_fuer_alle_verbindungen_dieselbe(engine: Engine) -> None:
    # Ohne StaticPool sähe die zweite Verbindung eine eigene, leere Datenbank.
    with engine.begin() as first:
        first.execute(text("CREATE TABLE probe (name TEXT)"))
        first.execute(text("INSERT INTO probe VALUES ('holz')"))
    with engine.connect() as second:
        assert second.execute(text("SELECT name FROM probe")).scalar() == "holz"


def test_jeder_test_bekommt_eine_leere_datenbank(engine: Engine) -> None:
    # Die Tabelle aus dem Test davor darf hier nicht mehr da sein.
    with engine.connect() as connection:
        tables = connection.execute(text("SELECT name FROM sqlite_master")).all()
    assert ("probe",) not in tables


def _write(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture
def fake_features(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """Ein nachgebautes features-Paket mit drei Ordnern, nur für diese Tests."""
    root = tmp_path / "probe_features"
    _write(root / "__init__.py")
    # alpha: hat eine api.py mit Router
    _write(root / "alpha" / "__init__.py")
    _write(
        root / "alpha" / "api.py",
        "from fastapi import APIRouter\nrouter = APIRouter(prefix='/api/alpha')\n",
    )
    # beta: hat nur Tabellen, keine Endpunkte
    _write(root / "beta" / "__init__.py")
    _write(root / "beta" / "models.py", "LOADED = True\n")
    # ohne_init: kein Feature, weil __init__.py fehlt
    _write(root / "ohne_init" / "api.py", "raise RuntimeError('darf nicht geladen werden')\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    yield "probe_features"
    # Python merkt sich geladene Module. Damit der nächste Test sein eigenes Paket bekommt,
    # wird das nachgebaute Paket danach wieder vergessen.
    for module_name in list(sys.modules):
        if module_name.split(".")[0] == "probe_features":
            del sys.modules[module_name]
    importlib.invalidate_caches()


def test_feature_ordner_werden_selbst_gefunden(fake_features: str) -> None:
    assert feature_names(fake_features) == ["alpha", "beta"]


def test_router_aus_api_py_werden_geladen(fake_features: str) -> None:
    routers = load_features(fake_features)
    assert [router.prefix for router in routers] == ["/api/alpha"]
    assert all(isinstance(router, APIRouter) for router in routers)
    # models.py wird auch ohne api.py geladen, damit die Tabellen angelegt werden.
    assert sys.modules[f"{fake_features}.beta.models"].LOADED is True


def test_api_py_ohne_router_ist_ein_fehler(fake_features: str, tmp_path: Path) -> None:
    _write(tmp_path / fake_features / "gamma" / "__init__.py")
    _write(tmp_path / fake_features / "gamma" / "api.py", "# router vergessen\n")
    with pytest.raises(RuntimeError, match="router"):
        load_features(fake_features)
