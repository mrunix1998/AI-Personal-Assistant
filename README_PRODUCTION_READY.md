# AI Personal Assistant — Production Ready Update

This update keeps the project structure from the uploaded ZIP and adds the missing production automation layer.

## Included phases

1. **Celery Worker + Celery Beat + Reminder Engine**
   - `worker` service in `docker-compose.yml`
   - `scheduler` service in `docker-compose.yml`
   - Celery app: `backend/app/workers/celery_app.py`
   - Celery tasks: `backend/app/workers/tasks.py`
   - Reminder engine: `backend/app/services/reminder_engine.py`

2. **Telegram + Email Reminders**
   - Direct Telegram Bot API delivery
   - Direct SMTP delivery
   - Shared delivery service: `backend/app/services/notification_delivery_service.py`

3. **Daily Agenda Scheduler**
   - Celery Beat runs daily agenda at 07:00 Europe/Berlin
   - Manual and queued endpoints under `/api/v1/automation/*`

4. **Frontend Controls + Notification History**
   - New sidebar tabs: `automation`, `monitoring`
   - Manual controls for generate reminders, run due reminders, send daily agenda, and queue Celery jobs

5. **Monitoring + Health Checks + Backup**
   - `/api/v1/monitoring/health`
   - `/api/v1/monitoring/readiness`
   - `/api/v1/monitoring/metrics`
   - DB backup script: `./scripts/backup_postgres.sh`

## Run

```bash
cp backend/.env.example backend/.env
# Fill SECRET_KEY, TOKEN_ENCRYPTION_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET if needed

docker compose up --build -d
```

## Verify

```bash
./scripts/production_readiness_check.sh
```

## Test manually

1. Login in frontend.
2. Connect Google Calendar and sync.
3. Save Telegram bot token + chat id, then Send test.
4. Save Email SMTP config, then Send test.
5. Go to Automation tab:
   - Generate reminders
   - Run due reminders now
   - Send daily agenda now
6. Go to Monitoring tab and refresh.

## Backup

```bash
./scripts/backup_postgres.sh
```
