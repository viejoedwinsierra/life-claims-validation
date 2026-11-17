"""Configuration factory for the insurance core HTTP client."""

import os

import httpx


def create_core_http_client() -> httpx.Client:
    """Create an HTTP client with explicit connection timeouts."""
    base_url = os.environ.get(
        "CORE_BASE_URL",
        "http://localhost:8081",
    )

    timeout = httpx.Timeout(
        connect=3.0,
        read=5.0,
        write=3.0,
        pool=3.0,
    )

    return httpx.Client(
        base_url=base_url,
        timeout=timeout,
    )
