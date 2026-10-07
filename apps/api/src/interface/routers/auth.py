"""Endpoints de autenticación."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from ...application.auth_service import AuthService
from ...domain.user import Role, User
from ..deps import (
    enforce_login_rate_limit,
    get_auth_service,
    get_current_user,
    require_roles,
)
from ..schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_login_rate_limit)],
)
def register(
    body: RegisterRequest, service: AuthService = Depends(get_auth_service)
) -> UserResponse:
    user = service.register(email=body.email, password=body.password)
    return UserResponse(
        id=user.id,  # type: ignore[arg-type]
        email=user.email,
        role=user.role,
        plan=user.plan,
        email_verified=user.email_verified,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(enforce_login_rate_limit)],
)
def login(body: LoginRequest, service: AuthService = Depends(get_auth_service)) -> TokenResponse:
    pair = service.login(email=body.email, password=body.password)
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    body: RefreshRequest, service: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    pair = service.refresh(refresh_token=body.refresh_token)
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(body: LogoutRequest, service: AuthService = Depends(get_auth_service)) -> Response:
    service.logout(refresh_token=body.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        id=user.id,  # type: ignore[arg-type]
        email=user.email,
        role=user.role,
        plan=user.plan,
        email_verified=user.email_verified,
    )


@router.get("/admin/ping", tags=["admin"])
def admin_ping(_: User = Depends(require_roles(Role.ADMIN))) -> dict[str, str]:
    """Endpoint de ejemplo protegido por RBAC: solo administradores."""
    return {"status": "ok", "scope": "admin"}
