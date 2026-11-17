"""Tests for claim date validation rules."""

from datetime import date, timedelta

import pytest

from life_claims.domain.date_rules import validate_dates


@pytest.fixture
def valid_policy():
    return {
        "fecha_inicio": date(2020, 1, 1),
        "fecha_fin": date(2030, 12, 31),
        "estado": "ACTIVA",
        "fecha_cambio_estado": None,
    }


@pytest.mark.parametrize(
    "loss_date",
    [date(2025, 1, 1), date(2025, 12, 31)],
)
def test_r3_policy_validity_boundaries(valid_policy, loss_date):
    valid_policy["fecha_inicio"] = date(2025, 1, 1)
    valid_policy["fecha_fin"] = date(2025, 12, 31)

    result = validate_dates(
        policy=valid_policy,
        loss_date=loss_date,
        filing_date=date(2026, 1, 1),
        today=date(2026, 1, 1),
    )

    assert "R3" not in result


def test_r4_rejects_cancelled_policy_before_loss(valid_policy):
    valid_policy["estado"] = "CANCELADA"
    valid_policy["fecha_cambio_estado"] = date(2025, 1, 1)

    result = validate_dates(
        policy=valid_policy,
        loss_date=date(2025, 6, 1),
        filing_date=date(2025, 6, 2),
        today=date(2025, 6, 2),
    )

    assert "R4" in result


@pytest.mark.parametrize(
    ("elapsed_days", "expected_rejection"),
    [(730, False), (731, True)],
)
def test_r6_prescription_limit(valid_policy, elapsed_days, expected_rejection):
    loss_date = date(2024, 1, 1)
    filing_date = loss_date + timedelta(days=elapsed_days)

    result = validate_dates(
        policy=valid_policy,
        loss_date=loss_date,
        filing_date=filing_date,
        today=filing_date,
    )

    assert ("R6" in result) is expected_rejection


def test_r7_rejects_future_loss(valid_policy):
    result = validate_dates(
        policy=valid_policy,
        loss_date=date(2026, 1, 2),
        filing_date=date(2026, 1, 2),
        today=date(2026, 1, 1),
    )

    assert "R7" in result
@pytest.mark.parametrize(
    "loss_date",
    [date(2024, 12, 31), date(2026, 1, 1)],
)
def test_r3_rejects_loss_outside_policy_validity(valid_policy, loss_date):
    valid_policy["fecha_inicio"] = date(2025, 1, 1)
    valid_policy["fecha_fin"] = date(2025, 12, 31)

    result = validate_dates(
        policy=valid_policy,
        loss_date=loss_date,
        filing_date=date(2026, 1, 2),
        today=date(2026, 1, 2),
    )

    assert "R3" in result


@pytest.mark.parametrize("status", ["CANCELADA", "SUSPENDIDA"])
def test_r4_rejects_status_change_on_loss_date(valid_policy, status):
    valid_policy["estado"] = status
    valid_policy["fecha_cambio_estado"] = date(2025, 6, 1)

    result = validate_dates(
        policy=valid_policy,
        loss_date=date(2025, 6, 1),
        filing_date=date(2025, 6, 2),
        today=date(2025, 6, 2),
    )

    assert "R4" in result


def test_r4_allows_status_change_after_loss(valid_policy):
    valid_policy["estado"] = "CANCELADA"
    valid_policy["fecha_cambio_estado"] = date(2025, 6, 3)

    result = validate_dates(
        policy=valid_policy,
        loss_date=date(2025, 6, 1),
        filing_date=date(2025, 6, 2),
        today=date(2025, 6, 2),
    )

    assert "R4" not in result


def test_r7_rejects_loss_after_filing(valid_policy):
    result = validate_dates(
        policy=valid_policy,
        loss_date=date(2025, 6, 2),
        filing_date=date(2025, 6, 1),
        today=date(2025, 6, 3),
    )

    assert "R7" in result