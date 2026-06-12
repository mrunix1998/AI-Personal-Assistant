def test_web_push_subscription_crud(client, test_user):
    headers = test_user["headers"]
    payload = {
        "endpoint": "https://example.com/fake-push-endpoint-test",
        "p256dh": "fake-p256dh-key",
        "auth": "fake-auth-key",
        "user_agent": "pytest",
    }
    created = client.post("/api/v1/notifications/web-push/subscriptions", headers=headers, json=payload)
    assert created.status_code in (200, 201), created.text
    sub_id = created.json()["id"]

    listing = client.get("/api/v1/notifications/web-push/subscriptions", headers=headers)
    assert listing.status_code == 200, listing.text
    assert any(s["id"] == sub_id for s in listing.json())

    deleted = client.delete(f"/api/v1/notifications/web-push/subscriptions/{sub_id}", headers=headers)
    assert deleted.status_code in (200, 204), deleted.text
