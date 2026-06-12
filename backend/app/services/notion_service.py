from datetime import datetime
import httpx
from app.schemas.tasks import TaskCreate

class NotionService:
    def __init__(self, token: str, database_id: str):
        self.token = token
        self.database_id = database_id
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }

    async def fetch_tasks(self) -> list[TaskCreate]:
        url = f"https://api.notion.com/v1/databases/{self.database_id}/query"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=self.headers, json={})
            response.raise_for_status()
            data = response.json()
        tasks: list[TaskCreate] = []
        for page in data.get("results", []):
            props = page.get("properties", {})
            title = self._title(props) or "Untitled Notion task"
            due_at = self._date(props)
            status_text = self._status(props)
            if status_text and status_text.lower() in {"done", "complete", "completed"}:
                continue
            tasks.append(TaskCreate(
                provider_name="notion",
                external_task_id=f"notion:{page.get('id')}",
                title=title,
                due_at=due_at,
                priority=self._priority(props),
                url=page.get("url"),
            ))
        return tasks

    def _title(self, props: dict) -> str | None:
        for value in props.values():
            if value.get("type") == "title":
                return "".join([x.get("plain_text", "") for x in value.get("title", [])]).strip() or None
        return None

    def _date(self, props: dict):
        for value in props.values():
            if value.get("type") == "date" and value.get("date") and value["date"].get("start"):
                raw = value["date"]["start"]
                try:
                    return datetime.fromisoformat(raw.replace("Z", "+00:00"))
                except ValueError:
                    return None
        return None

    def _priority(self, props: dict) -> str | None:
        for key, value in props.items():
            if key.lower() == "priority" and value.get("type") in {"select", "status"}:
                selected = value.get(value["type"])
                if selected:
                    return selected.get("name")
        return "medium"

    def _status(self, props: dict) -> str | None:
        for key, value in props.items():
            if key.lower() == "status" and value.get("type") in {"select", "status"}:
                selected = value.get(value["type"])
                if selected:
                    return selected.get("name")
        return None
