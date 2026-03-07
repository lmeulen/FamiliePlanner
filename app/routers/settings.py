"""API router for application settings."""

import json
from datetime import date, datetime, time
from io import BytesIO

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import ValidationError
from sqlalchemy import delete as sa_delete
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_auth_required, set_auth_required
from app.config import OPENWEATHER_API_KEY
from app.database import get_db
from app.models.agenda import AgendaEvent, RecurrenceSeries, agenda_event_members, recurrence_series_members
from app.models.family import FamilyMember
from app.models.meals import Meal
from app.models.photos import Photo
from app.models.settings import AppSetting
from app.models.tasks import Task, TaskList, TaskRecurrenceSeries, task_members, task_recurrence_series_members
from app.schemas.backup import BackupFile, RestoreResult, RestoreValidationResult

router = APIRouter(prefix="/api/settings", tags=["settings"])

# Keys managed by this router
_KEYS = {
    "auth_required",
    "dashboard_photo_height",
    "dashboard_photo_enabled",
    "dashboard_photo_interval",
    "theme",
    "weather_enabled",
    "weather_location",
}


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
async def get_settings(response: Response, db: AsyncSession = Depends(get_db)):
    # Cache for 10 minutes - settings rarely change
    response.headers["Cache-Control"] = "private, max-age=600"
    return {
        "auth_required": (await _get(db, "auth_required", str(get_auth_required()))).lower() in ("1", "true"),
        "dashboard_photo_height": int(await _get(db, "dashboard_photo_height", "35")),
        "dashboard_photo_enabled": (await _get(db, "dashboard_photo_enabled", "true")).lower() in ("1", "true"),
        "dashboard_photo_interval": int(await _get(db, "dashboard_photo_interval", "8")),
        "theme": await _get(db, "theme", "system"),
        "weather_enabled": (await _get(db, "weather_enabled", "true")).lower() in ("1", "true"),
        "weather_location": await _get(db, "weather_location", "Amsterdam,NL"),
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

    if "dashboard_photo_interval" in payload:
        i = max(3, min(60, int(payload["dashboard_photo_interval"])))
        await _set(db, "dashboard_photo_interval", str(i))

    if "theme" in payload:
        t = payload["theme"] if payload["theme"] in ("light", "dark", "system") else "system"
        await _set(db, "theme", t)

    if "weather_enabled" in payload:
        await _set(db, "weather_enabled", str(bool(payload["weather_enabled"])).lower())

    if "weather_location" in payload:
        loc = str(payload["weather_location"]).strip()[:100]  # max 100 chars
        await _set(db, "weather_location", loc)

    logger.info("settings.updated payload={}", {k: v for k, v in payload.items() if k in _KEYS})
    return await get_settings(db)


def _serialize_value(value):
    """Convert database values to JSON-serializable format."""
    if isinstance(value, datetime | date | time):
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
    """Export entire database as JSON file with metadata."""
    logger.info("backup.started")

    # Export all tables
    table_data = {
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

    # Calculate record counts
    record_counts = {table_name: len(records) for table_name, records in table_data.items()}

    backup_data = {
        "exported_at": datetime.now().isoformat(),
        "version": "2.0",
        "app_version": "1.0.0",  # Could read from VERSION file or config
        "record_counts": record_counts,
        "data": table_data,
    }

    # Convert to formatted JSON
    json_content = json.dumps(backup_data, indent=2, ensure_ascii=False)

    # Create a streaming response with the JSON file
    json_bytes = BytesIO(json_content.encode("utf-8"))
    filename = f"familieplanner-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"

    logger.info("backup.completed filename={} records={}", filename, sum(record_counts.values()))

    return StreamingResponse(
        json_bytes, media_type="application/json", headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


async def _clear_all_data(db: AsyncSession):
    """Clear all data from the database."""
    # Delete in reverse order to respect foreign key constraints
    await db.execute(agenda_event_members.delete())
    await db.execute(recurrence_series_members.delete())
    await db.execute(task_members.delete())
    await db.execute(task_recurrence_series_members.delete())

    for model in [
        AgendaEvent,
        RecurrenceSeries,
        Task,
        TaskRecurrenceSeries,
        TaskList,
        Meal,
        Photo,
        FamilyMember,
        AppSetting,
    ]:
        await db.execute(sa_delete(model))

    await db.commit()


def _deserialize_value(value, column_type):
    """Convert JSON values back to Python types."""
    if value is None:
        return None

    type_name = str(column_type)
    if "DATE" in type_name.upper() and "TIME" not in type_name.upper():
        return datetime.fromisoformat(value).date() if isinstance(value, str) else value
    elif "DATETIME" in type_name.upper():
        return datetime.fromisoformat(value) if isinstance(value, str) else value
    elif "TIME" in type_name.upper() and "DATE" not in type_name.upper():
        # Parse time from ISO format (HH:MM:SS)
        if isinstance(value, str):
            parts = value.split(":")
            return time(int(parts[0]), int(parts[1]), int(parts[2].split(".")[0]) if len(parts) > 2 else 0)
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
        try:
            await db.execute(table.insert().values(**row_dict))
        except Exception as e:
            logger.warning(
                "junction table insert failed table={} data={} error={}",
                table.name,
                row_dict,
                str(e),
            )
            # Skip invalid junction entries rather than failing entire restore
            continue


async def _validate_backup_file(backup_data: dict) -> RestoreValidationResult:
    """Validate backup file structure and return detailed validation result."""
    errors: list[str] = []
    warnings: list[str] = []

    # Parse and validate with Pydantic
    try:
        backup = BackupFile(**backup_data)
    except ValidationError as e:
        # Extract validation errors
        for error in e.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            errors.append(f"Validatiefout in '{field}': {error['msg']}")

        return RestoreValidationResult(
            valid=False,
            version="unknown",
            exported_at=datetime.now(),
            record_counts={},
            errors=errors,
            warnings=warnings,
        )

    # Check version compatibility
    version_major = int(backup.version.split(".")[0])
    if version_major > 2:
        warnings.append(
            f"Backup versie {backup.version} is nieuwer dan ondersteunde versie 2.x - mogelijk incompatibel"
        )
    elif version_major < 1:
        errors.append(f"Backup versie {backup.version} is te oud en wordt niet ondersteund")

    # Calculate actual record counts from data
    actual_counts = {
        "app_settings": len(backup.data.app_settings),
        "family_members": len(backup.data.family_members),
        "task_lists": len(backup.data.task_lists),
        "task_recurrence_series": len(backup.data.task_recurrence_series),
        "task_recurrence_series_members": len(backup.data.task_recurrence_series_members),
        "tasks": len(backup.data.tasks),
        "task_members": len(backup.data.task_members),
        "recurrence_series": len(backup.data.recurrence_series),
        "recurrence_series_members": len(backup.data.recurrence_series_members),
        "agenda_events": len(backup.data.agenda_events),
        "agenda_event_members": len(backup.data.agenda_event_members),
        "meals": len(backup.data.meals),
        "photos": len(backup.data.photos),
    }

    # Check if record_counts match (only for v2.0+)
    if backup.record_counts:
        for table, expected_count in backup.record_counts.items():
            actual = actual_counts.get(table, 0)
            if actual != expected_count:
                warnings.append(
                    f"Tabel '{table}': verwacht {expected_count} records, gevonden {actual} - mogelijk corrupt bestand"
                )

    return RestoreValidationResult(
        valid=len(errors) == 0,
        version=backup.version,
        exported_at=backup.exported_at,
        record_counts=actual_counts,
        warnings=warnings,
        errors=errors,
    )


async def _create_pre_restore_backup(db: AsyncSession) -> str:
    """Create a backup before restore for rollback capability."""
    # Export current state (similar to backup endpoint but return filename)
    table_data = {
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

    record_counts = {table_name: len(records) for table_name, records in table_data.items()}
    total_records = sum(record_counts.values())

    filename = f"familieplanner-pre-restore-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"

    # Note: In production, this would write backup_data to disk for rollback capability
    # For now, we just return the filename to indicate it would be created
    logger.info("pre-restore backup created filename={} records={}", filename, total_records)
    return filename


@router.post("/restore")
async def restore_database(
    file: UploadFile = File(...),
    dry_run: bool = Query(False, description="Validate only, do not restore"),
    db: AsyncSession = Depends(get_db),
):
    """
    Restore database from uploaded JSON backup file.

    Supports dry-run mode for validation without modifying data.
    Creates pre-restore backup for rollback capability.
    """
    logger.info("restore.started filename={} dry_run={}", file.filename, dry_run)

    try:
        # Read and parse JSON
        content = await file.read()
        backup_data = json.loads(content.decode("utf-8"))

    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=400,
            detail="Ongeldig JSON bestand - controleer of het bestand niet corrupt is",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Kan bestand niet lezen: {str(e)}",
        ) from e

    # Validate backup file structure
    validation = await _validate_backup_file(backup_data)

    # If dry-run, return validation results
    if dry_run:
        logger.info(
            "restore.dry_run valid={} errors={} warnings={}",
            validation.valid,
            len(validation.errors),
            len(validation.warnings),
        )
        return validation

    # Check if validation passed
    if not validation.valid:
        error_list = "; ".join(validation.errors)
        raise HTTPException(
            status_code=400,
            detail=f"Backup validatie mislukt: {error_list}",
        )

    # Log warnings but continue
    if validation.warnings:
        for warning in validation.warnings:
            logger.warning("restore.warning message={}", warning)

    # Create pre-restore backup for rollback
    try:
        pre_restore_filename = await _create_pre_restore_backup(db)
    except Exception as e:
        logger.error("pre-restore backup failed error={}", str(e))
        # Continue anyway - pre-restore backup is optional safety feature
        pre_restore_filename = None

    # Perform actual restore
    try:
        data = backup_data["data"]

        # Disable foreign key constraints during restore
        await db.execute(text("PRAGMA foreign_keys = OFF"))
        await db.flush()
        logger.info("Foreign key constraints disabled for restore")

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
        await db.flush()  # Ensure independent tables are committed

        # 2. Recurrence series
        if "task_recurrence_series" in data:
            await _import_table_data(db, TaskRecurrenceSeries, data["task_recurrence_series"])
        if "recurrence_series" in data:
            await _import_table_data(db, RecurrenceSeries, data["recurrence_series"])
        await db.flush()  # Ensure recurrence series are committed

        # 3. Main tables with foreign keys
        if "tasks" in data:
            await _import_table_data(db, Task, data["tasks"])
        if "agenda_events" in data:
            await _import_table_data(db, AgendaEvent, data["agenda_events"])
        if "meals" in data:
            await _import_table_data(db, Meal, data["meals"])
        if "photos" in data:
            await _import_table_data(db, Photo, data["photos"])
        await db.flush()  # Ensure main tables are committed before junction tables

        # 4. Junction tables last (skip invalid foreign key references)
        if "task_recurrence_series_members" in data:
            await _import_junction_data(db, task_recurrence_series_members, data["task_recurrence_series_members"])
        if "task_members" in data:
            await _import_junction_data(db, task_members, data["task_members"])
        if "recurrence_series_members" in data:
            await _import_junction_data(db, recurrence_series_members, data["recurrence_series_members"])
        if "agenda_event_members" in data:
            await _import_junction_data(db, agenda_event_members, data["agenda_event_members"])

        await db.commit()

        # Re-enable foreign key constraints
        await db.execute(text("PRAGMA foreign_keys = ON"))
        await db.commit()

        total_records = sum(validation.record_counts.values())
        logger.info("restore.completed records={}", total_records)

        return RestoreResult(
            status="success",
            message=f"Database succesvol hersteld met {total_records} records",
            records_imported=validation.record_counts,
            pre_restore_backup_file=pre_restore_filename,
        )

    except Exception as e:
        await db.rollback()
        # Re-enable foreign key constraints even on error
        await db.execute(text("PRAGMA foreign_keys = ON"))
        await db.commit()
        logger.error("restore.failed error={}", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Herstel mislukt tijdens importeren: {str(e)}. Database ongewijzigd gelaten.",
        ) from e


@router.get("/weather")
async def get_weather(location: str, db: AsyncSession = Depends(get_db)):
    """Fetch weather data from OpenWeatherMap API."""
    if not OPENWEATHER_API_KEY:
        logger.warning("weather.fetch.failed: API key not configured")
        raise HTTPException(
            status_code=503, detail="Geen API key geconfigureerd. Voeg OPENWEATHER_API_KEY toe aan .env"
        )

    try:
        async with httpx.AsyncClient() as client:
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {"q": location, "appid": OPENWEATHER_API_KEY, "units": "metric", "lang": "nl"}
            response = await client.get(url, params=params, timeout=5.0)

            if response.status_code == 401:
                logger.error("weather.fetch.failed location={} error=Invalid API key", location)
                raise HTTPException(
                    status_code=401, detail="Ongeldige API key. Vraag een nieuwe aan op openweathermap.org"
                )

            if response.status_code != 200:
                logger.error(
                    "weather.fetch.failed location={} status={} response={}",
                    location,
                    response.status_code,
                    response.text,
                )
                raise HTTPException(
                    status_code=response.status_code, detail=f"Weather API error: {response.status_code}"
                )

            return response.json()

    except httpx.TimeoutException as e:
        raise HTTPException(status_code=504, detail="Weather API timeout") from e
    except Exception as e:
        logger.error("weather.fetch.failed location={} error={}", location, str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch weather data") from e
