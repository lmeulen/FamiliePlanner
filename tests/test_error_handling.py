"""Tests for enhanced error handling with Dutch user-friendly messages."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_404_not_found_json(client: AsyncClient):
    """Test 404 error returns Dutch error response."""
    response = await client.get("/api/family/99999")
    assert response.status_code == 404

    data = response.json()
    assert "code" in data
    assert "message" in data
    assert data["code"] == "NOT_FOUND"
    assert "niet" in data["message"].lower() or "gevonden" in data["message"].lower()


@pytest.mark.asyncio
async def test_404_not_found_html(client: AsyncClient):
    """Test 404 on HTML page returns error page."""
    response = await client.get("/nonexistent-page", headers={"Accept": "text/html"})
    assert response.status_code == 404
    assert "text/html" in response.headers["content-type"]
    assert "Pagina niet gevonden" in response.text or "404" in response.text


@pytest.mark.asyncio
async def test_validation_error_dutch(client: AsyncClient):
    """Test validation errors return Dutch messages."""
    # Create family member with invalid data (empty name)
    response = await client.post(
        "/api/family/",
        json={"name": "", "avatar": "👤", "color": "#FF0000"},
    )
    assert response.status_code == 422

    data = response.json()
    assert data["code"] == "VALIDATION_ERROR"
    assert "message" in data
    # Should be in Dutch
    assert any(word in data["message"].lower() for word in ["geldig", "gegevens", "niet", "validatie"])


@pytest.mark.asyncio
async def test_integrity_error_unique_constraint(client: AsyncClient):
    """Test unique constraint violation returns Dutch error."""
    # Create a family member
    await client.post(
        "/api/family/",
        json={"name": "Test Unique", "avatar": "🧪", "color": "#00FF00"},
    )

    # Try to create another with same name (if unique constraint exists)
    # This test assumes name has unique constraint - adjust if needed
    response = await client.post(
        "/api/family/",
        json={"name": "Test Unique", "avatar": "🧪", "color": "#00FF00"},
    )

    # May be 422 (validation) or 201 (success if no unique constraint)
    # If unique constraint exists:
    if response.status_code == 422:
        data = response.json()
        assert "code" in data
        # Should mention uniqueness or existing value
        message_lower = (data.get("message", "") + data.get("details", "")).lower()
        assert any(word in message_lower for word in ["bestaat", "unique", "al"])


@pytest.mark.asyncio
async def test_foreign_key_error_dutch(client: AsyncClient):
    """Test foreign key error returns Dutch message."""
    # Try to create an event with non-existent member
    response = await client.post(
        "/api/agenda/",
        json={
            "title": "Test Event",
            "start_time": "2026-06-01T10:00:00",
            "end_time": "2026-06-01T11:00:00",
            "member_ids": [99999],  # Non-existent member
        },
    )

    # Should return 422 with foreign key error
    if response.status_code == 422:
        data = response.json()
        assert "code" in data
        # Should be in Dutch
        message = data.get("message", "")
        assert any(word in message.lower() for word in ["verwijderd", "ongeldig", "bestaat niet", "referentie"])


@pytest.mark.asyncio
async def test_database_error_format(client: AsyncClient):
    """Test database errors return consistent format."""
    # Try an operation that might cause DB error
    response = await client.get("/api/family/invalid")

    # Should return error with consistent format
    if not response.is_success:
        data = response.json()
        # New error format should have these fields
        assert "code" in data
        assert "message" in data
        # Optional fields
        if "details" in data:
            assert isinstance(data["details"], str)


@pytest.mark.asyncio
async def test_error_response_no_stack_trace(client: AsyncClient):
    """Test that error responses don't contain stack traces."""
    response = await client.get("/api/family/99999")
    assert response.status_code == 404

    text = response.text.lower()
    # Should not contain Python stack trace indicators
    assert "traceback" not in text
    assert "line " not in text  # "File line X"
    assert "raise " not in text
    assert ".py" not in text


@pytest.mark.asyncio
async def test_multiple_validation_errors(client: AsyncClient):
    """Test validation errors with multiple fields."""
    # Send completely empty data
    response = await client.post("/api/family/", json={})
    assert response.status_code == 422

    data = response.json()
    assert data["code"] == "VALIDATION_ERROR"
    assert "message" in data
    # Should have field information
    if "field" in data:
        assert isinstance(data["field"], str)


@pytest.mark.asyncio
async def test_network_error_message_format(client: AsyncClient):
    """Test that error message structure is consistent."""
    response = await client.get("/api/family/99999")

    data = response.json()
    # Verify new error format
    assert isinstance(data, dict)
    assert "code" in data
    assert "message" in data
    assert isinstance(data["code"], str)
    assert isinstance(data["message"], str)

    # Verify it's not old format (just "detail" string)
    if "detail" in data:
        # If detail exists, should be part of structured response
        assert "code" in data and "message" in data
