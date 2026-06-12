def test_automation_and_monitoring_paths(client, test_user):
    headers = test_user["headers"]

    status = client.get("/api/v1/automation/status", headers=headers)
    assert status.status_code == 200, status.text
    assert status.json()["status"] == "enabled"

    generated = client.post(
        "/api/v1/automation/generate-reminders?agenda_date=2026-06-06&lead_minutes=15",
        headers=headers,
    )
    assert generated.status_code == 200, generated.text
    assert "created_count" in generated.json()

    due = client.post("/api/v1/automation/run-due-reminders?limit=10", headers=headers)
    assert due.status_code == 200, due.text
    assert "processed_count" in due.json()

    health = client.get("/api/v1/monitoring/health")
    assert health.status_code == 200, health.text

    metrics = client.get("/api/v1/monitoring/metrics")
    assert metrics.status_code == 200, metrics.text
    assert "counts" in metrics.json()
