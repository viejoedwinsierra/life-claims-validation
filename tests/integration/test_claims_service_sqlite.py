"""Integration tests for application service with SQLite."""

import sqlite3
from datetime import date
from pathlib import Path
from unittest.mock import Mock

from life_claims.application.claims_service import ClaimsApplicationService
from life_claims.infrastructure.sqlite_claims_repository import (
    SQLiteClaimsRepository,
)

MIGRATION = Path(__file__).resolve().parents[2] / "datos" / "migrations" / "001_create_claims.sql"


def test_existing_request_does_not_call_core_again(tmp_path):
    """An existing request must not trigger another core operation."""
    database_path = tmp_path / "claims.db"

    with sqlite3.connect(database_path) as connection:
        connection.executescript(MIGRATION.read_text(encoding="utf-8"))

    repository = SQLiteClaimsRepository(database_path)

    claim = {
        "id_solicitud": "SOL-TEST-005-011",
        "numero_poliza": "AV-VI-0100000",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "2123456789",
        },
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
        "fecha_radicacion": "2026-01-15T10:30:00",
    }

    assert repository.reserve_claim(claim) == "CREATED"

    repository.save_result(
        id_solicitud=claim["id_solicitud"],
        estado="REGISTERED",
        motivos_rechazo=[],
        numero_siniestro="SIN-TEST-011",
    )

    core_client = Mock()

    service = ClaimsApplicationService(
        core_client=core_client,
        repository=repository,
        today_provider=lambda: date(2026, 2, 1),
    )

    result = service.submit_claim(claim)

    assert result["id_solicitud"] == claim["id_solicitud"]
    assert result["estado"] == "REGISTERED"
    assert result["numero_siniestro"] == "SIN-TEST-011"

    core_client.get_policy.assert_not_called()
    core_client.create_claim.assert_not_called()


def test_rejected_claim_is_persisted_and_replayed_without_core_call(tmp_path):
    """A rejected claim must persist and replay without another core call."""
    database_path = tmp_path / "claims.db"

    with sqlite3.connect(database_path) as connection:
        connection.executescript(MIGRATION.read_text(encoding="utf-8"))

    repository = SQLiteClaimsRepository(database_path)

    claim = {
        "id_solicitud": "SOL-TEST-005-012",
        "numero_poliza": "AV-VI-NO-EXISTE",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "2123456789",
        },
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
        "fecha_radicacion": "2026-01-15T10:30:00",
    }

    core_client = Mock()
    core_client.get_policy.return_value = None

    service = ClaimsApplicationService(
        core_client=core_client,
        repository=repository,
        today_provider=lambda: date(2026, 2, 1),
    )

    first_result = service.submit_claim(claim)

    assert first_result["estado"] == "REJECTED"
    assert "R1" in first_result["motivos_rechazo"]
    assert first_result["numero_siniestro"] is None

    stored = repository.get_by_request_id(claim["id_solicitud"])

    assert stored is not None
    assert stored["estado"] == "REJECTED"
    assert "R1" in stored["motivos_rechazo"]

    second_result = service.submit_claim(claim)

    assert second_result == first_result

    core_client.get_policy.assert_called_once_with("AV-VI-NO-EXISTE")
    core_client.create_claim.assert_not_called()


def test_registered_claim_is_persisted_and_replayed_after_reopening_db(tmp_path):
    """A registered claim must survive reopening SQLite without another core call."""
    database_path = tmp_path / "claims.db"

    with sqlite3.connect(database_path) as connection:
        connection.executescript(MIGRATION.read_text(encoding="utf-8"))

    claim = {
        "id_solicitud": "SOL-TEST-005-013",
        "numero_poliza": "AV-VI-0100000",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "2123456789",
        },
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
        "fecha_radicacion": "2026-01-15T10:30:00",
    }

    core_client = Mock()
    core_client.get_policy.return_value = {
        "numero_poliza": "AV-VI-0100000",
        "tipo_documento_asegurado": "CC",
        "numero_documento_asegurado": "2123456789",
        "fecha_inicio_vigencia": "2020-01-01",
        "fecha_fin_vigencia": "2030-12-31",
        "estado": "VIGENTE",
        "fecha_cambio_estado": "2020-01-01",
        "amparos": ["MUERTE"],
    }
    core_client.create_claim.return_value = {
        "numero_siniestro": "SIN-TEST-013",
        "estado_core": "REGISTRADO",
    }

    repository = SQLiteClaimsRepository(database_path)

    service = ClaimsApplicationService(
        core_client=core_client,
        repository=repository,
        today_provider=lambda: date(2026, 2, 1),
    )

    first_result = service.submit_claim(claim)

    assert first_result["estado"] == "REGISTERED"
    assert first_result["numero_siniestro"] == "SIN-TEST-013"

    core_client.create_claim.assert_called_once_with(
        payload={
            "numero_poliza": "AV-VI-0100000",
            "numero_documento_asegurado": "2123456789",
            "tipo_reclamacion": "MUERTE",
            "fecha_siniestro": "2026-01-01",
        },
        idempotency_key="SOL-TEST-005-013",
    )

    reopened_repository = SQLiteClaimsRepository(database_path)

    stored = reopened_repository.get_by_request_id("SOL-TEST-005-013")

    assert stored is not None
    assert stored["estado"] == "REGISTERED"
    assert stored["numero_siniestro"] == "SIN-TEST-013"

    replay_service = ClaimsApplicationService(
        core_client=core_client,
        repository=reopened_repository,
        today_provider=lambda: date(2026, 2, 1),
    )

    second_result = replay_service.submit_claim(claim)

    assert second_result == first_result
    core_client.get_policy.assert_called_once()
    core_client.create_claim.assert_called_once()


