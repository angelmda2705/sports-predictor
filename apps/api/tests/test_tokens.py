"""Pruebas del servicio de tokens (JWT de acceso + refresh opacos)."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from src.application.security.tokens import (
    TokenService,
    hash_refresh_token,
    new_refresh_token,
)
from src.domain.errors import InvalidToken
from src.domain.user import Plan, Role, User


def _user() -> User:
    return User(id=7, email="a@b.com", password_hash="x", role=Role.ANALYST, plan=Plan.PRO)


def test_access_token_round_trip() -> None:
    ts = TokenService(secret="s3cr3t", access_ttl_minutes=15)
    token = ts.create_access_token(_user())
    claims = ts.decode_access_token(token)
    assert claims["sub"] == "7"
    assert claims["role"] == "analyst"
    assert claims["plan"] == "pro"
    assert claims["type"] == "access"


def test_expired_token_rejected() -> None:
    ts = TokenService(secret="s3cr3t", access_ttl_minutes=-1)  # ya expirado
    token = ts.create_access_token(_user())
    with pytest.raises(InvalidToken):
        ts.decode_access_token(token)


def test_wrong_secret_rejected() -> None:
    issuer = TokenService(secret="secret-a")
    verifier = TokenService(secret="secret-b")
    token = issuer.create_access_token(_user())
    with pytest.raises(InvalidToken):
        verifier.decode_access_token(token)


def test_non_access_token_type_rejected() -> None:
    ts = TokenService(secret="s3cr3t")
    forged = jwt.encode(
        {"sub": "1", "type": "refresh", "exp": datetime.now(UTC) + timedelta(hours=1)},
        "s3cr3t",
        algorithm="HS256",
    )
    with pytest.raises(InvalidToken):
        ts.decode_access_token(forged)


def test_refresh_token_hash_is_deterministic_and_matches() -> None:
    raw, digest = new_refresh_token()
    assert digest == hash_refresh_token(raw)
    assert len(digest) == 64  # sha256 hex
    assert raw != digest
