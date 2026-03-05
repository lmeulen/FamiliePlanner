"""API router for application settings."""
import json
from datetime import date, datetime, time
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_auth_required, set_auth_required
from app.database import get_db
from app.models.settings import AppSetting
from app.models.family import FamilyMember
from app.models.meals import Meal
from app.models.tasks import Task, TaskList, TaskRecurrenceSeries, task_members, task_recurrence_series_members
from app.models.agenda import AgendaEvent, RecurrenceSeries, agenda_event_members, recurrence_series_members
from app.models.photos import Photo

router = APIRouter(prefix="/api/settings", tags=["settings"])

# Keys managed by this router
_KEYS = {"auth_required", "dashboard_photo_height", "dashboard_photo_enabled", "theme"}


async def _get(db: AsyncSession, key: str, default: str) -> str:
    row = await db.get(AppSetting, key)
    return row.value if row else default


async def _set(db: AsyncSession, key: str, value: str) -> None:
    row = await db.get(AppSetting, key)
    if row:
        row.value = value
    else:
        db.add(AppSetting(key=key, value=value))
    await db.commit()


@router.get("/", response_model=dict)
async def get_settings(db: AsyncSession = Depends(get_db)):
    return {
        "auth_required": (await _get(db, "auth_required", str(get_auth_required()))).lower() in ("1", "true"),
        "dashboard_photo_height": int(await _get(db, "dashboard_photo_height", "35")),
        "dashboard_photo_enabled": (await _get(db, "dashboard_photo_enabled", "true")).lower() in ("1", "true"),
        "theme": await _get(db, "theme", "system"),
    }


@router.put("/", response_model=dict)
async def update_settings(payload: dict, db: AsyncSession = Depends(get_db)):
    if "auth_required" in payload:
        val = bool(payload["auth_required"])
        await _set(db, "auth_required", str(val).lower())
        set_auth_required(val)

    if "dashboard_photo_enabled" in payload:
        await _set(db, "dashboard_photo_enabled", str(bool(payload["dashboard_photo_enabled"])).lower())

    if "dashboard_photo_height" in payload:
        h = max(10, min(80, int(payload["dashboard_photo_height"])))
        await _set(db, "dashboard_photo_height", str(h))

    if "theme" in payload:
        t = payload["theme"] if payload["theme"] in ("light", "dark", "system") else "system"
        await _set(db, "theme", t)

    logger.info("settings.updated payload={}", {k: v for k, v in payload.items() if k in _KEYS})
    return await get_settings(db)


def _serialize_value(value):
    """Convert database values to JSON-serializable format."""
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    return value


async def _export_table_data(db: AsyncSession, model, table_name: str) -> list[dict]:
    """Export all rows from a table as list of dicts."""
    result = await db.execute(select(model))
    rows = result.scalars().all()
    data = []
    for row in rows:
        row_dict = {}
        for column in model.__table__.columns:
            value = getattr(row, column.name)
            row_dict[column.name] = _serialize_value(value)
        data.append(row_dict)
    return data


async def _export_junction_table(db: AsyncSession, table) -> list[dict]:
    """Export all rows from a many-to-many junction table."""
    result = await db.execute(select(table))
    rows = result.all()
    return [dict(row._mapping) for row in rows]


