"""
Application configuration settings.
Extend this file to add new config options as the app grows.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Database
DATABASE_URL = f"sqlite+aiosqlite:///{BASE_DIR}/familieplanner.db"

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
