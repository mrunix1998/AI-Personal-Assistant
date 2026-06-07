from enum import StrEnum


class ProviderType(StrEnum):
    CALENDAR = "calendar"
    TASK_MANAGER = "task_manager"


class ProviderName(StrEnum):
    GOOGLE_CALENDAR = "google_calendar"
    MICROSOFT_CALENDAR = "microsoft_calendar"
    APPLE_CALENDAR = "apple_calendar"
    CALDAV = "caldav"
    LOCAL_TASKS = "local_tasks"
    TODOIST = "todoist"
    MICROSOFT_TODO = "microsoft_todo"
    NOTION = "notion"
    TRELLO = "trello"
    ASANA = "asana"


class ReminderStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    CANCELLED = "cancelled"
