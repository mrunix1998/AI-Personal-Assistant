from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ExternalCalendarEvent:
    external_id: str
    title: str
    starts_at: datetime
    ends_at: datetime
    description: str | None = None
    location: str | None = None
    timezone: str | None = None


class CalendarProvider(ABC):
    provider_name: str

    @abstractmethod
    async def build_authorization_url(self, state: str) -> str:
        """Return provider OAuth authorization URL."""

    @abstractmethod
    async def exchange_code_for_tokens(self, code: str) -> dict:
        """Exchange OAuth code for access/refresh tokens."""

    @abstractmethod
    async def fetch_events(self, start: datetime, end: datetime) -> list[ExternalCalendarEvent]:
        """Fetch calendar events from provider."""
