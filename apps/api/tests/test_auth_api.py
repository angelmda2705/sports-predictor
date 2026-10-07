"""Pruebas de integración de los endpoints de auth (vía TestClient, repos en memoria)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _register(client: TestClient, email: str = "user@example.com", password: str = "password123"):
    return client.post("/auth/register", json={"email": email, "password": password})


def _login(client: TestClient, email: str = "user@example.com", password: str = "password123"):
    return client.post("/auth/login", json={"email": email, "password": password})


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_register_success(client: TestClient) -> None:
    r = _register(client)
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "user@example.com"
    assert body["role"] == "user"
    assert body["plan"] == "free"
    assert "password" not in body and "password_hash" not in body


def test_register_duplicate_conflict(client: TestClient) -> None:
    _register(client)
    r = _register(client)
    assert r.status_code == 409


def test_register_is_case_insensitive_on_email(client: TestClient) -> None:
    assert _register(client, email="User@Example.com").status_code == 201
    assert _register(client, email="user@example.com").status_code == 409


def test_register_weak_password_rejected(client: TestClient) -> None:
    r = _register(client, password="short")
    assert r.status_code == 422  # validación Pydantic (min_length=8)


def test_login_success_returns_tokens(client: TestClient) -> None:
    _register(client)
    r = _login(client)
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]
    assert body["expires_in"] > 0


def test_login_wrong_password_is_generic_401(client: TestClient) -> None:
    _register(client)
    r = _login(client, password="incorrect-password")
    assert r.status_code == 401
    wrong_detail = r.json()["detail"]
    # Mismo mensaje que con email inexistente (anti-enumeración).
    r2 = _login(client, email="nobody@example.com", password="whatever123")
    assert r2.status_code == 401
    assert r2.json()["detail"] == wrong_detail


def test_me_requires_token(client: TestClient) -> None:
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_me_returns_current_user(client: TestClient) -> None:
    _register(client)
    access = _login(client).json()["access_token"]
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 200
    assert r.json()["email"] == "user@example.com"


def test_refresh_rotates_repeatedly(client: TestClient) -> None:
    _register(client)
    r1 = _login(client).json()["refresh_token"]
    second = client.post("/auth/refresh", json={"refresh_token": r1})
    assert second.status_code == 200
    r2 = second.json()["refresh_token"]
    assert r2 != r1
    third = client.post("/auth/refresh", json={"refresh_token": r2})
    assert third.status_code == 200


def test_refresh_reuse_detection_revokes_chain(client: TestClient) -> None:
    _register(client)
    r1 = _login(client).json()["refresh_token"]
    r2 = client.post("/auth/refresh", json={"refresh_token": r1}).json()["refresh_token"]

    # Reusar r1 (ya rotado) debe fallar y revocar toda la cadena.
    reused = client.post("/auth/refresh", json={"refresh_token": r1})
    assert reused.status_code == 401

    # r2 también queda invalidado por la revocación de la cadena.
    assert client.post("/auth/refresh", json={"refresh_token": r2}).status_code == 401


def test_logout_revokes_refresh_token(client: TestClient) -> None:
    _register(client)
    refresh = _login(client).json()["refresh_token"]
    assert client.post("/auth/logout", json={"refresh_token": refresh}).status_code == 204
    assert client.post("/auth/refresh", json={"refresh_token": refresh}).status_code == 401


def test_rbac_admin_only(client: TestClient, seed_admin) -> None:
    # Usuario normal: 403 en endpoint de admin.
    _register(client)
    user_access = _login(client).json()["access_token"]
    forbidden = client.get(
        "/auth/admin/ping", headers={"Authorization": f"Bearer {user_access}"}
    )
    assert forbidden.status_code == 403

    # Admin sembrado: 200.
    email, password = seed_admin()
    admin_access = _login(client, email=email, password=password).json()["access_token"]
    ok = client.get("/auth/admin/ping", headers={"Authorization": f"Bearer {admin_access}"})
    assert ok.status_code == 200
    assert ok.json()["scope"] == "admin"
