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

from app.config import APP_TITLE, APP_VERSION
from app.database import init_db
from app.routers import agenda, family, meals, tasks

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

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
