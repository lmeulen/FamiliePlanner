"""
Application configuration settings.
Extend this file to add new config options as the app grows.
"""

import os
import secrets
from pathlib import Path

import bcrypt
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


def verify_password(plain: str, stored: str) -> bool:
    """Verify a password against a stored value.

    Accepts either a bcrypt hash (starts with '$2') or a plain-text value
    for backwards compatibility with existing .env files.
    """
    if stored.startswith("$2"):
        return bcrypt.checkpw(plain.encode(), stored.encode())
    # Plain-text fallback – use timing-safe comparison
    return secrets.compare_digest(plain.encode(), stored.encode())


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of the given password."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


# Security
ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "development")
ALLOWED_HOSTS: str = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1")

# Family members – edit names/colours here or expose via API later
FAMILY_MEMBERS_DEFAULT = [
    {"id": 1, "name": "Leo", "color": "#FF6B6B", "avatar": "👨"},
    {"id": 2, "name": "Erna", "color": "#4ECDC4", "avatar": "👩"},
    {"id": 3, "name": "Ruben", "color": "#FFE66D", "avatar": "🧒"},
    {"id": 4, "name": "Thomas", "color": "#6C5CE7", "avatar": "🧒"},
    {"id": 5, "name": "Hayden", "color": "#FF8E53", "avatar": "🧒"},
]

# Weather API (OpenWeatherMap)
OPENWEATHER_API_KEY: str = os.environ.get("OPENWEATHER_API_KEY", "")

# Cozi integration
COZI_ICS_URL: str = os.environ.get("COZI_ICS_URL", "")

# App metadata
APP_TITLE = "FamiliePlanner"
APP_VERSION = "1.0.0"
