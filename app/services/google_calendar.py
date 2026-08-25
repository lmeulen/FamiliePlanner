"""Thin async wrapper around the Google Calendar API.

Uses a service account: share the target calendar with the service account's
email address and grant "Make changes to events". The SDK is synchronous, so
calls run in a worker thread; the sync worker is off the request path anyway.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from loguru import logger

from app.config import BASE_DIR

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

DEFAULT_CREDENTIALS_PATH = BASE_DIR / "data" / "google_service_account.json"


class GoogleCalendarError(RuntimeError):
    """Raised when the Google Calendar API cannot be reached or rejects a call."""


class GoogleCalendarNotConfigured(GoogleCalendarError):
    """Raised when credentials or the calendar id are missing."""


def credentials_path() -> Path:
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()
    return Path(raw) if raw else DEFAULT_CREDENTIALS_PATH


def credentials_available() -> bool:
    return credentials_path().is_file()


def _build_service() -> Any:
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError as exc:  # pragma: no cover - depends on optional install
        raise GoogleCalendarNotConfigured(
            "google-api-python-client is niet geïnstalleerd. Draai: pip install -r requirements.txt"
        ) from exc

    path = credentials_path()
    if not path.is_file():
        raise GoogleCalendarNotConfigured(f"Service account bestand niet gevonden: {path}")

    creds = service_account.Credentials.from_service_account_file(str(path), scopes=SCOPES)
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


class GoogleCalendarClient:
    """Minimal event CRUD against one calendar."""

    def __init__(self, calendar_id: str):
        if not calendar_id:
            raise GoogleCalendarNotConfigured("Geen Google Calendar ID geconfigureerd.")
        self.calendar_id = calendar_id
        self._service: Any = None

    def _events(self) -> Any:
        if self._service is None:
            self._service = _build_service()
        return self._service.events()

    async def _call(self, fn: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return await asyncio.to_thread(lambda: fn(*args, **kwargs).execute())
        except (TimeoutError, OSError) as exc:
            raise GoogleCalendarError(
                "Google Calendar is tijdelijk niet bereikbaar. Controleer de internetverbinding en probeer opnieuw."
            ) from exc

    async def insert(self, body: dict) -> dict:
        events = self._events()
        return dict(await self._call(events.insert, calendarId=self.calendar_id, body=body))

    async def patch(self, event_id: str, body: dict) -> dict:
        events = self._events()
        return dict(await self._call(events.patch, calendarId=self.calendar_id, eventId=event_id, body=body))

    async def get(self, event_id: str) -> dict | None:
        events = self._events()
        try:
            return dict(await self._call(events.get, calendarId=self.calendar_id, eventId=event_id))
        except Exception as exc:
            if _is_missing(exc):
                return None
            raise

    async def delete(self, event_id: str) -> bool:
        """Delete an event. A missing event counts as success."""
        events = self._events()
        try:
            await self._call(events.delete, calendarId=self.calendar_id, eventId=event_id)
            return True
        except Exception as exc:
            if _is_missing(exc):
                logger.debug("Google event was already gone; treating delete as success.", event_id=event_id)
                return True
            raise

    async def instances(self, event_id: str, time_min: str, time_max: str) -> list[dict]:
        events = self._events()
        result = await self._call(
            events.instances,
            calendarId=self.calendar_id,
            eventId=event_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=2500,
            showDeleted=False,
        )
        return list(result.get("items", []))

    async def list_synced(self, fp_type: str | None = None) -> list[dict]:
        """List events this app created, identified by their private fp_id property."""
        events = self._events()
        params: dict[str, Any] = {
            "calendarId": self.calendar_id,
            "maxResults": 2500,
            "singleEvents": False,
            "showDeleted": False,
            "privateExtendedProperty": f"fp_type={fp_type}" if fp_type else "fp_managed=1",
        }

        items: list[dict] = []
        page_token: str | None = None
        while True:
            if page_token:
                params["pageToken"] = page_token
            result = await self._call(events.list, **params)
            items.extend(result.get("items", []))
            page_token = result.get("nextPageToken")
            if not page_token:
                break
        return items

    async def list_all_events(self) -> list[dict]:
        """List every event in the configured calendar, including recurring parents."""
        events = self._events()
        params: dict[str, Any] = {
            "calendarId": self.calendar_id,
            "maxResults": 2500,
            "singleEvents": False,
            "showDeleted": False,
        }

        items: list[dict] = []
        page_token: str | None = None
        while True:
            if page_token:
                params["pageToken"] = page_token
            result = await self._call(events.list, **params)
            items.extend(result.get("items", []))
            page_token = result.get("nextPageToken")
            if not page_token:
                break
        return items

    async def verify(self) -> dict:
        """Round-trip check that credentials work and the calendar is writable."""
        events = self._events()
        result = await self._call(
            events.list,
            calendarId=self.calendar_id,
            maxResults=1,
            singleEvents=True,
        )
        return {"calendar_id": self.calendar_id, "summary": result.get("summary", "")}


def _is_missing(exc: Exception) -> bool:
    """True when Google reports the event as already deleted/absent."""
    status = getattr(getattr(exc, "resp", None), "status", None)
    return status in (404, 410)


def is_rate_limited(exc: Exception) -> bool:
    status = getattr(getattr(exc, "resp", None), "status", None)
    return status in (403, 429, 500, 502, 503, 504)
