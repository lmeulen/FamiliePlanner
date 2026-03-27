"""Tests for security headers middleware."""

import pytest


@pytest.mark.asyncio
async def test_security_headers_present(client):
    """Test that security headers are added to responses."""
    response = await client.get("/health")

    # Check that all expected security headers are present
    assert "Content-Security-Policy" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "X-Content-Type-Options" in response.headers
    assert "X-XSS-Protection" in response.headers
    assert "Referrer-Policy" in response.headers
    assert "Permissions-Policy" in response.headers


@pytest.mark.asyncio
async def test_csp_header_content(client):
    """Test that CSP header contains expected directives."""
    response = await client.get("/health")

    csp = response.headers["Content-Security-Policy"]

    # Check for key CSP directives
    assert "default-src 'self'" in csp
    assert "script-src 'self' 'unsafe-inline'" in csp
    assert "style-src 'self' 'unsafe-inline'" in csp
    assert "img-src 'self' data: https:" in csp
    assert "frame-ancestors 'none'" in csp
    assert "form-action 'self'" in csp


@pytest.mark.asyncio
async def test_x_frame_options_deny(client):
    """Test that X-Frame-Options is set to DENY."""
    response = await client.get("/health")

    assert response.headers["X-Frame-Options"] == "DENY"


@pytest.mark.asyncio
async def test_x_content_type_options_nosniff(client):
    """Test that X-Content-Type-Options is set to nosniff."""
    response = await client.get("/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"


@pytest.mark.asyncio
async def test_referrer_policy(client):
    """Test that Referrer-Policy is set correctly."""
    response = await client.get("/health")

    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


@pytest.mark.asyncio
async def test_permissions_policy(client):
    """Test that Permissions-Policy disables unnecessary features."""
    response = await client.get("/health")

    permissions = response.headers["Permissions-Policy"]

    # Check that sensitive features are disabled
    assert "geolocation=()" in permissions
    assert "microphone=()" in permissions
    assert "camera=()" in permissions
    assert "payment=()" in permissions
    assert "usb=()" in permissions


@pytest.mark.asyncio
async def test_hsts_not_present_in_development(client):
    """Test that HSTS header is not present in development (HTTP)."""
    response = await client.get("/health")

    # HSTS should not be present in development or over HTTP
    assert "Strict-Transport-Security" not in response.headers


@pytest.mark.asyncio
async def test_csp_report_endpoint(client):
    """Test that CSP violation reporting endpoint works."""
    # Send a mock CSP violation report
    violation_report = {
        "csp-report": {
            "document-uri": "http://test/",
            "violated-directive": "script-src 'self'",
            "blocked-uri": "http://evil.com/script.js",
        }
    }

    response = await client.post("/api/csp-report", json=violation_report)

    assert response.status_code == 200
    assert response.json() == {"status": "reported"}


@pytest.mark.asyncio
async def test_csp_report_endpoint_handles_invalid_data(client):
    """Test that CSP report endpoint handles invalid data gracefully."""
    # Send invalid data
    response = await client.post("/api/csp-report", json={"invalid": "data"})

    # Should still return 200 and not crash
    assert response.status_code == 200
    assert response.json() == {"status": "reported"}
