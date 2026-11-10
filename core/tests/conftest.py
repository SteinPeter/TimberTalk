"""Gemeinsame Test-Fixtures."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from timbertalk_core.api.app import create_app


@pytest.fixture
def app() -> FastAPI:
    """Frische FastAPI-Anwendung für einen Test."""
    return create_app()


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """HTTP-Client gegen die Anwendung."""
    with TestClient(app) as test_client:
        yield test_client
