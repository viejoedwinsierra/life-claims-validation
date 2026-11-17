"""Tests for the HTTP claim request contract."""

import pytest
from pydantic import ValidationError

from life_claims.api.schemas import ClaimRequest


def valid_claim():
    return {
        "id_solicitud": "SOL-00231",
        "canal": "CORREDOR",
        "numero_poliza": "AV-VI-0100791",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "2310351885",
        },
        "tipo_reclamacion": "ITP",
        "fecha_siniestro": "2014-11-08",
        "fecha_radicacion": "2014-11-23T11:02:17",
        "reclamante": {},
        "descripcion": "Reclamacion de prueba",
        "documentos_adjuntos": [],
    }


def test_valid_claim_preserves_domain_input():
    payload = valid_claim()

    claim = ClaimRequest.model_validate(payload)

    assert claim.model_dump(mode="json") == payload


@pytest.mark.parametrize(
    "missing_field",
    [
        "id_solicitud",
        "numero_poliza",
        "asegurado",
        "tipo_reclamacion",
        "fecha_siniestro",
        "fecha_radicacion",
    ],
)
def test_required_fields_are_enforced(missing_field):
    payload = valid_claim()
    payload.pop(missing_field)

    with pytest.raises(ValidationError):
        ClaimRequest.model_validate(payload)


def test_insured_document_is_required():
    payload = valid_claim()
    payload["asegurado"].pop("numero_documento")

    with pytest.raises(ValidationError):
        ClaimRequest.model_validate(payload)


def test_invalid_loss_date_is_rejected():
    payload = valid_claim()
    payload["fecha_siniestro"] = "2014-99-99"

    with pytest.raises(ValidationError):
        ClaimRequest.model_validate(payload)
