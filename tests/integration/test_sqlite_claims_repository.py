"""Integration tests for SQLite claims persistence."""

import sqlite3
from pathlib import Path

from life_claims.infrastructure.sqlite_claims_repository import (
    SQLiteClaimsRepository,
)

MIGRATION = Path(__file__).resolve().parents[2] / "datos" / "migrations" / "001_create_claims.sql"


def test_reserve_claim_is_idempotent(tmp_path):
    """Repeated requests must not create duplicate records."""
    database_path = tmp_path / "claims.db"

    with sqlite3.connect(database_path) as connection:
        connection.executescript(MIGRATION.read_text(encoding="utf-8"))

    repository = SQLiteClaimsRepository(database_path)

    claim = {
        "id_solicitud": "SOL-TEST-005-004",
        "canal": "WEB",
        "numero_poliza": "AV-VI-0100000",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "2123456789",
        },
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
        "fecha_radicacion": "2026-01-15T10:30:00",
    }

    first = repository.reserve_claim(claim)
    second = repository.reserve_claim(claim)

    assert first == "CREATED"
    assert second == "ALREADY_EXISTS"

    with sqlite3.connect(database_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM reclamaciones").fetchone()[0]

    assert count == 1


def test_reserve_claim_detects_payload_conflict(tmp_path):
    """The same request ID with different content must conflict."""
    database_path = tmp_path / "claims.db"

    with sqlite3.connect(database_path) as connection:
        connection.executescript(MIGRATION.read_text(encoding="utf-8"))

    repository = SQLiteClaimsRepository(database_path)

    original = {
        "id_solicitud": "SOL-TEST-005-005",
        "numero_poliza": "AV-VI-0100000",
        "tipo_reclamacion": "MUERTE",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "2123456789",
        },
        "fecha_siniestro": "2026-01-01",
    }

    modified = {
        **original,
        "tipo_reclamacion": "ITP",
    }

    first = repository.reserve_claim(original)
    second = repository.reserve_claim(modified)

    assert first == "CREATED"
    assert second == "PAYLOAD_CONFLICT"

    with sqlite3.connect(database_path) as connection:
        stored_payload = connection.execute(
            """
            SELECT payload_json
            FROM reclamaciones
            WHERE id_solicitud = ?
            """,
            ("SOL-TEST-005-005",),
        ).fetchone()[0]

    import json

    assert json.loads(stored_payload) == original


