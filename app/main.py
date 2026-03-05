"""
FamiliePlanner – FastAPI application entry point.
Mounts static files, registers routers, serves Jinja2 templates.
"""
from contextlib import asynccontextmanager
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger
from starlette.middleware.sessions import SessionMiddleware

from app.auth import AuthMiddleware, login_get, login_post, logout
from app.config import APP_TITLE, APP_VERSION, SECRET_KEY
from app.database import init_db
from app.logging_config import setup_logging
from app.routers import agenda, family, meals, tasks

BASE_DIR = Path(__file__).resolve().parent

# Initialise logging before anything else
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting {} v{}", APP_TITLE, APP_VERSION)
    await init_db()
    logger.info("Database ready")
    yield
    logger.info("Shutting down {}", APP_TITLE)


app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ── Middleware (outermost last = SessionMiddleware runs first) ────
app.add_middleware(AuthMiddleware)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, https_only=False)


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

# Auth routes
app.get("/login", response_class=HTMLResponse)(login_get)
app.post("/login")(login_post)
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


@app.get("/gezin", response_class=HTMLResponse)
async def page_family(request: Request):
    return templates.TemplateResponse("family.html", {"request": request})
