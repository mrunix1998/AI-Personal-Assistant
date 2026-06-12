def test_notification_center_daily_agenda_and_read_flow(client, test_user):
    headers = test_user["headers"]

    created = client.post(
        "/api/v1/notifications/center/daily-agenda?agenda_date=2026-06-06",
        headers=headers,
    )
    assert created.status_code in (200, 201), created.text
    notification = created.json()["notification"]
    notification_id = notification["id"]
    assert notification["status"] == "unread"

    listing = client.get("/api/v1/notifications/center", headers=headers)
    assert listing.status_code == 200, listing.text
    assert any(n["id"] == notification_id for n in listing.json())

    read = client.post(f"/api/v1/notifications/center/{notification_id}/read", headers=headers)
    assert read.status_code == 200, read.text
    assert read.json()["status"] == "read"

    read_all = client.post("/api/v1/notifications/center/read-all", headers=headers)
    assert read_all.status_code == 200, read_all.text
    assert "updated_count" in read_all.json()