def test_concurrent_reservations_create_only_one_claim(tmp_path):
    """Concurrent reservations must preserve request uniqueness."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    database_path = tmp_path / "claims.db"

    with sqlite3.connect(database_path) as connection:
        connection.executescript(MIGRATION.read_text(encoding="utf-8"))

    claim = {
        "id_solicitud": "SOL-TEST-005-006",
        "numero_poliza": "AV-VI-0100000",
        "tipo_reclamacion": "MUERTE",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "2123456789",
        },
        "fecha_siniestro": "2026-01-01",
    }

    barrier = Barrier(2)

    def reserve():
        repository = SQLiteClaimsRepository(database_path)
        barrier.wait(timeout=10)
        return repository.reserve_claim(claim)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(reserve) for _ in range(2)]
        results = [future.result(timeout=15) for future in futures]

    assert sorted(results) == ["ALREADY_EXISTS", "CREATED"]

    with sqlite3.connect(database_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM reclamaciones").fetchone()[0]

    assert count == 1


def test_save_and_retrieve_rejected_claim(tmp_path):
    """A rejected claim must remain available after reconnecting."""
    database_path = tmp_path / "claims.db"

    with sqlite3.connect(database_path) as connection:
        connection.executescript(MIGRATION.read_text(encoding="utf-8"))

    claim = {
        "id_solicitud": "SOL-TEST-005-007",
        "numero_poliza": "AV-VI-0100000",
        "tipo_reclamacion": "MUERTE",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "2123456789",
        },
        "fecha_siniestro": "2026-01-01",
    }

    repository = SQLiteClaimsRepository(database_path)

    assert repository.reserve_claim(claim) == "CREATED"

    repository.save_result(
        id_solicitud=claim["id_solicitud"],
        estado="REJECTED",
        motivos_rechazo=["R2", "R5"],
        numero_siniestro=None,
    )

    reconnected_repository = SQLiteClaimsRepository(database_path)

    result = reconnected_repository.get_by_request_id(claim["id_solicitud"])

    assert result is not None
    assert result["id_solicitud"] == claim["id_solicitud"]
    assert result["estado"] == "REJECTED"
    assert result["motivos_rechazo"] == ["R2", "R5"]
    assert result["numero_siniestro"] is None


def test_registered_claim_persists_core_number(tmp_path):
    """A registered claim must retain its core claim number."""
    database_path = tmp_path / "claims.db"

    with sqlite3.connect(database_path) as connection:
        connection.executescript(MIGRATION.read_text(encoding="utf-8"))

    claim = {
        "id_solicitud": "SOL-TEST-005-008",
        "numero_poliza": "AV-VI-0100000",
        "tipo_reclamacion": "MUERTE",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "2123456789",
        },
        "fecha_siniestro": "2026-01-01",
    }

    repository = SQLiteClaimsRepository(database_path)
    assert repository.reserve_claim(claim) == "CREATED"

    repository.save_result(
        id_solicitud=claim["id_solicitud"],
        estado="REGISTERED",
        motivos_rechazo=[],
        numero_siniestro="SIN-TEST-008",
    )

    reconnected = SQLiteClaimsRepository(database_path)
    result = reconnected.get_by_request_id(claim["id_solicitud"])

    assert result is not None
    assert result["estado"] == "REGISTERED"
    assert result["numero_siniestro"] == "SIN-TEST-008"
    assert result["motivos_rechazo"] == []


def test_finalized_claim_cannot_be_overwritten(tmp_path):
    """A finalized claim must not accept another result."""
    import pytest

    database_path = tmp_path / "claims.db"

    with sqlite3.connect(database_path) as connection:
        connection.executescript(MIGRATION.read_text(encoding="utf-8"))

    claim = {
        "id_solicitud": "SOL-TEST-005-009",
        "numero_poliza": "AV-VI-0100000",
        "tipo_reclamacion": "MUERTE",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "2123456789",
        },
        "fecha_siniestro": "2026-01-01",
    }

    repository = SQLiteClaimsRepository(database_path)
    assert repository.reserve_claim(claim) == "CREATED"

    repository.save_result(
        id_solicitud=claim["id_solicitud"],
        estado="REGISTERED",
        motivos_rechazo=[],
        numero_siniestro="SIN-TEST-009",
    )

    with pytest.raises(ValueError):
        repository.save_result(
            id_solicitud=claim["id_solicitud"],
            estado="REJECTED",
            motivos_rechazo=["R2"],
            numero_siniestro=None,
        )

    result = repository.get_by_request_id(claim["id_solicitud"])

    assert result is not None
    assert result["estado"] == "REGISTERED"
    assert result["numero_siniestro"] == "SIN-TEST-009"


def test_get_existing_claims_returns_registered_claims(tmp_path):
    """R8 lookup must return previously registered claims."""
    database_path = tmp_path / "claims.db"

    with sqlite3.connect(database_path) as connection:
        connection.executescript(MIGRATION.read_text(encoding="utf-8"))

    claim = {
        "id_solicitud": "SOL-TEST-005-010",
        "numero_poliza": "AV-VI-0100000",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "2123456789",
        },
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
    }

    repository = SQLiteClaimsRepository(database_path)

    assert repository.reserve_claim(claim) == "CREATED"

    repository.save_result(
        id_solicitud=claim["id_solicitud"],
        estado="REGISTERED",
        motivos_rechazo=[],
        numero_siniestro="SIN-TEST-010",
    )

    existing = repository.get_existing_claims(claim["numero_poliza"])

    assert len(existing) == 1
    assert existing[0] == claim


def test_get_existing_claims_excludes_rejected_and_other_policies(tmp_path):
    """R8 lookup must return only registered claims for the given policy."""
    database_path = tmp_path / "claims.db"

    with sqlite3.connect(database_path) as connection:
        connection.executescript(MIGRATION.read_text(encoding="utf-8"))

    repository = SQLiteClaimsRepository(database_path)

    cases = [
        ("SOL-010-A", "AV-VI-0100000", "REGISTERED"),
        ("SOL-010-B", "AV-VI-0100000", "REJECTED"),
        ("SOL-010-C", "AV-VI-0200000", "REGISTERED"),
    ]

    for request_id, policy_number, state in cases:
        claim = {
            "id_solicitud": request_id,
            "numero_poliza": policy_number,
            "asegurado": {
                "tipo_documento": "CC",
                "numero_documento": "2123456789",
            },
            "tipo_reclamacion": "MUERTE",
            "fecha_siniestro": ("2026-01-02" if request_id == "SOL-010-B" else "2026-01-01"),
        }

        assert repository.reserve_claim(claim) == "CREATED"

        repository.save_result(
            id_solicitud=request_id,
            estado=state,
            motivos_rechazo=["R2"] if state == "REJECTED" else [],
            numero_siniestro=(f"SIN-{request_id}" if state == "REGISTERED" else None),
        )

    existing = repository.get_existing_claims("AV-VI-0100000")

    assert len(existing) == 1
    assert existing[0]["id_solicitud"] == "SOL-010-A"


def test_same_business_event_with_different_request_ids_cannot_be_reserved(
    tmp_path,
):
    """R8 must prevent reserving the same business event twice."""
    database_path = tmp_path / "claims.db"

    with sqlite3.connect(database_path) as connection:
        connection.executescript(MIGRATION.read_text(encoding="utf-8"))

    repository = SQLiteClaimsRepository(database_path)

    first_claim = {
        "id_solicitud": "SOL-TEST-005-016-A",
        "numero_poliza": "AV-VI-0100000",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "2123456789",
        },
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
    }

    second_claim = {
        **first_claim,
        "id_solicitud": "SOL-TEST-005-016-B",
    }

    assert repository.reserve_claim(first_claim) == "CREATED"

    assert repository.reserve_claim(second_claim) == "BUSINESS_DUPLICATE"


def test_rejected_claim_releases_business_event_reservation(tmp_path):
    """A rejected request must not block a later claim for the same event."""
    database_path = tmp_path / "claims.db"

    with sqlite3.connect(database_path) as connection:
        connection.executescript(MIGRATION.read_text(encoding="utf-8"))

    repository = SQLiteClaimsRepository(database_path)

    original = {
        "id_solicitud": "SOL-TEST-005-017-A",
        "numero_poliza": "AV-VI-0100000",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "2123456789",
        },
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
    }

    replacement = {
        **original,
        "id_solicitud": "SOL-TEST-005-017-B",
    }

    assert repository.reserve_claim(original) == "CREATED"

    repository.save_result(
        id_solicitud=original["id_solicitud"],
        estado="REJECTED",
        motivos_rechazo=["R2"],
        numero_siniestro=None,
    )

    assert repository.reserve_claim(replacement) == "CREATED"

    assert repository.get_by_request_id(original["id_solicitud"])["estado"] == "REJECTED"
