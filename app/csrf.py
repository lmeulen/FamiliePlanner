"""CSRF protection middleware using the synchronizer token pattern.

A per-session token is stored in the Starlette session and must be echoed:
- As the ``X-CSRF-Token`` request header for AJAX/API calls.

The token is exposed to templates via ``request.state.csrf_token``.

Note: The /login endpoint is exempt from CSRF checks since there's no session yet
at first login. Session is created after successful authentication.

Set ``AUTH_DISABLED=1`` in the environment to skip CSRF checks (tests only).
"""

import os
import secrets

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

_SESSION_KEY = "csrf_token"
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_CSRF_EXEMPT_PATHS = frozenset({"/login"})  # Login has no session yet, exempt from CSRF
# TEST bypass
_TEST_DISABLED = os.environ.get("AUTH_DISABLED", "").lower() in ("1", "true", "yes")


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if _TEST_DISABLED:
            request.state.csrf_token = "test-csrf-token"
            return await call_next(request)

        # Ensure a token exists in the session for every visitor
        if _SESSION_KEY not in request.session:
            request.session[_SESSION_KEY] = secrets.token_hex(32)

        token: str = request.session[_SESSION_KEY]

        # Skip CSRF check for exempt paths (like /login which has no session yet)
        if request.method not in _SAFE_METHODS and request.url.path not in _CSRF_EXEMPT_PATHS:
            # API calls send the token as a header (body is not consumed)
            submitted = request.headers.get("X-CSRF-Token", "")
            if not secrets.compare_digest(submitted, token):
                return JSONResponse({"detail": "CSRF token ongeldig"}, status_code=403)

        # Make token available in templates via {{ request.state.csrf_token }}
        request.state.csrf_token = token
        return await call_next(request)
