"""Composición y arranque de la aplicación FastAPI.

``create_app`` permite inyectar settings y repositorios (para pruebas). Por
defecto usa repositorios EN MEMORIA, de modo que la API arranca sin Postgres
(útil para desarrollo local). El cableado con SQLAlchemy/Postgres es un
incremento posterior (requiere sesión por request).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .application.auth_service import AuthService
from .application.backtest_service import BacktestService
from .application.catalog_service import CatalogService
from .application.prediction_service import PredictionService
from .application.catalog_ports import CatalogRepository
from .application.player_service import PlayerService
from .application.populate_history import populate
from .application.prediction_history import PredictionHistoryRepository
from .application.ports import RefreshTokenRepository, UserRepository
from .application.security.password import Argon2PasswordHasher
from .application.security.tokens import TokenService
from .config import Settings
from .infrastructure.db.engine import (
    build_engine,
    build_inmemory_engine,
    build_session_factory,
)
from .infrastructure.db.prediction_repository import SqlAlchemyPredictionHistory
from .infrastructure.ingestion.snapshot import default_snapshot_path, load_snapshot
from .infrastructure.memory.catalog_repository import InMemoryCatalogRepository
from .infrastructure.providers.api_football import ApiFootballClient
from .infrastructure.memory.repositories import (
    InMemoryRefreshTokenRepository,
    InMemoryUserRepository,
)
from .interface.errors import register_exception_handlers
from .interface.rate_limit import FixedWindowRateLimiter
from .interface.routers import auth as auth_router
from .interface.routers import catalog as catalog_router
from .interface.routers import history as history_router
from .interface.routers import performance as performance_router
from .interface.routers import players as players_router
from .interface.routers import prediction as prediction_router
from .interface.routers import providers as providers_router


def create_app(
    *,
    settings: Settings | None = None,
    user_repo: UserRepository | None = None,
    refresh_repo: RefreshTokenRepository | None = None,
    catalog_repo: CatalogRepository | None = None,
    seed_ratings: dict[str, float] | None = None,
    seed_counts: dict[str, int] | None = None,
    history_repo: PredictionHistoryRepository | None = None,
) -> FastAPI:
    settings = settings or Settings()
    user_repo = user_repo or InMemoryUserRepository()
    refresh_repo = refresh_repo or InMemoryRefreshTokenRepository()
    # Por defecto: catálogo mock. El arranque real (módulo `app`) inyecta el
    # snapshot de datos reales si existe. Los tests usan el mock (sin argumento).
    catalog_repo = catalog_repo or InMemoryCatalogRepository.from_mock()
    # Historial: por defecto SQLite en memoria (tests). El app real usa archivo.
    if history_repo is None:
        engine = build_inmemory_engine()
        history_repo = SqlAlchemyPredictionHistory(build_session_factory(engine))
        history_repo.create_tables(engine)

    tokens = TokenService(
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        access_ttl_minutes=settings.jwt_access_ttl_min,
    )
    service = AuthService(
        users=user_repo,
        refresh_tokens=refresh_repo,
        hasher=Argon2PasswordHasher(),
        tokens=tokens,
        refresh_ttl_days=settings.jwt_refresh_ttl_days,
    )

    international = {c.code for c in catalog_repo.list_competitions() if c.is_international}
    catalog_service = CatalogService(catalog_repo)
    prediction_service = PredictionService(
        catalog_repo,
        seed_ratings=seed_ratings,
        seed_counts=seed_counts,
        international_competitions=international,
    )
    backtest_service = BacktestService(
        catalog_repo,
        seed_ratings=seed_ratings,
        seed_counts=seed_counts,
        international_competitions=international,
    )

    app = FastAPI(title="sports-predictor API", version="0.1.0")

    # Estado compartido leído por las dependencias.
    app.state.settings = settings
    app.state.user_repo = user_repo
    app.state.refresh_repo = refresh_repo
    app.state.token_service = tokens
    app.state.auth_service = service
    app.state.catalog_repo = catalog_repo
    app.state.catalog_service = catalog_service
    app.state.prediction_service = prediction_service
    app.state.backtest_service = backtest_service
    app.state.history_repo = history_repo
    # Proveedor de pago: se instancia solo si el usuario puso su API key en .env.
    api_football_client = (
        ApiFootballClient(settings.api_football_key) if settings.api_football_configured else None
    )
    app.state.api_football_client = api_football_client
    # Servicio de jugadores: requiere el proveedor de pago (datos por jugador).
    app.state.player_service = (
        PlayerService(api_football_client) if api_football_client is not None else None
    )
    app.state.login_limiter = FixedWindowRateLimiter(max_requests=10, window_seconds=60)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(auth_router.router)
    app.include_router(catalog_router.router)
    app.include_router(prediction_router.router)
    app.include_router(performance_router.router)
    app.include_router(providers_router.router)
    app.include_router(players_router.router)
    app.include_router(history_router.router)

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok", "env": settings.app_env}

    return app


def _build_app() -> FastAPI:
    """Arranca con datos reales (snapshot) si existe; si no, con mock.

    Usa una base de datos persistente (SQLite local por defecto, o Postgres vía
    DATABASE_URL) y puebla el historial de predicciones una sola vez.
    """
    settings = Settings()
    history_engine = build_engine(settings.database_url)
    history_repo = SqlAlchemyPredictionHistory(build_session_factory(history_engine))
    history_repo.create_tables(history_engine)

    try:
        path = default_snapshot_path()
        if path.exists():
            snap = load_snapshot(path)
            catalog_repo = InMemoryCatalogRepository(snap.competitions, snap.teams, snap.matches)
            app = create_app(
                settings=settings,
                catalog_repo=catalog_repo,
                seed_ratings=snap.seed_ratings,
                seed_counts=snap.seed_counts,
                history_repo=history_repo,
            )
        else:
            app = create_app(settings=settings, history_repo=history_repo)
    except Exception:  # noqa: BLE001 — ante cualquier problema, caer a mock
        app = create_app(settings=settings, history_repo=history_repo)

    # Poblar el historial (una vez, si está vacío) con los servicios ya construidos.
    try:
        n = populate(
            app.state.catalog_repo,
            app.state.backtest_service,
            app.state.prediction_service,
            history_repo,
        )
        if n:
            print(f"[historial] {n} predicciones guardadas.")
    except Exception as exc:  # noqa: BLE001 — el historial no debe tumbar el arranque
        print(f"[historial] no se pudo poblar: {exc}")

    return app


app = _build_app()

