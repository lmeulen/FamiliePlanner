"""Authentication middleware and login/logout route handlers."""

import os
import secrets

from fastapi import Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import APP_PASSWORD, APP_USERNAME, AUTH_REQUIRED, BASE_DIR, verify_password

# Paths that are accessible without authentication
_PUBLIC_PATHS = frozenset({"/login", "/logout", "/health"})

# Legacy test bypass
_TEST_DISABLED = os.environ.get("AUTH_DISABLED", "").lower() in ("1", "true", "yes")

# Runtime-mutable auth flag (seeded from .env on startup, then controlled via settings API)
_auth_required: bool = AUTH_REQUIRED


def get_auth_required() -> bool:
    return _auth_required and not _TEST_DISABLED


def set_auth_required(value: bool) -> None:
    global _auth_required
    _auth_required = value
    logger.info("auth.auth_required changed to {}", value)


templates = Jinja2Templates(directory=BASE_DIR / "app" / "templates")


class AuthMiddleware(BaseHTTPMiddleware):
    """Session-based authentication middleware."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if not get_auth_required():
            return await call_next(request)

        # Always allow static files and login/logout
        if path in _PUBLIC_PATHS or path.startswith("/static"):
            return await call_next(request)

        if not request.session.get("authenticated"):
            if path.startswith("/api/"):
                return JSONResponse({"detail": "Niet ingelogd"}, status_code=401)
            return RedirectResponse(url="/login", status_code=302)

        return await call_next(request)


# ── Login / logout route handlers ────────────────────────────────


async def login_get(request: Request) -> HTMLResponse | RedirectResponse:
    """Show the login form.  Redirect to dashboard if already logged in."""
    if request.session.get("authenticated"):
        return RedirectResponse(url="/", status_code=302)
    error = request.query_params.get("error")
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
) -> RedirectResponse:
    """Validate credentials and create session."""
    user_ok = secrets.compare_digest(username.encode(), APP_USERNAME.encode())
    pass_ok = verify_password(password, APP_PASSWORD)
    if user_ok and pass_ok:
        request.session["authenticated"] = True
        logger.info("auth.login.success user='{}'", username)
        next_url = request.query_params.get("next", "/")
        return RedirectResponse(url=next_url, status_code=302)
    logger.warning("auth.login.failed user='{}'", username)
    return RedirectResponse(url="/login?error=1", status_code=302)


async def logout(request: Request) -> RedirectResponse:
    """Clear the session and redirect to login."""
    request.session.clear()
    logger.info("auth.logout")
    return RedirectResponse(url="/login", status_code=302)