def test_same_request_id_with_different_payload_is_rejected(tmp_path):
    """Different payloads with the same request ID must not reach the core."""
    database_path = tmp_path / "claims.db"

    with sqlite3.connect(database_path) as connection:
        connection.executescript(MIGRATION.read_text(encoding="utf-8"))

    repository = SQLiteClaimsRepository(database_path)

    original_claim = {
        "id_solicitud": "SOL-TEST-005-014",
        "numero_poliza": "AV-VI-0100000",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "2123456789",
        },
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
        "fecha_radicacion": "2026-01-15T10:30:00",
    }

    assert repository.reserve_claim(original_claim) == "CREATED"

    repository.save_result(
        id_solicitud=original_claim["id_solicitud"],
        estado="REGISTERED",
        motivos_rechazo=[],
        numero_siniestro="SIN-TEST-014",
    )

    modified_claim = {
        **original_claim,
        "fecha_siniestro": "2026-01-02",
    }

    core_client = Mock()

    service = ClaimsApplicationService(
        core_client=core_client,
        repository=repository,
        today_provider=lambda: date(2026, 2, 1),
    )

    import pytest

    with pytest.raises(ValueError, match="Idempotency conflict"):
        service.submit_claim(modified_claim)

    stored = repository.get_by_request_id(original_claim["id_solicitud"])

    assert stored is not None
    assert stored["estado"] == "REGISTERED"
    assert stored["numero_siniestro"] == "SIN-TEST-014"

    core_client.get_policy.assert_not_called()
    core_client.create_claim.assert_not_called()


def test_core_timeout_persists_pending_confirmation_without_retry(tmp_path):
    """An uncertain core result must remain pending without a second POST."""
    import httpx

    database_path = tmp_path / "claims.db"

    with sqlite3.connect(database_path) as connection:
        connection.executescript(MIGRATION.read_text(encoding="utf-8"))

    repository = SQLiteClaimsRepository(database_path)

    claim = {
        "id_solicitud": "SOL-TEST-005-015",
        "numero_poliza": "AV-VI-0100000",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "2123456789",
        },
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
        "fecha_radicacion": "2026-01-15T10:30:00",
    }

    core_client = Mock()
    core_client.get_policy.return_value = {
        "numero_poliza": "AV-VI-0100000",
        "tipo_documento_asegurado": "CC",
        "numero_documento_asegurado": "2123456789",
        "fecha_inicio_vigencia": "2020-01-01",
        "fecha_fin_vigencia": "2030-12-31",
        "estado": "VIGENTE",
        "fecha_cambio_estado": "2020-01-01",
        "amparos": ["MUERTE"],
    }
    core_client.create_claim.side_effect = httpx.ReadTimeout("Core response timed out")

    service = ClaimsApplicationService(
        core_client=core_client,
        repository=repository,
        today_provider=lambda: date(2026, 2, 1),
    )

    first_result = service.submit_claim(claim)

    assert first_result["estado"] == "PENDING_CONFIRMATION"
    assert first_result["numero_siniestro"] is None

    stored = repository.get_by_request_id(claim["id_solicitud"])

    assert stored is not None
    assert stored["estado"] == "PENDING_CONFIRMATION"

    second_result = service.submit_claim(claim)

    assert second_result == first_result
    core_client.create_claim.assert_called_once()


