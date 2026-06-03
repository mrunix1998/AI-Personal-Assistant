# AI Personal Assistant

A cloud-native personal assistant that connects to calendars and task managers, builds a daily agenda, and sends smart reminders.

## MVP Scope

- Python/FastAPI backend
- PostgreSQL database
- Redis/Celery worker foundation
- Multi-provider integration layer
- Google Calendar OAuth foundation
- Daily agenda endpoint

## Local Development

```bash
cd ai-personal-assistant
cp backend/.env.example backend/.env
docker compose up --build
```

Health check:

```bash
curl http://localhost:8000/api/v1/health
```

Daily agenda endpoint example:

```bash
curl "http://localhost:8000/api/v1/agenda/daily?user_id=<USER_UUID>&agenda_date=2026-06-03"
```

## Provider Strategy

Calendar providers and task providers are implemented through adapters. This lets us add Google Calendar, Microsoft Calendar, Apple/CalDAV, Todoist, Notion, Trello, Asana, and others without changing the core app design.
