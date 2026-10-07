"""Puerto (interfaz) de proveedores de datos deportivos y DTOs de transporte.

Este módulo define el contrato que TODO proveedor debe cumplir. El resto del
sistema programa contra `SportsDataProvider`, nunca contra una implementación
concreta. Así se cumple la regla de la capa de abstracción: cambiar de proveedor
no debe requerir modificar el dominio ni el pipeline.

Cada DTO incluye el campo ``is_mock``. Los datos de prueba SIEMPRE viajan con
``is_mock=True`` para que puedan etiquetarse en la base de datos y en la UI, y
nunca se confundan con datos reales (regla obligatoria del producto).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class TeamDTO:
    """Equipo tal como lo entrega un proveedor, antes de la estandarización canónica."""

    provider_ref: str
    name: str
    short_name: str | None = None
    country: str | None = None
    is_mock: bool = False


@dataclass(frozen=True)
class MatchDTO:
    """Partido (fixture o resultado) entregado por un proveedor.

    ``home_score``/``away_score`` son ``None`` mientras el partido no haya
    terminado. El pipeline NUNCA debe usar el marcador de un partido como
    variable predictiva de ese mismo partido (anti-fuga, ver ``features``).
    """

    provider_ref: str
    competition_ref: str
    season_label: str
    home_team_ref: str
    away_team_ref: str
    kickoff_utc: datetime
    status: str  # "scheduled" | "live" | "finished" | "postponed"
    home_score: int | None = None
    away_score: int | None = None
    venue_name: str | None = None
    is_mock: bool = False


@dataclass(frozen=True)
class InjuryDTO:
    """Reporte de lesión/suspensión. ``reported_at`` es clave para el anti-fuga:
    una lesión solo puede usarse como feature de un partido si fue reportada
    ANTES del kickoff de ese partido."""

    player_ref: str
    team_ref: str
    status: str  # "out" | "doubtful" | "questionable" | "suspended"
    reported_at: datetime
    source: str | None = None
    is_mock: bool = False


@dataclass(frozen=True)
class ProviderMetadata:
    """Identidad y características de un proveedor, para trazabilidad/observabilidad."""

    name: str
    requires_api_key: bool
    is_mock: bool = False
    supported_sports: tuple[str, ...] = field(default_factory=tuple)


@runtime_checkable
class SportsDataProvider(Protocol):
    """Puerto que todo proveedor de datos deportivos debe implementar.

    Las implementaciones reales harán llamadas HTTP a APIs externas; la
    implementación de prueba (`MockSportsDataProvider`) devuelve datos en
    memoria claramente etiquetados con ``is_mock=True``.
    """

    def metadata(self) -> ProviderMetadata:
        """Devuelve la identidad/capacidades del proveedor."""
        ...

    def fetch_teams(self, competition_ref: str, season_label: str) -> list[TeamDTO]:
        """Equipos participantes en una competición/temporada."""
        ...

    def fetch_matches(self, competition_ref: str, season_label: str) -> list[MatchDTO]:
        """Partidos (históricos y programados) de una competición/temporada."""
        ...

    def fetch_injuries(self, competition_ref: str, season_label: str) -> list[InjuryDTO]:
        """Reportes de lesiones/suspensiones disponibles."""
        ...
