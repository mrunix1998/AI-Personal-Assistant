from app.integrations.calendars.google import GoogleCalendarProvider
from app.models.enums import ProviderName


def get_calendar_provider(provider_name: ProviderName, access_token: str | None = None):
    if provider_name == ProviderName.GOOGLE_CALENDAR:
        return GoogleCalendarProvider(access_token=access_token)
    raise ValueError(f"Unsupported calendar provider: {provider_name}")
