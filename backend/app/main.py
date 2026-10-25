"""HVA API application factory."""

from __future__ import annotations

import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_router
from app.core.config import settings
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging, log_event
from app.core.middleware import SecurityMiddleware

configure_logging(settings.log_level)

DESCRIPTION = """
Human Vernacular Assist (HVA) API.

Independent assistance platform for discovering Indian government schemes. This API
does not submit applications, certify identity or grant benefits. Endpoints are
versioned under /api/v1; the OpenAPI document is generated at /api/v1/openapi.json.

Authentication uses an HttpOnly session cookie plus a double-submit CSRF header.
Mutation requests must send `X-CSRF-Token` equal to the `hva_csrf` cookie.
"""

app = FastAPI(
    title="Human Vernacular Assist API",
    version="1.0.0",
    description=DESCRIPTION,
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/v1/openapi.json",
)

app.add_middleware(SecurityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "X-Request-Id"],
    expose_headers=["X-Request-Id", "Retry-After"],
    max_age=600,
)
install_error_handlers(app)


@app.middleware("http")
async def request_timing(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    log_event(
        "http_request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round((time.perf_counter() - start) * 1000, 1),
    )
    return response


app.include_router(api_router)


@app.get("/", include_in_schema=False)
def root() -> JSONResponse:
    return JSONResponse(
        {
            "service": "Human Vernacular Assist API",
            "version": "1.0.0",
            "docs": "/api/docs",
            "openapi": "/api/v1/openapi.json",
            "health": "/api/v1/health",
            "notice": "Independent assistance platform. Not a government service.",
        }
    )
