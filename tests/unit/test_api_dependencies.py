"""Tests for HTTP API dependency wiring."""

from pathlib import Path

import pytest
from fastapi import HTTPException

from life_claims.api.main import get_claims_repository
from life_claims.infrastructure.sqlite_claims_repository import (
    SQLiteClaimsRepository,
)


def test_repository_dependency_uses_configured_database(
    monkeypatch,
    tmp_path,
):
    database_path = tmp_path / "claims.sqlite3"
    monkeypatch.setenv("CLAIMS_DB_PATH", str(database_path))

    repository = get_claims_repository()

    assert isinstance(repository, SQLiteClaimsRepository)
    assert repository.database_path == database_path


def test_repository_dependency_requires_configuration(monkeypatch):
    monkeypatch.delenv("CLAIMS_DB_PATH", raising=False)

    with pytest.raises(HTTPException) as exc_info:
        get_claims_repository()

    assert exc_info.value.status_code == 503


def test_repository_dependency_accepts_absolute_path(
    monkeypatch,
    tmp_path,
):
    database_path = Path(tmp_path / "custom.sqlite3")
    monkeypatch.setenv("CLAIMS_DB_PATH", str(database_path))

    repository = get_claims_repository()

    assert repository.database_path == database_path
