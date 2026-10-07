"""Dependencias de FastAPI: autenticación de la petición, RBAC y rate limiting.

Los componentes (servicio de auth, servicio de tokens, repos, limitador) se
guardan en ``app.state`` durante el arranque (ver ``main.create_app``) y se leen
aquí. Esto mantiene los handlers desacoplados del wiring concreto.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..application.auth_service import AuthService
from ..application.backtest_service import BacktestService
from ..application.catalog_service import CatalogService
from ..application.prediction_service import PredictionService
from ..application.security.tokens import TokenService
from ..domain.errors import InvalidToken
from ..domain.user import Role, User

_bearer = HTTPBearer(auto_error=False)


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


def get_catalog_service(request: Request) -> CatalogService:
    return request.app.state.catalog_service


def get_prediction_service(request: Request) -> PredictionService:
    return request.app.state.prediction_service


def get_backtest_service(request: Request) -> BacktestService:
    return request.app.state.backtest_service


def get_token_service(request: Request) -> TokenService:
    return request.app.state.token_service


def enforce_login_rate_limit(request: Request) -> None:
    """Protege endpoints de auth contra fuerza bruta (clave = IP del cliente)."""
    limiter = request.app.state.login_limiter
    client_ip = request.client.host if request.client else "unknown"
    if not limiter.allow(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos. Intenta de nuevo más tarde.",
        )


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    tokens: TokenService = request.app.state.token_service
    user_repo = request.app.state.user_repo
    try:
        claims = tokens.decode_access_token(credentials.credentials)
        user_id = int(str(claims["sub"]))
    except (InvalidToken, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = user_repo.get_by_id(user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no disponible.",
        )
    return user


def require_roles(*roles: Role) -> Callable[..., User]:
    """Crea una dependencia que exige que el usuario tenga uno de los roles dados."""

    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para esta operación.",
            )
        return user

    return _checker