@router.get("/backup")
async def backup_database(db: AsyncSession = Depends(get_db)):
    """Export entire database as JSON file."""
    logger.info("backup.started")

    # Export all tables
    backup_data = {
        "exported_at": datetime.now().isoformat(),
        "version": "1.0",
        "data": {
            "app_settings": await _export_table_data(db, AppSetting, "app_settings"),
            "family_members": await _export_table_data(db, FamilyMember, "family_members"),
            "task_lists": await _export_table_data(db, TaskList, "task_lists"),
            "task_recurrence_series": await _export_table_data(db, TaskRecurrenceSeries, "task_recurrence_series"),
            "task_recurrence_series_members": await _export_junction_table(db, task_recurrence_series_members),
            "tasks": await _export_table_data(db, Task, "tasks"),
            "task_members": await _export_junction_table(db, task_members),
            "recurrence_series": await _export_table_data(db, RecurrenceSeries, "recurrence_series"),
            "recurrence_series_members": await _export_junction_table(db, recurrence_series_members),
            "agenda_events": await _export_table_data(db, AgendaEvent, "agenda_events"),
            "agenda_event_members": await _export_junction_table(db, agenda_event_members),
            "meals": await _export_table_data(db, Meal, "meals"),
            "photos": await _export_table_data(db, Photo, "photos"),
        }
    }

    # Convert to formatted JSON
    json_content = json.dumps(backup_data, indent=2, ensure_ascii=False)

    # Create a streaming response with the JSON file
    json_bytes = BytesIO(json_content.encode('utf-8'))
    filename = f"familieplanner-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"

    logger.info("backup.completed filename={}", filename)

    return StreamingResponse(
        json_bytes,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


async def _clear_all_data(db: AsyncSession):
    """Clear all data from the database."""
    # Delete in reverse order to respect foreign key constraints
    await db.execute(agenda_event_members.delete())
    await db.execute(recurrence_series_members.delete())
    await db.execute(task_members.delete())
    await db.execute(task_recurrence_series_members.delete())

    for model in [AgendaEvent, RecurrenceSeries, Task, TaskRecurrenceSeries, TaskList, Meal, Photo, FamilyMember, AppSetting]:
        await db.execute(model.__table__.delete())

    await db.commit()


def _deserialize_value(value, column_type):
    """Convert JSON values back to Python types."""
    if value is None:
        return None

    type_name = str(column_type)
    if 'DATE' in type_name.upper() and 'TIME' not in type_name.upper():
        return datetime.fromisoformat(value).date() if isinstance(value, str) else value
    elif 'DATETIME' in type_name.upper():
        return datetime.fromisoformat(value) if isinstance(value, str) else value
    elif 'TIME' in type_name.upper() and 'DATE' not in type_name.upper():
        # Parse time from ISO format (HH:MM:SS)
        if isinstance(value, str):
            parts = value.split(':')
            return time(int(parts[0]), int(parts[1]), int(parts[2].split('.')[0]) if len(parts) > 2 else 0)
        return value

    return value


async def _import_table_data(db: AsyncSession, model, data: list[dict]):
    """Import rows into a table."""
    for row_dict in data:
        # Convert values to proper types
        converted = {}
        for column in model.__table__.columns:
            if column.name in row_dict:
                converted[column.name] = _deserialize_value(row_dict[column.name], column.type)

        # Insert row
        db.add(model(**converted))


async def _import_junction_data(db: AsyncSession, table, data: list[dict]):
    """Import rows into a junction table."""
    for row_dict in data:
        await db.execute(table.insert().values(**row_dict))


@router.post("/restore")
async def restore_database(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """Restore database from uploaded JSON backup file."""
    logger.info("restore.started filename={}", file.filename)

    try:
        # Read and parse JSON
        content = await file.read()
        backup_data = json.loads(content.decode('utf-8'))

        # Validate structure
        if "data" not in backup_data:
            raise HTTPException(status_code=400, detail="Invalid backup file format: missing 'data' key")

        data = backup_data["data"]

        # Clear existing data
        await _clear_all_data(db)

        # Import data in correct order (respecting foreign keys)
        # 1. Independent tables first
        if "app_settings" in data:
            await _import_table_data(db, AppSetting, data["app_settings"])
        if "family_members" in data:
            await _import_table_data(db, FamilyMember, data["family_members"])
        if "task_lists" in data:
            await _import_table_data(db, TaskList, data["task_lists"])

        # 2. Recurrence series
        if "task_recurrence_series" in data:
            await _import_table_data(db, TaskRecurrenceSeries, data["task_recurrence_series"])
        if "recurrence_series" in data:
            await _import_table_data(db, RecurrenceSeries, data["recurrence_series"])

        # 3. Main tables with foreign keys
        if "tasks" in data:
            await _import_table_data(db, Task, data["tasks"])
        if "agenda_events" in data:
            await _import_table_data(db, AgendaEvent, data["agenda_events"])
        if "meals" in data:
            await _import_table_data(db, Meal, data["meals"])
        if "photos" in data:
            await _import_table_data(db, Photo, data["photos"])

        # 4. Junction tables last
        if "task_recurrence_series_members" in data:
            await _import_junction_data(db, task_recurrence_series_members, data["task_recurrence_series_members"])
        if "task_members" in data:
            await _import_junction_data(db, task_members, data["task_members"])
        if "recurrence_series_members" in data:
            await _import_junction_data(db, recurrence_series_members, data["recurrence_series_members"])
        if "agenda_event_members" in data:
            await _import_junction_data(db, agenda_event_members, data["agenda_event_members"])

        await db.commit()

        logger.info("restore.completed")
        return {"status": "success", "message": "Database restored successfully"}

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        await db.rollback()
        logger.error("restore.failed error={}", str(e))
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")
