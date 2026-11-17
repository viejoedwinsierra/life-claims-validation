"""OpenAPI contract tests for the claims HTTP API."""

from life_claims.api.main import app


def test_claims_endpoints_document_expected_http_responses():
    """OpenAPI must describe the implemented HTTP outcomes."""
    schema = app.openapi()
    paths = schema["paths"]

    post_responses = paths["/reclamaciones"]["post"]["responses"]
    get_responses = paths["/reclamaciones/{id_solicitud}"]["get"]["responses"]

    assert {"200", "201", "202", "409", "422", "503"} <= set(post_responses)

    assert {"200", "404", "422", "503"} <= set(get_responses)


def test_claims_request_schema_is_published():
    """The claim request must be represented in OpenAPI."""
    schema = app.openapi()

    assert "ClaimRequest" in schema["components"]["schemas"]
    assert "InsuredRequest" in schema["components"]["schemas"]
