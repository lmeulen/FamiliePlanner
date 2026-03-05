"""
Application configuration settings.
Extend this file to add new config options as the app grows.
"""
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file if present (development convenience)
load_dotenv(BASE_DIR / ".env")

# Database
DATABASE_URL = f"sqlite+aiosqlite:///{BASE_DIR}/familieplanner.db"

# Authentication
SECRET_KEY: str = os.environ.get("SECRET_KEY", secrets.token_hex(32))
APP_USERNAME: str = os.environ.get("APP_USERNAME", "admin")
APP_PASSWORD: str = os.environ.get("APP_PASSWORD", "familieplanner")
AUTH_REQUIRED: bool = os.environ.get("AUTH_REQUIRED", "true").lower() not in ("0", "false", "no")

# Family members – edit names/colours here or expose via API later
FAMILY_MEMBERS_DEFAULT = [
    {"id": 1, "name": "Leo",   "color": "#FF6B6B", "avatar": "👨"},
    {"id": 2, "name": "Erna",   "color": "#4ECDC4", "avatar": "👩"},
    {"id": 3, "name": "Ruben", "color": "#FFE66D", "avatar": "🧒"},
    {"id": 4, "name": "Thomas", "color": "#6C5CE7", "avatar": "🧒"},
    {"id": 5, "name": "Hayden", "color": "#FF8E53", "avatar": "🧒"},
]

# App metadata
APP_TITLE = "FamiliePlanner"
APP_VERSION = "1.0.0"
