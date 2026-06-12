import httpx
from app.core.config import get_settings
class N8nWorkflowService:
    def __init__(self): self.base=get_settings().n8n_base_url.rstrip('/')
    async def trigger(self, path: str, payload: dict):
        async with httpx.AsyncClient(timeout=30) as client:
            r=await client.post(f"{self.base}/webhook/{path}", json=payload)
            r.raise_for_status(); return r.json()
    async def telegram_daily(self, payload: dict): return await self.trigger("telegram-daily-agenda", payload)
    async def email_daily(self, payload: dict): return await self.trigger("email-daily-agenda", payload)
