"""Prüft das Laden der Einstellungen."""

from __future__ import annotations

from pathlib import Path

import pytest

from timbertalk_core.config import Settings, get_settings


def test_standardwerte() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.environment == "local"
    assert settings.database_url.startswith("sqlite")
    assert settings.data_dir == Path("data")


def test_liest_env_datei(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "TIMBERTALK_ENVIRONMENT=test\nTIMBERTALK_DATA_DIR=/tmp/tt-data\nTIMBERTALK_API_KEY=geheim\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    settings = Settings()
    assert settings.environment == "test"
    assert settings.data_dir == Path("/tmp/tt-data")
    assert settings.api_key == "geheim"
    assert settings.attachments_dir == Path("/tmp/tt-data/attachments")


def test_umgebungsvariable_hat_vorrang(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TIMBERTALK_API_KEY", "aus-umgebung")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.api_key == "aus-umgebung"


def test_get_settings_ist_zwischengespeichert() -> None:
    assert get_settings() is get_settings()


@pytest.mark.parametrize(
    ("environment", "dev_ui", "erwartet"),
    [
        ("local", None, True),
        ("test", None, False),
        ("production", None, False),
        ("local", False, False),
        ("test", True, True),
        ("production", True, True),
    ],
)
def test_dev_ui_folgt_der_betriebsart(environment: str, dev_ui: bool | None, erwartet: bool) -> None:
    """Ohne Angabe zeigt nur `local` die Werkbank; `dev_ui` übersteuert beidseitig."""
    settings = Settings(_env_file=None, environment=environment, dev_ui=dev_ui)  # type: ignore[call-arg,arg-type]
    assert settings.dev_ui_enabled is erwartet


def test_dev_ui_kommt_aus_der_umgebung(monkeypatch: pytest.MonkeyPatch) -> None:
    """`TIMBERTALK_DEV_UI=false` schaltet die Werkbank auch lokal ab."""
    monkeypatch.setenv("TIMBERTALK_DEV_UI", "false")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.environment == "local"
    assert settings.dev_ui_enabled is False
