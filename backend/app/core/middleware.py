"""Request-scoped middleware: request id, size limit, Origin and CSRF checks, headers."""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.errors import error_body
from app.core.logging import log_event, request_id_ctx
from app.core.security import constant_time_compare

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        token = request_id_ctx.set(request_id)
        try:
            origin_response = self._check_origin(request)
            if origin_response is not None:
                return self._finish(origin_response, request_id)

            length = request.headers.get("content-length")
            if length and length.isdigit() and int(length) > settings.max_request_bytes:
                return self._finish(
                    JSONResponse(
                        status_code=413,
                        content=error_body("payload_too_large", "Request body is too large."),
                    ),
                    request_id,
                )

            if request.method in UNSAFE_METHODS and request.url.path.startswith("/api/"):
                csrf_response = self._check_csrf(request)
                if csrf_response is not None:
                    return self._finish(csrf_response, request_id)

            response = await call_next(request)
            return self._finish(response, request_id)
        finally:
            request_id_ctx.reset(token)

    @staticmethod
    def _finish(response: Response, request_id: str) -> Response:
        """Apply security headers to every response, including early rejections."""
        response.headers["X-Request-Id"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(self), camera=()"
        response.headers["Cross-Origin-Resource-Policy"] = "same-site"
        if settings.env == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    def _check_origin(self, request: Request) -> Response | None:
        if request.method not in UNSAFE_METHODS:
            return None
        origin = request.headers.get("origin")
        referer = request.headers.get("referer")
        candidate = origin
        if not candidate and referer:
            candidate = str(request.url.replace(path="", query="")) if referer.startswith(str(request.base_url)) else referer
        if not candidate:
            return None
        allowed = {item.rstrip("/") for item in settings.cors_origins}
        allowed.add(settings.app_base_url.rstrip("/"))
        allowed.add(settings.api_base_url.rstrip("/"))
        if candidate.rstrip("/") not in allowed:
            log_event("origin_rejected")
            return JSONResponse(
                status_code=403,
                content=error_body("cross_origin_denied", "Request origin is not allowed."),
            )
        return None

    def _check_csrf(self, request: Request) -> Response | None:
        cookie = request.cookies.get(settings.csrf_cookie_name)
        header = request.headers.get("x-csrf-token")
        if not cookie or not header or not constant_time_compare(cookie, header):
            return JSONResponse(
                status_code=403,
                content=error_body(
                    "csrf_failed",
                    "Missing or invalid CSRF token. Reload the page and try again.",
                ),
            )
        return None
