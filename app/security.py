"""Security headers middleware and configuration."""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import ENVIRONMENT


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # Content Security Policy
        # - default-src 'self': Only allow resources from same origin by default
        # - script-src 'self' 'unsafe-inline': Allow inline scripts (needed for vanilla JS)
        # - style-src 'self' 'unsafe-inline': Allow inline styles (needed for dynamic styling)
        # - img-src 'self' data: https:: Allow images from same origin, data URIs, and HTTPS
        # - font-src 'self': Only allow fonts from same origin
        # - connect-src 'self': Only allow fetch/XHR to same origin
        # - frame-ancestors 'none': Prevent embedding in iframes (clickjacking protection)
        # - base-uri 'self': Restrict <base> tag URLs
        # - form-action 'self': Only allow form submissions to same origin
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

        # X-Frame-Options: Prevent clickjacking attacks
        # DENY prevents the page from being embedded in any frame/iframe
        response.headers["X-Frame-Options"] = "DENY"

        # X-Content-Type-Options: Prevent MIME sniffing
        # nosniff tells browsers to respect the Content-Type header
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-XSS-Protection: Enable XSS filter in older browsers
        # Modern browsers use CSP, but this helps legacy browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer-Policy: Control referrer information
        # strict-origin-when-cross-origin sends full URL for same-origin, origin only for cross-origin
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy: Disable unnecessary browser features
        # Disable geolocation, microphone, camera, payment, and USB APIs
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=(), payment=(), usb=()"

        # Strict-Transport-Security: Force HTTPS (only in production with HTTPS)
        # max-age=31536000: Remember for 1 year
        # includeSubDomains: Apply to all subdomains
        if request.url.scheme == "https" and ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
