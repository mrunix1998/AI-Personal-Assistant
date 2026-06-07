from datetime import date
from typing import Any
from uuid import UUID

import httpx

from app.core.config import get_settings


class N8nWorkflowService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def trigger_daily_summary_workflow(
        self,
        *,
        user_id: UUID,
        user_email: str,
        agenda_date: date,
        access_token: str,
    ) -> Any:
        url = f"{self.settings.n8n_base_url.rstrip('/')}/{self.settings.n8n_daily_summary_webhook_path.lstrip('/')}"
        payload = {
            "event": "daily_summary_requested",
            "user_id": str(user_id),
            "user_email": user_email,
            "agenda_date": agenda_date.isoformat(),
            "backend_base_url": "http://backend:8000",
        }
        headers = {
            "X-N8N-Webhook-Secret": self.settings.n8n_webhook_secret,
            # This lets n8n call protected backend endpoints during local development.
            # In production, replace this with a short-lived service token or internal auth.
            "Authorization": f"Bearer {access_token}",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                return response.json()
            return response.text

    async def trigger_ai_planning_workflow(
        self,
        *,
        user_id: UUID,
        user_email: str,
        agenda_date: date,
        access_token: str,
        planning_context: dict,
    ) -> Any:
        url = f"{self.settings.n8n_base_url.rstrip('/')}/{self.settings.n8n_ai_planning_webhook_path.lstrip('/')}"
        payload = {
            "event": "ai_planning_requested",
            "user_id": str(user_id),
            "user_email": user_email,
            "agenda_date": agenda_date.isoformat(),
            "backend_base_url": "http://backend:8000",
            "planning_context": planning_context,
        }
        headers = {
            "X-N8N-Webhook-Secret": self.settings.n8n_webhook_secret,
            "Authorization": f"Bearer {access_token}",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                return response.json()
            return {"raw_response": response.text}
    async def trigger_unified_agenda_workflow(
        self,
        *,
        user_id: UUID,
        user_email: str,
        agenda_date: date,
        access_token: str,
        unified_agenda: dict,
    ) -> Any:
        url = f"{self.settings.n8n_base_url.rstrip('/')}/{self.settings.n8n_unified_agenda_webhook_path.lstrip('/')}"
        payload = {
            "event": "unified_agenda_requested",
            "user_id": str(user_id),
            "user_email": user_email,
            "agenda_date": agenda_date.isoformat(),
            "backend_base_url": "http://backend:8000",
            "unified_agenda": unified_agenda,
        }
        headers = {
            "X-N8N-Webhook-Secret": self.settings.n8n_webhook_secret,
            "Authorization": f"Bearer {access_token}",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                return response.json()
            return {"raw_response": response.text}

