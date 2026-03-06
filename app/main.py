"""
FamiliePlanner – FastAPI application entry point.
Mounts static files, registers routers, serves Jinja2 templates.
"""

import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.middleware.sessions import SessionMiddleware

from app.auth import AuthMiddleware, login_get, login_post, logout
from app.config import APP_TITLE, APP_VERSION, SECRET_KEY
from app.csrf import CSRFMiddleware
from app.database import AsyncSessionLocal, init_db
from app.logging_config import setup_logging
from app.routers import agenda, family, meals, photos, tasks
from app.routers import settings as settings_router

BASE_DIR = Path(__file__).resolve().parent

# Initialise logging before anything else
setup_logging()

# ── Rate limiter ──────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=[])


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting {} v{}", APP_TITLE, APP_VERSION)
    await init_db()
    logger.info("Database ready")
    # Load persisted auth_required setting from DB
    from app.auth import set_auth_required
    from app.database import AsyncSessionLocal
    from app.models.settings import AppSetting

    async with AsyncSessionLocal() as db:
        row = await db.get(AppSetting, "auth_required")
        if row is not None:
            set_auth_required(row.value.lower() in ("1", "true"))
    yield
    logger.info("Shutting down {}", APP_TITLE)


app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# ── Middleware (outermost last = SessionMiddleware runs first) ────
# Execution order: SessionMiddleware → CSRFMiddleware → AuthMiddleware → SlowAPI → routes
app.add_middleware(AuthMiddleware)
app.add_middleware(CSRFMiddleware)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, https_only=False)


# ── Database exception handlers ───────────────────────────────────


def _integrity_message(exc: IntegrityError) -> str:
    msg = str(exc.orig).lower()
    if "foreign key" in msg:
        return "Referenced resource does not exist (invalid id)."
    if "unique" in msg or "not unique" in msg:
        return "A record with this value already exists."
    return "Database integrity error."


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    detail = _integrity_message(exc)
    logger.warning("IntegrityError on {} {}: {}", request.method, request.url.path, exc.orig)
    return JSONResponse(status_code=422, content={"detail": detail})


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    logger.error("SQLAlchemyError on {} {}: {}", request.method, request.url.path, exc)
    return JSONResponse(status_code=400, content={"detail": "Database error. Please try again."})


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


# Static files
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

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

# Auth routes – login POST is rate-limited to 5 attempts per minute per IP
app.get("/login", response_class=HTMLResponse, response_model=None)(login_get)
app.post("/login")(limiter.limit("5/minute")(login_post))
app.get("/logout")(logout)

# ────────────────────────────────────────────────
# Page routes – each renders a Jinja2 template
# ────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/agenda", response_class=HTMLResponse)
async def page_agenda(request: Request):
    return templates.TemplateResponse("agenda.html", {"request": request})


@app.get("/taken", response_class=HTMLResponse)
async def page_tasks(request: Request):
    return templates.TemplateResponse("tasks.html", {"request": request})


@app.get("/maaltijden", response_class=HTMLResponse)
async def page_meals(request: Request):
    return templates.TemplateResponse("meals.html", {"request": request})


@app.get("/instellingen", response_class=HTMLResponse)
async def page_settings(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})


@app.get("/fotos", response_class=HTMLResponse)
async def page_photos(request: Request):
    return templates.TemplateResponse("photos.html", {"request": request})


@app.get("/gezin", response_class=HTMLResponse)
async def page_family(request: Request):
    return templates.TemplateResponse("family.html", {"request": request})
