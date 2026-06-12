import os
import time
import uuid

import httpx
import pytest


BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8000")


def wait_for_api(timeout_seconds: int = 30) -> None:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            response = httpx.get(f"{BASE_URL}/api/v1/health", timeout=2)
            if response.status_code < 500:
                return
        except Exception as exc:  # pragma: no cover
            last_error = exc
        time.sleep(1)
    raise RuntimeError(f"API did not become ready at {BASE_URL}: {last_error}")


@pytest.fixture(scope="session", autouse=True)
def api_ready() -> None:
    wait_for_api()


@pytest.fixture()
def client() -> httpx.Client:
    with httpx.Client(base_url=BASE_URL, timeout=10) as c:
        yield c


@pytest.fixture()
def test_user(client: httpx.Client) -> dict:
    unique = uuid.uuid4().hex[:10]
    email = f"test-{unique}@example.com"
    password = "StrongPass123!"
    payload = {"email": email, "password": password, "full_name": "Test User"}
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code in (200, 201), response.text
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return {"email": email, "password": password, "token": token, "headers": {"Authorization": f"Bearer {token}"}}
