"""Tests for /api/settings endpoints including backup/restore."""

import json

from httpx import AsyncClient


async def test_backup_creates_valid_file(client: AsyncClient):
    """Test that backup creates a valid JSON file with metadata."""
    # Create some test data
    await client.post(
        "/api/agenda/",
        json={
            "title": "Test Event",
            "description": "Test",
            "location": "",
            "start_time": "2026-03-10T10:00:00",
            "end_time": "2026-03-10T11:00:00",
            "all_day": False,
            "member_ids": [],
            "color": "#4ECDC4",
        },
    )

    # Create backup
    r = await client.get("/api/settings/backup")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/json"
    assert "attachment" in r.headers["content-disposition"]

    # Parse backup content
    backup_data = json.loads(r.content.decode("utf-8"))

    # Verify v2.0 structure
    assert "version" in backup_data
    assert backup_data["version"] == "2.0"
    assert "exported_at" in backup_data
    assert "app_version" in backup_data
    assert "record_counts" in backup_data
    assert "data" in backup_data

    # Verify record_counts
    assert isinstance(backup_data["record_counts"], dict)
    assert "agenda_events" in backup_data["record_counts"]
    assert backup_data["record_counts"]["agenda_events"] == 1

    # Verify data structure
    assert "agenda_events" in backup_data["data"]
    assert len(backup_data["data"]["agenda_events"]) == 1


async def test_backup_empty_database(client: AsyncClient):
    """Test backup of empty database."""
    r = await client.get("/api/settings/backup")
    assert r.status_code == 200

    backup_data = json.loads(r.content.decode("utf-8"))
    assert backup_data["version"] == "2.0"

    # All counts should be zero
    for count in backup_data["record_counts"].values():
        assert count == 0


async def test_restore_dry_run_validation(client: AsyncClient):
    """Test dry-run mode validates without modifying data."""
    # Create test data
    await client.post(
        "/api/agenda/",
        json={
            "title": "Original Event",
            "description": "",
            "location": "",
            "start_time": "2026-03-10T10:00:00",
            "end_time": "2026-03-10T11:00:00",
            "all_day": False,
            "member_ids": [],
            "color": "#4ECDC4",
        },
    )

    # Create backup
    backup_r = await client.get("/api/settings/backup")
    backup_data = backup_r.content

    # Dry-run restore
    files = {"file": ("backup.json", backup_data, "application/json")}
    r = await client.post("/api/settings/restore?dry_run=true", files=files)

    assert r.status_code == 200
    result = r.json()

    # Verify validation result structure
    assert "valid" in result
    assert result["valid"] is True
    assert "version" in result
    assert result["version"] == "2.0"
    assert "exported_at" in result
    assert "record_counts" in result
    assert "warnings" in result
    assert "errors" in result

    # Verify original data still exists (dry-run didn't modify)
    events_r = await client.get("/api/agenda/?start=2026-03-01&end=2026-03-31")
    events = events_r.json()
    assert len(events) == 1
    assert events[0]["title"] == "Original Event"


async def test_restore_invalid_json(client: AsyncClient):
    """Test restore rejects invalid JSON."""
    files = {"file": ("invalid.json", b"not valid json{", "application/json")}
    r = await client.post("/api/settings/restore", files=files)

    assert r.status_code == 400
    assert "JSON" in r.json()["detail"]


async def test_restore_missing_data_key(client: AsyncClient):
    """Test restore rejects backup without data key."""
    invalid_backup = json.dumps({"version": "2.0", "exported_at": "2026-03-07T10:00:00"})
    files = {"file": ("backup.json", invalid_backup.encode(), "application/json")}
    r = await client.post("/api/settings/restore?dry_run=true", files=files)

    assert r.status_code == 200
    result = r.json()
    assert result["valid"] is False
    assert len(result["errors"]) > 0


async def test_restore_invalid_version_format(client: AsyncClient):
    """Test restore validates version format."""
    invalid_backup = json.dumps(
        {
            "version": "invalid",
            "exported_at": "2026-03-07T10:00:00",
            "data": {
                "app_settings": [],
                "family_members": [],
                "task_lists": [],
                "task_recurrence_series": [],
                "task_recurrence_series_members": [],
                "tasks": [],
                "task_members": [],
                "recurrence_series": [],
                "recurrence_series_members": [],
                "agenda_events": [],
                "agenda_event_members": [],
                "meals": [],
                "photos": [],
            },
        }
    )
    files = {"file": ("backup.json", invalid_backup.encode(), "application/json")}
    r = await client.post("/api/settings/restore?dry_run=true", files=files)

    assert r.status_code == 200
    result = r.json()
    assert result["valid"] is False
    assert any("version" in error.lower() for error in result["errors"])


async def test_restore_success_with_data(client: AsyncClient):
    """Test successful restore with actual data."""
    # Create test data
    list_r = await client.post("/api/tasks/lists", json={"name": "Test List", "color": "#4ECDC4"})
    list_id = list_r.json()["id"]

    await client.post(
        "/api/tasks/",
        json={
            "title": "Test Task",
            "description": "Test description",
            "list_id": list_id,
            "member_ids": [],
            "due_date": "2026-03-15",
        },
    )

    await client.post(
        "/api/meals/",
        json={
            "date": "2026-03-10",
            "meal_type": "dinner",
            "name": "Test Meal",
            "description": "",
            "recipe_url": "",
            "cook_member_id": None,
        },
    )

    # Create backup
    backup_r = await client.get("/api/settings/backup")
    backup_content = backup_r.content

    # Modify database (add more data)
    await client.post(
        "/api/meals/",
        json={
            "date": "2026-03-11",
            "meal_type": "lunch",
            "name": "New Meal",
            "description": "",
            "recipe_url": "",
            "cook_member_id": None,
        },
    )

    # Verify we have 2 meals now
    meals_before = await client.get("/api/meals/?start=2026-03-01&end=2026-03-31")
    assert len(meals_before.json()) == 2

    # Restore backup
    files = {"file": ("backup.json", backup_content, "application/json")}
    r = await client.post("/api/settings/restore", files=files)

    assert r.status_code == 200
    result = r.json()
    assert result["status"] == "success"
    assert "records_imported" in result
    assert result["records_imported"]["tasks"] == 1
    assert result["records_imported"]["meals"] == 1

    # Verify database restored to backup state
    meals_after = await client.get("/api/meals/?start=2026-03-01&end=2026-03-31")
    assert len(meals_after.json()) == 1
    assert meals_after.json()[0]["name"] == "Test Meal"

    tasks_after = await client.get("/api/tasks/")
    assert len(tasks_after.json()) == 1
    assert tasks_after.json()[0]["title"] == "Test Task"


