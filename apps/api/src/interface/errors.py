"""Manejo centralizado de errores: mapea errores de dominio a respuestas HTTP."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from ..domain.errors import (
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidToken,
    UserNotFound,
)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(EmailAlreadyRegistered)
    async def _email_taken(_: Request, exc: EmailAlreadyRegistered) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)}
        )

    @app.exception_handler(InvalidCredentials)
    async def _bad_creds(_: Request, exc: InvalidCredentials) -> JSONResponse:
        # 401 genérico: no revela si el email existe (anti-enumeración).
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": str(exc)}
        )

    @app.exception_handler(InvalidToken)
    async def _bad_token(_: Request, exc: InvalidToken) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": str(exc)}
        )

    @app.exception_handler(UserNotFound)
    async def _no_user(_: Request, exc: UserNotFound) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": str(exc)}
        )
