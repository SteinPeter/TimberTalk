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
