def test_create_task_and_unified_daily_agenda(client, test_user):
    headers = test_user["headers"]
    task_payload = {
        "title": "Prepare production readiness checklist",
        "due_at": "2026-06-06T15:00:00Z",
    }
    created = client.post("/api/v1/tasks", headers=headers, json=task_payload)
    assert created.status_code in (200, 201), created.text
    assert created.json()["title"] == task_payload["title"]

    tasks = client.get("/api/v1/tasks", headers=headers)
    assert tasks.status_code == 200, tasks.text
    assert any(t["title"] == task_payload["title"] for t in tasks.json())

    agenda = client.get("/api/v1/agenda/unified-daily?agenda_date=2026-06-06", headers=headers)
    assert agenda.status_code == 200, agenda.text
    body = agenda.json()
    assert body["date"] == "2026-06-06"
    assert body["stats"]["task_count"] >= 1
    assert any(t["title"] == task_payload["title"] for t in body["tasks"])
