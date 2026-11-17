"""HTTP client for the simulated insurance core."""

from typing import Any

import httpx


class CoreClient:
    """Access the insurance core through an injected HTTP client."""

    def __init__(self, http_client: httpx.Client) -> None:
        self._http_client = http_client

    def get_policy(self, policy_number: str) -> dict[str, Any] | None:
        """Retrieve a policy, returning None only for HTTP 404."""
        response = self._http_client.get(
            f"/api/v1/polizas/{policy_number}"
        )

        if response.status_code == 404:
            return None

        response.raise_for_status()

        policy = response.json()

        if not isinstance(policy, dict):
            raise ValueError("Invalid core policy response")

        return policy

    def create_claim(
        self,
        payload: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Register a claim in the core with an idempotency key."""
        response = self._http_client.post(
            "/api/v1/siniestros",
            json=payload,
            headers={"Idempotency-Key": idempotency_key},
        )

        response.raise_for_status()

        result = response.json()

        if not isinstance(result, dict):
            raise ValueError("Invalid core claim response")

        return result
