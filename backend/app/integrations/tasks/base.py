from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ExternalTaskItem:
    external_id: str
    title: str
    due_at: datetime | None = None
    notes: str | None = None
    is_completed: bool = False


class TaskProvider(ABC):
    provider_name: str

    @abstractmethod
    async def build_authorization_url(self, state: str) -> str:
        """Return provider OAuth authorization URL."""

    @abstractmethod
    async def exchange_code_for_tokens(self, code: str) -> dict:
        """Exchange OAuth code for access/refresh tokens."""

    @abstractmethod
    async def fetch_tasks(self) -> list[ExternalTaskItem]:
        """Fetch task items from provider."""
