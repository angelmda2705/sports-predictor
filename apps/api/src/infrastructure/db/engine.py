"""Motor y sesión de base de datos.

Por defecto usa **SQLite local** (archivo en disco, persiste entre reinicios, sin
instalar nada). En producción, definir ``DATABASE_URL`` (p. ej. Postgres) y el mismo
código funciona sin cambios.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def default_sqlite_path() -> Path:
    # engine.py → db → infrastructure → src → api → apps → sports-predictor
    repo_root = Path(__file__).resolve().parents[5]
    return repo_root / "db" / "sports_predictor.db"


def build_engine(database_url: str | None = None) -> Engine:
    if database_url:
        url = database_url
    else:
        path = default_sqlite_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{path.as_posix()}"
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, future=True)


def build_inmemory_engine() -> Engine:
    """SQLite en memoria compartida (para tests y como default sin tocar disco)."""
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)
