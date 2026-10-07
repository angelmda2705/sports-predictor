"""Pruebas del hashing de contraseñas (Argon2id)."""

from src.application.security.password import Argon2PasswordHasher


def test_hash_is_not_plaintext() -> None:
    hasher = Argon2PasswordHasher()
    h = hasher.hash("super-secret-123")
    assert h != "super-secret-123"
    assert h.startswith("$argon2")


def test_verify_correct_password() -> None:
    hasher = Argon2PasswordHasher()
    h = hasher.hash("super-secret-123")
    assert hasher.verify("super-secret-123", h) is True


def test_verify_wrong_password() -> None:
    hasher = Argon2PasswordHasher()
    h = hasher.hash("super-secret-123")
    assert hasher.verify("wrong-password", h) is False


def test_verify_invalid_hash_returns_false() -> None:
    hasher = Argon2PasswordHasher()
    assert hasher.verify("whatever", "not-a-valid-hash") is False


def test_same_password_distinct_hashes_due_to_salt() -> None:
    hasher = Argon2PasswordHasher()
    assert hasher.hash("same-password") != hasher.hash("same-password")
