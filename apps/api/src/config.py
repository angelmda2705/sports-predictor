"""Configuración de la API vía variables de entorno (pydantic-settings).

Los secretos NUNCA se hardcodean: se leen de entorno. El valor por defecto de
``jwt_secret`` solo sirve para desarrollo/tests y debe sobreescribirse en producción.
"""

from __future__ import annotations

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_DEFAULT_SECRET = "dev-only-insecure-secret-change-me"
_MIN_PROD_SECRET_BYTES = 32  # RFC 7518: clave HMAC-SHA256 >= 32 bytes


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"

    # Seguridad / Auth
    jwt_secret: str = _DEV_DEFAULT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_min: int = 15
    jwt_refresh_ttl_days: int = 7

    @model_validator(mode="after")
    def _enforce_strong_secret_in_production(self) -> Settings:
        """Impide desplegar en producción con el secreto de desarrollo o uno débil."""
        if self.app_env == "production":
            if self.jwt_secret == _DEV_DEFAULT_SECRET:
                raise ValueError(
                    "JWT_SECRET no puede ser el valor por defecto de desarrollo en producción."
                )
            if len(self.jwt_secret.encode("utf-8")) < _MIN_PROD_SECRET_BYTES:
                raise ValueError(
                    f"JWT_SECRET debe tener al menos {_MIN_PROD_SECRET_BYTES} bytes en producción."
                )
        return self

    # CORS (lista separada por comas)
    cors_allowed_origins: str = "http://localhost:3000"

    # Base de datos (producción). En dev/tests se usan repos en memoria.
    database_url: str | None = None

    # Proveedor de pago API-Football (api-sports.io). La clave la pone el usuario
    # en su .env; nunca se hardcodea. Si está vacía, el proveedor queda desactivado.
    api_football_key: str | None = None

    @property
    def api_football_configured(self) -> bool:
        return bool(self.api_football_key)

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]
