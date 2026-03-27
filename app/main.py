"""
FamiliePlanner – FastAPI application entry point.
Mounts static files, registers routers, serves Jinja2 templates.
"""

import asyncio
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from app.auth import AuthMiddleware, login_get, login_post, logout
from app.backup_scheduler import run_nightly_backup_scheduler
from app.config import APP_TITLE, APP_VERSION, SECRET_KEY
from app.csrf import CSRFMiddleware
from app.database import AsyncSessionLocal, init_db
from app.errors import ErrorCode, ErrorResponse, get_error_message, translate_validation_error
from app.logging_config import setup_logging
from app.metrics import PrometheusMiddleware, db_connections
from app.routers import agenda, family, grocery, meals, photos, recipes, search, stats, tasks
from app.routers import settings as settings_router
from app.security import SecurityHeadersMiddleware

BASE_DIR = Path(__file__).resolve().parent

# Initialise logging before anything else
setup_logging()


# ── Custom StaticFiles with cache headers ─────────────────────────
class CachedStaticFiles(StaticFiles):
    """StaticFiles with Cache-Control headers for browser caching."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)

        # Add cache headers based on file type
        if path.startswith("uploads/thumbnails/"):
            # Thumbnails: cache for 1 year (immutable filenames)
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif path.startswith("uploads/"):
            # Original photos: cache for 1 day
            response.headers["Cache-Control"] = "public, max-age=86400"
        elif path.endswith((".css", ".js")):
            # CSS/JS: cache for 1 hour (we use ?v= query param for busting)
            response.headers["Cache-Control"] = "public, max-age=3600"
        elif path.endswith((".png", ".jpg", ".jpeg", ".svg", ".ico", ".woff", ".woff2")):
            # Images and fonts: cache for 1 week
            response.headers["Cache-Control"] = "public, max-age=604800"
        else:
            # Other static files: cache for 1 hour
            response.headers["Cache-Control"] = "public, max-age=3600"

        return response


# ── Rate limiter ──────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=[])


def rate_limit_exceeded_handler(request: Request, exc: Exception) -> Response:
    return _rate_limit_exceeded_handler(request, cast(RateLimitExceeded, exc))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting {} v{}", APP_TITLE, APP_VERSION)
    await init_db()
    logger.info("Database ready")
    backup_stop_event = asyncio.Event()
    backup_task = asyncio.create_task(run_nightly_backup_scheduler(backup_stop_event))
    # Load persisted auth_required setting from DB
    from app.auth import set_auth_required
    from app.database import AsyncSessionLocal
    from app.models.settings import AppSetting

    async with AsyncSessionLocal() as db:
        row = await db.get(AppSetting, "auth_required")
        if row is not None:
            set_auth_required(row.value.lower() in ("1", "true"))
    try:
        yield
    finally:
        backup_stop_event.set()
        await backup_task
        logger.info("Shutting down {}", APP_TITLE)


app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# ── Middleware (outermost last = SessionMiddleware runs first) ────
# Execution order: SessionMiddleware → SecurityHeadersMiddleware → CSRFMiddleware → AuthMiddleware → PrometheusMiddleware → SlowAPI → routes
app.add_middleware(AuthMiddleware)
app.add_middleware(PrometheusMiddleware)
app.add_middleware(CSRFMiddleware)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, https_only=False)


# ── Exception Handlers ───────────────────────────────────────────


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors with user-friendly Dutch messages."""
    errors = exc.errors()
    logger.warning("Validation error on {} {}: {}", request.method, request.url.path, errors)

    # Get first error for primary message
    first_error = errors[0] if errors else {}
    error_type = first_error.get("type", "value_error")
    ctx = first_error.get("ctx")
    field = ".".join(str(loc) for loc in first_error.get("loc", [])) if first_error.get("loc") else None

    # Translate to Dutch
    details = translate_validation_error(error_type, ctx)

    error_response = ErrorResponse(
        code=ErrorCode.VALIDATION_ERROR,
        message=get_error_message(ErrorCode.VALIDATION_ERROR),
        details=details,
        field=field,
    )

    return JSONResponse(
        status_code=422,
        content=error_response.model_dump(exclude_none=True),
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Handle database integrity errors (foreign key, unique constraints)."""
    msg = str(exc.orig).lower()

    if "foreign key" in msg:
        code = ErrorCode.FOREIGN_KEY_ERROR
    elif "unique" in msg or "not unique" in msg:
        code = ErrorCode.UNIQUE_CONSTRAINT
    else:
        code = ErrorCode.DATABASE_ERROR

    logger.warning("IntegrityError on {} {}: {}", request.method, request.url.path, exc.orig)

    error_response = ErrorResponse(
        code=code,
        message=get_error_message(code),
    )

    return JSONResponse(
        status_code=422,
        content=error_response.model_dump(exclude_none=True),
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    """Handle generic database errors."""
    logger.error("SQLAlchemyError on {} {}: {}", request.method, request.url.path, exc)

    error_response = ErrorResponse(
        code=ErrorCode.DATABASE_ERROR,
        message=get_error_message(ErrorCode.DATABASE_ERROR),
    )

    return JSONResponse(
        status_code=500,
        content=error_response.model_dump(exclude_none=True),
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions (404, 403, etc.) with user-friendly messages."""
    # Map status codes to error codes
    code_map = {
        404: ErrorCode.NOT_FOUND,
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        409: ErrorCode.CONFLICT,
        429: ErrorCode.RATE_LIMIT,
    }

    code = code_map.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
    message = get_error_message(code)

    # For 404 on HTML pages, return HTML error page
    if exc.status_code == 404 and "text/html" in request.headers.get("accept", ""):
        return templates.TemplateResponse(
            request,
            "error.html",
            {
                "request": request,
                "error_code": 404,
                "title": "Pagina niet gevonden",
                "message": "De pagina die je zoekt bestaat niet of is verplaatst.",
                "suggestion": "Ga terug naar het overzicht of gebruik het menu.",
            },
            status_code=404,
        )

    logger.warning("{} error on {} {}: {}", exc.status_code, request.method, request.url.path, exc.detail)

    error_response = ErrorResponse(
        code=code,
        message=message,
        details=str(exc.detail) if exc.detail else None,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(exclude_none=True),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for unexpected exceptions."""
    logger.exception("Unhandled exception on {} {}: {}", request.method, request.url.path, exc)

    # Return 500 HTML page for browser requests
    if "text/html" in request.headers.get("accept", ""):
        return templates.TemplateResponse(
            request,
            "error.html",
            {
                "request": request,
                "error_code": 500,
                "title": "Er is iets misgegaan",
                "message": "Er is een onverwachte fout opgetreden.",
                "suggestion": "Probeer de pagina te vernieuwen. Als het probleem blijft, neem contact op.",
            },
            status_code=500,
        )

    error_response = ErrorResponse(
        code=ErrorCode.INTERNAL_ERROR,
        message=get_error_message(ErrorCode.INTERNAL_ERROR),
    )

    return JSONResponse(
        status_code=500,
        content=error_response.model_dump(exclude_none=True),
    )


# ── Request logging middleware ────────────────────────────────────


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "{method} {path} → {status} ({duration:.1f}ms)",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration=duration_ms,
    )
    return response


# ── Health check ─────────────────────────────────────────────────


@app.get("/health", tags=["health"], include_in_schema=True)
async def health():
    """Liveness + readiness probe. Returns 200 when the DB is reachable."""
    db_ok = False
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_ok = True
    except Exception as exc:  # noqa: BLE001
        logger.error("health check: DB unreachable – {}", exc)

    status = "ok" if db_ok else "degraded"
    payload = {
        "status": status,
        "version": APP_VERSION,
        "database": "ok" if db_ok else "error",
    }
    return JSONResponse(payload, status_code=200 if db_ok else 503)


@app.get("/metrics", tags=["monitoring"], include_in_schema=False)
async def metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text format. Not protected by authentication
    to allow monitoring systems to scrape metrics.
    """
    # Update database connection gauge
    try:
        async with AsyncSessionLocal() as db:
            # SQLite uses single connection, just verify it's reachable
            await db.execute(text("SELECT 1"))
            db_connections.set(1)
    except Exception:  # noqa: BLE001
        db_connections.set(0)

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/csp-report", tags=["security"], include_in_schema=False)
async def csp_violation_report(request: Request):
    """
    Content-Security-Policy violation reporting endpoint.

    Logs CSP violations reported by browsers. This helps identify resources
    that are blocked by the CSP policy during development and production.
    """
    try:
        violation = await request.json()
        csp_report = violation.get("csp-report", {})

        logger.warning(
            "CSP Violation: {} blocked {} from {}",
            csp_report.get("violated-directive", "unknown"),
            csp_report.get("blocked-uri", "unknown"),
            csp_report.get("document-uri", "unknown"),
        )
    except Exception:  # noqa: BLE001
        # Don't break on invalid reports
        pass

    return {"status": "reported"}


# Static files (with cache headers)
app.mount("/static", CachedStaticFiles(directory=BASE_DIR / "static"), name="static")

# Templates
templates = Jinja2Templates(directory=BASE_DIR / "templates")
templates.env.globals["static_v"] = str(int(time.time()))

# API routers
app.include_router(family.router)
app.include_router(agenda.router)
app.include_router(tasks.router)
app.include_router(meals.router)
app.include_router(photos.router)
app.include_router(settings_router.router)
app.include_router(search.router)
app.include_router(stats.router)
app.include_router(grocery.router)
app.include_router(recipes.router)

# Auth routes – login POST is rate-limited to 5 attempts per minute per IP
app.get("/login", response_class=HTMLResponse, response_model=None)(login_get)
app.post("/login")(limiter.limit("5/minute")(login_post))
app.get("/logout")(logout)

# ────────────────────────────────────────────────
# Page routes – each renders a Jinja2 template
# ────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html", {"request": request})


@app.get("/agenda", response_class=HTMLResponse)
async def page_agenda(request: Request):
    return templates.TemplateResponse(request, "agenda.html", {"request": request})


@app.get("/taken", response_class=HTMLResponse)
async def page_tasks(request: Request):
    return templates.TemplateResponse(request, "tasks.html", {"request": request})


@app.get("/maaltijden", response_class=HTMLResponse)
async def page_meals(request: Request):
    return templates.TemplateResponse(request, "meals.html", {"request": request})


@app.get("/boodschappen", response_class=HTMLResponse)
async def page_grocery(request: Request):
    return templates.TemplateResponse(request, "grocery.html", {"request": request})


@app.get("/recepten", response_class=HTMLResponse)
async def page_recipes(request: Request):
    return templates.TemplateResponse(request, "recipes.html", {"request": request})


@app.get("/instellingen", response_class=HTMLResponse)
async def page_settings(request: Request):
    return templates.TemplateResponse(request, "settings.html", {"request": request})


@app.get("/fotos", response_class=HTMLResponse)
async def page_photos(request: Request):
    return templates.TemplateResponse(request, "photos.html", {"request": request})


@app.get("/gezin", response_class=HTMLResponse)
async def page_family(request: Request):
    return templates.TemplateResponse(request, "family.html", {"request": request})


@app.get("/zoeken", response_class=HTMLResponse)
async def page_search(request: Request):
    return templates.TemplateResponse(request, "search.html", {"request": request})


@app.get("/statistieken", response_class=HTMLResponse)
async def page_stats(request: Request):
    return templates.TemplateResponse(request, "stats.html", {"request": request})
