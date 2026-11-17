"""Structured HTTP access logging without external dependencies."""

import json
import logging
import time
import uuid
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("life_claims.http")

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

logger.setLevel(logging.INFO)
logger.propagate = False


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Log HTTP requests as JSON without sensitive payloads."""

    async def dispatch(self, request, call_next):
        request_id = str(uuid.uuid4())
        started = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration_ms = round(
                (time.perf_counter() - started) * 1000,
                2,
            )

            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "INFO",
                "event": "http_request",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": duration_ms,
            }

            logger.info(json.dumps(event, ensure_ascii=False))