def test_registered_business_duplicate_returns_r8_without_core_call(tmp_path):
    """A registered event must reject a different request ID with R8."""
    database_path = tmp_path / "claims.db"

    with sqlite3.connect(database_path) as connection:
        connection.executescript(MIGRATION.read_text(encoding="utf-8"))

    repository = SQLiteClaimsRepository(database_path)

    original = {
        "id_solicitud": "SOL-TEST-005-018-A",
        "numero_poliza": "AV-VI-0100000",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "2123456789",
        },
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
        "fecha_radicacion": "2026-01-15T10:30:00",
    }

    duplicate = {
        **original,
        "id_solicitud": "SOL-TEST-005-018-B",
    }

    assert repository.reserve_claim(original) == "CREATED"

    repository.save_result(
        id_solicitud=original["id_solicitud"],
        estado="REGISTERED",
        motivos_rechazo=[],
        numero_siniestro="SIN-TEST-018",
    )

    core_client = Mock()

    service = ClaimsApplicationService(
        core_client=core_client,
        repository=repository,
        today_provider=lambda: date(2026, 2, 1),
    )

    result = service.submit_claim(duplicate)

    assert result == {
        "id_solicitud": duplicate["id_solicitud"],
        "estado": "REJECTED",
        "numero_siniestro": None,
        "motivos_rechazo": ["R8"],
    }

    original_stored = repository.get_by_request_id(original["id_solicitud"])

    assert original_stored is not None
    assert original_stored["estado"] == "REGISTERED"
    assert original_stored["numero_siniestro"] == "SIN-TEST-018"

    core_client.get_policy.assert_not_called()
    core_client.create_claim.assert_not_called()


def test_r8_rejection_is_persisted_and_replayed_without_core_call(tmp_path):
    """An R8 rejection must be durable and idempotent."""
    database_path = tmp_path / "claims.db"

    with sqlite3.connect(database_path) as connection:
        connection.executescript(MIGRATION.read_text(encoding="utf-8"))

    repository = SQLiteClaimsRepository(database_path)

    original = {
        "id_solicitud": "SOL-TEST-005-019-A",
        "numero_poliza": "AV-VI-0100000",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "2123456789",
        },
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
        "fecha_radicacion": "2026-01-15T10:30:00",
    }

    duplicate = {
        **original,
        "id_solicitud": "SOL-TEST-005-019-B",
    }

    assert repository.reserve_claim(original) == "CREATED"

    repository.save_result(
        id_solicitud=original["id_solicitud"],
        estado="REGISTERED",
        motivos_rechazo=[],
        numero_siniestro="SIN-TEST-019",
    )

    core_client = Mock()

    service = ClaimsApplicationService(
        core_client=core_client,
        repository=repository,
        today_provider=lambda: date(2026, 2, 1),
    )

    first_result = service.submit_claim(duplicate)
    second_result = service.submit_claim(duplicate)

    assert first_result == second_result
    assert first_result["estado"] == "REJECTED"
    assert first_result["motivos_rechazo"] == ["R8"]

    stored = repository.get_by_request_id(duplicate["id_solicitud"])

    assert stored is not None
    assert stored["estado"] == "REJECTED"
    assert stored["motivos_rechazo"] == ["R8"]

    with sqlite3.connect(database_path) as connection:
        count = connection.execute(
            """
            SELECT COUNT(*)
            FROM reclamaciones
            WHERE id_solicitud = ?
            """,
            (duplicate["id_solicitud"],),
        ).fetchone()[0]

    assert count == 1

    core_client.get_policy.assert_not_called()
    core_client.create_claim.assert_not_called()


def test_pending_business_event_does_not_trigger_second_core_call(tmp_path):
    """An uncertain business event must not be submitted twice."""
    database_path = tmp_path / "claims.db"

    with sqlite3.connect(database_path) as connection:
        connection.executescript(MIGRATION.read_text(encoding="utf-8"))

    repository = SQLiteClaimsRepository(database_path)

    original = {
        "id_solicitud": "SOL-TEST-005-020-A",
        "numero_poliza": "AV-VI-0100000",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "2123456789",
        },
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
        "fecha_radicacion": "2026-01-15T10:30:00",
    }

    duplicate = {
        **original,
        "id_solicitud": "SOL-TEST-005-020-B",
    }

    assert repository.reserve_claim(original) == "CREATED"

    repository.save_result(
        id_solicitud=original["id_solicitud"],
        estado="PENDING_CONFIRMATION",
        motivos_rechazo=[],
        numero_siniestro=None,
    )

    core_client = Mock()

    service = ClaimsApplicationService(
        core_client=core_client,
        repository=repository,
        today_provider=lambda: date(2026, 2, 1),
    )

    result = service.submit_claim(duplicate)

    assert result["estado"] == "IN_PROGRESS"
    assert result["numero_siniestro"] is None

    with sqlite3.connect(database_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM reclamaciones").fetchone()[0]

    assert count == 1

    core_client.get_policy.assert_not_called()
    core_client.create_claim.assert_not_called()
