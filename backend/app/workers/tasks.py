from app.workers.celery_app import celery_app


@celery_app.task(name="send_due_reminders")
def send_due_reminders() -> dict[str, str]:
    # MVP placeholder: next step will query pending reminders and send push notifications.
    return {"status": "not_implemented_yet"}
