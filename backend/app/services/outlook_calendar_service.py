from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException

from app.core.config import get_settings

MICROSOFT_AUTH_BASE = "https://login.microsoftonline.com"
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
SCOPES = "offline_access User.Read Calendars.Read"


class OutlookCalendarService:
    def build_authorization_url(self, *, state: str) -> str:
        settings = get_settings()
        tenant = getattr(settings, "microsoft_tenant_id", "common") or "common"
        params = {
            "client_id": settings.microsoft_client_id,
            "response_type": "code",
            "redirect_uri": settings.microsoft_redirect_uri,
            "response_mode": "query",
            "scope": SCOPES,
            "state": state,
            "prompt": "select_account",
        }
        return f"{MICROSOFT_AUTH_BASE}/{tenant}/oauth2/v2.0/authorize?{urlencode(params)}"

    async def exchange_code(self, *, code: str) -> dict[str, Any]:
        settings = get_settings()
        tenant = getattr(settings, "microsoft_tenant_id", "common") or "common"
        url = f"{MICROSOFT_AUTH_BASE}/{tenant}/oauth2/v2.0/token"
        data = {
            "client_id": settings.microsoft_client_id,
            "client_secret": settings.microsoft_client_secret,
            "code": code,
            "redirect_uri": settings.microsoft_redirect_uri,
            "grant_type": "authorization_code",
            "scope": SCOPES,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, data=data)
        if response.status_code >= 400:
            raise HTTPException(status_code=400, detail=f"Microsoft token exchange failed: {response.text}")
        return response.json()

    async def refresh_access_token(self, *, refresh_token: str) -> dict[str, Any]:
        settings = get_settings()
        tenant = getattr(settings, "microsoft_tenant_id", "common") or "common"
        url = f"{MICROSOFT_AUTH_BASE}/{tenant}/oauth2/v2.0/token"
        data = {
            "client_id": settings.microsoft_client_id,
            "client_secret": settings.microsoft_client_secret,
            "refresh_token": refresh_token,
            "redirect_uri": settings.microsoft_redirect_uri,
            "grant_type": "refresh_token",
            "scope": SCOPES,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, data=data)
        if response.status_code >= 400:
            raise HTTPException(status_code=400, detail=f"Microsoft token refresh failed: {response.text}")
        return response.json()

    async def me(self, *, access_token: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{GRAPH_BASE}/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        response.raise_for_status()
        return response.json()

    async def calendar_events(self, *, access_token: str, days_back: int = 30, days_forward: int = 30) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=days_back)
        end = now + timedelta(days=days_forward)
        params = {
            "startDateTime": start.isoformat(),
            "endDateTime": end.isoformat(),
            "$orderby": "start/dateTime",
            "$top": "100",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{GRAPH_BASE}/me/calendarView",
                headers={"Authorization": f"Bearer {access_token}", "Prefer": 'outlook.timezone="UTC"'},
                params=params,
            )
        response.raise_for_status()
        raw_events = response.json().get("value", [])
        return [self._normalize_event(event) for event in raw_events]

    def _normalize_event(self, event: dict[str, Any]) -> dict[str, Any]:
        start_raw = event.get("start", {}).get("dateTime")
        end_raw = event.get("end", {}).get("dateTime")
        starts_at = datetime.fromisoformat(start_raw.replace("Z", "+00:00")) if start_raw else datetime.now(timezone.utc)
        ends_at = datetime.fromisoformat(end_raw.replace("Z", "+00:00")) if end_raw else starts_at
        return {
            "external_event_id": event.get("id"),
            "title": event.get("subject") or "Untitled Outlook event",
            "description": event.get("bodyPreview"),
            "location": event.get("location", {}).get("displayName"),
            "starts_at": starts_at,
            "ends_at": ends_at,
            "timezone": event.get("start", {}).get("timeZone") or "UTC",
        }