async def test_restore_backward_compatibility_v1(client: AsyncClient):
    """Test restore supports v1.0 backup format."""
    # Create v1.0 format backup (without record_counts)
    v1_backup = {
        "version": "1.0",
        "exported_at": "2026-03-07T10:00:00",
        "data": {
            "app_settings": [],
            "family_members": [],
            "task_lists": [],
            "task_recurrence_series": [],
            "task_recurrence_series_members": [],
            "tasks": [],
            "task_members": [],
            "recurrence_series": [],
            "recurrence_series_members": [],
            "agenda_events": [
                {
                    "id": 1,
                    "title": "V1 Event",
                    "description": "",
                    "location": "",
                    "start_time": "2026-03-10T10:00:00",
                    "end_time": "2026-03-10T11:00:00",
                    "all_day": False,
                    "color": "#4ECDC4",
                    "series_id": None,
                    "is_exception": False,
                    "created_at": "2026-03-07T10:00:00",
                }
            ],
            "agenda_event_members": [],
            "meals": [],
            "photos": [],
        },
    }

    files = {"file": ("v1-backup.json", json.dumps(v1_backup).encode(), "application/json")}
    r = await client.post("/api/settings/restore?dry_run=true", files=files)

    assert r.status_code == 200
    result = r.json()
    assert result["valid"] is True
    assert result["version"] == "1.0"
    # v1 backups may have warnings about missing record_counts
    assert result["record_counts"]["agenda_events"] == 1


async def test_restore_warns_on_record_count_mismatch(client: AsyncClient):
    """Test restore warns when record counts don't match actual data."""
    # Create backup with mismatched counts
    mismatched_backup = {
        "version": "2.0",
        "exported_at": "2026-03-07T10:00:00",
        "app_version": "1.0.0",
        "record_counts": {
            "agenda_events": 5,  # Says 5 but only has 1
            "tasks": 0,
        },
        "data": {
            "app_settings": [],
            "family_members": [],
            "task_lists": [],
            "task_recurrence_series": [],
            "task_recurrence_series_members": [],
            "tasks": [],
            "task_members": [],
            "recurrence_series": [],
            "recurrence_series_members": [],
            "agenda_events": [
                {
                    "id": 1,
                    "title": "Test",
                    "description": "",
                    "location": "",
                    "start_time": "2026-03-10T10:00:00",
                    "end_time": "2026-03-10T11:00:00",
                    "all_day": False,
                    "color": "#4ECDC4",
                    "series_id": None,
                    "is_exception": False,
                    "created_at": "2026-03-07T10:00:00",
                }
            ],
            "agenda_event_members": [],
            "meals": [],
            "photos": [],
        },
    }

    files = {"file": ("backup.json", json.dumps(mismatched_backup).encode(), "application/json")}
    r = await client.post("/api/settings/restore?dry_run=true", files=files)

    assert r.status_code == 200
    result = r.json()
    assert result["valid"] is True  # Still valid, just warnings
    assert len(result["warnings"]) > 0
    assert any("agenda_events" in warning for warning in result["warnings"])
    assert any("verwacht 5" in warning for warning in result["warnings"])


async def test_restore_future_version_warning(client: AsyncClient):
    """Test restore warns about future backup versions."""
    future_backup = {
        "version": "99.0",
        "exported_at": "2026-03-07T10:00:00",
        "app_version": "99.0.0",
        "data": {
            "app_settings": [],
            "family_members": [],
            "task_lists": [],
            "task_recurrence_series": [],
            "task_recurrence_series_members": [],
            "tasks": [],
            "task_members": [],
            "recurrence_series": [],
            "recurrence_series_members": [],
            "agenda_events": [],
            "agenda_event_members": [],
            "meals": [],
            "photos": [],
        },
    }

    files = {"file": ("backup.json", json.dumps(future_backup).encode(), "application/json")}
    r = await client.post("/api/settings/restore?dry_run=true", files=files)

    assert r.status_code == 200
    result = r.json()
    assert result["valid"] is True
    assert len(result["warnings"]) > 0
    assert any("nieuwer" in warning.lower() for warning in result["warnings"])


async def test_get_settings(client: AsyncClient):
    """Test retrieving current settings."""
    r = await client.get("/api/settings/")
    assert r.status_code == 200

    settings = r.json()
    assert "auth_required" in settings
    assert "theme" in settings
    assert "weather_enabled" in settings
    assert "dashboard_photo_enabled" in settings


async def test_update_settings(client: AsyncClient):
    """Test updating settings."""
    r = await client.put("/api/settings/", json={"theme": "dark", "weather_enabled": False})

    assert r.status_code == 200
    settings = r.json()
    assert settings["theme"] == "dark"
    assert settings["weather_enabled"] is False
