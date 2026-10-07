"""Pruebas de la guarda de secretos en configuración."""

import pytest

from src.config import Settings


def test_dev_default_secret_allowed_in_development() -> None:
    s = Settings(app_env="development")
    assert s.jwt_secret  # el default de dev es válido fuera de producción


def test_production_rejects_dev_default_secret() -> None:
    with pytest.raises(ValueError):
        Settings(app_env="production")  # usa el secreto por defecto


def test_production_rejects_short_secret() -> None:
    with pytest.raises(ValueError):
        Settings(app_env="production", jwt_secret="too-short")


def test_production_accepts_strong_secret() -> None:
    strong = "x" * 48
    s = Settings(app_env="production", jwt_secret=strong)
    assert s.jwt_secret == strong
