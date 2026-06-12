from datetime import datetime
import httpx
from app.schemas.tasks import TaskCreate

class JiraService:
    def __init__(self, base_url: str, email: str, api_token: str, jql: str):
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.api_token = api_token
        self.jql = jql

    async def fetch_tasks(self) -> list[TaskCreate]:
        url = f"{self.base_url}/rest/api/3/search"
        params = {"jql": self.jql, "fields": "summary,duedate,priority,status", "maxResults": 50}
        async with httpx.AsyncClient(timeout=30, auth=(self.email, self.api_token)) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        tasks: list[TaskCreate] = []
        for issue in data.get("issues", []):
            fields = issue.get("fields", {})
            due = fields.get("duedate")
            due_at = None
            if due:
                try:
                    due_at = datetime.fromisoformat(due)
                except ValueError:
                    due_at = None
            key = issue.get("key")
            tasks.append(TaskCreate(
                provider_name="jira",
                external_task_id=f"jira:{issue.get('id') or key}",
                title=f"{key} {fields.get('summary', '')}".strip(),
                due_at=due_at,
                priority=(fields.get("priority") or {}).get("name", "medium"),
                url=f"{self.base_url}/browse/{key}" if key else None,
            ))
        return tasks
