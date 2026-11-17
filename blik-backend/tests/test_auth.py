from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings


def make_token(secret=None, **claims):
    payload = {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(minutes=5), **claims}
    return jwt.encode(payload, secret or settings.secret_key, algorithm="HS256")


def test_login_returns_token(client, staff_user):
    response = client.post(
        "/auth/login", data={"username": staff_user["email"], "password": staff_user["password"]}
    )
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_login_email_is_case_insensitive(client, staff_user):
    response = client.post(
        "/auth/login",
        data={"username": staff_user["email"].upper(), "password": staff_user["password"]},
    )
    assert response.status_code == 200


def test_wrong_password_and_unknown_email_look_the_same(client, staff_user):
    wrong_password = client.post(
        "/auth/login", data={"username": staff_user["email"], "password": "nope-nope-nope"}
    )
    unknown_email = client.post(
        "/auth/login", data={"username": "nobody@blik.test", "password": "nope-nope-nope"}
    )
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_login_is_rate_limited(client, staff_user, monkeypatch):
    monkeypatch.setattr(settings, "login_rate_limit_per_minute", 2)
    form = {"username": staff_user["email"], "password": "wrong-password"}
    assert client.post("/auth/login", data=form).status_code == 401
    assert client.post("/auth/login", data=form).status_code == 401
    assert client.post("/auth/login", data=form).status_code == 429


def test_staff_endpoints_require_a_token(client):
    assert client.get("/refills").status_code == 401
    assert client.patch("/refills/1", json={"status": "ready"}).status_code == 401


def test_garbage_token_rejected(client):
    response = client.get("/refills", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_expired_token_rejected(client, staff_user):
    expired = make_token(exp=datetime.now(timezone.utc) - timedelta(minutes=1))
    response = client.get("/refills", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401


def test_token_signed_with_wrong_key_rejected(client, staff_user):
    forged = make_token(secret="a-different-secret-key-that-is-long-enough-123")
    response = client.get("/refills", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


def test_token_for_deleted_staff_rejected(client, staff_user):
    token = make_token(sub="9999")  # no such staff id
    response = client.get("/refills", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_valid_token_is_accepted(client, auth_headers):
    assert client.get("/refills", headers=auth_headers).status_code == 200
