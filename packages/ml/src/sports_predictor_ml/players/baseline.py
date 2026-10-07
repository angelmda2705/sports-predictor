"""Predicción individual de jugadores: baseline minutos-primero + per-90.

Sigue el orden que pide la spec: primero estima TITULARIDAD y MINUTOS, y luego
escala las estadísticas por los minutos esperados (no proyecta 90' automáticamente).
Las tasas se calculan **per-90** (normalizadas por minutos), nunca acumuladas.

Es el baseline obligatorio (promedio reciente per-90, ponderado por recencia) contra
el que se compararán los modelos ML por posición. Python puro (stdlib).

⚠️ Requiere datos REALES por jugador (de un proveedor con stats de jugador, p. ej.
API-Football). Sin suficientes partidos, la predicción se marca de baja confianza.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime

# Mínimo de partidos para confianza plena; por debajo se advierte baja confianza.
_MIN_GAMES_FULL = 8
_RECENCY_HALF_LIFE = 5.0  # partidos: peso a la mitad cada ~5 juegos hacia atrás


@dataclass(frozen=True)
class PlayerGameLog:
    """Una actuación del jugador (normalizada). minutes=0 si no jugó."""

    kickoff: datetime
    started: bool
    minutes: int
    goals: int = 0
    assists: int = 0
    shots: int = 0
    shots_on: int = 0
    key_passes: int = 0


@dataclass(frozen=True)
class PlayerPrediction:
    n_games: int
    prob_start: float
    expected_minutes: float
    expected_goals: float
    expected_assists: float
    expected_shots: float
    expected_shots_on: float
    prob_scores: float  # P(al menos 1 gol)
    confidence: float
    confidence_band: str  # baja | media | alta
    low_confidence_note: str | None
    factors: list[str] = field(default_factory=list)


def _per90(weighted_stat: float, weighted_minutes: float) -> float:
    return (weighted_stat / weighted_minutes) * 90.0 if weighted_minutes > 0 else 0.0


def predict_player(logs: list[PlayerGameLog], *, recent_n: int = 15) -> PlayerPrediction:
    """Predice la próxima actuación a partir del historial reciente (per-90)."""
    if not logs:
        return PlayerPrediction(
            0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, "baja",
            "Sin historial: predicción no disponible.", [],
        )

    games = sorted(logs, key=lambda g: g.kickoff, reverse=True)[:recent_n]
    n = len(games)
    # Pesos por recencia (decaimiento exponencial: los partidos recientes pesan más).
    weights = [0.5 ** (i / _RECENCY_HALF_LIFE) for i in range(n)]
    w_total = sum(weights)

    prob_start = sum(w * (1.0 if g.started else 0.0) for w, g in zip(weights, games)) / w_total
    expected_minutes = sum(w * g.minutes for w, g in zip(weights, games)) / w_total

    w_minutes = sum(w * g.minutes for w, g in zip(weights, games))
    goals90 = _per90(sum(w * g.goals for w, g in zip(weights, games)), w_minutes)
    assists90 = _per90(sum(w * g.assists for w, g in zip(weights, games)), w_minutes)
    shots90 = _per90(sum(w * g.shots for w, g in zip(weights, games)), w_minutes)
    shots_on90 = _per90(sum(w * g.shots_on for w, g in zip(weights, games)), w_minutes)

    scale = expected_minutes / 90.0
    exp_goals = round(goals90 * scale, 3)
    exp_assists = round(assists90 * scale, 3)
    exp_shots = round(shots90 * scale, 2)
    exp_shots_on = round(shots_on90 * scale, 2)
    # P(>=1 gol) bajo Poisson con media = goles esperados.
    prob_scores = round(1.0 - math.exp(-exp_goals), 3)

    total_minutes = sum(g.minutes for g in games)
    data_quality = min(1.0, n / _MIN_GAMES_FULL) * min(1.0, total_minutes / 450.0)
    confidence = round(data_quality, 3)
    band = "alta" if confidence >= 0.66 else "media" if confidence >= 0.33 else "baja"

    note = None
    if n < 5 or expected_minutes < 30 or total_minutes < 200:
        note = (
            "Predicción de baja confianza por historial limitado, posible rotación o "
            "pocos minutos."
        )

    factors = [
        f"Titular en {sum(1 for g in games if g.started)} de los últimos {n} partidos.",
        f"Promedio reciente: {shots90:.1f} tiros/90, {goals90:.2f} goles/90.",
        f"Minutos esperados: {expected_minutes:.0f}.",
    ]

    return PlayerPrediction(
        n_games=n,
        prob_start=round(prob_start, 3),
        expected_minutes=round(expected_minutes, 1),
        expected_goals=exp_goals,
        expected_assists=exp_assists,
        expected_shots=exp_shots,
        expected_shots_on=exp_shots_on,
        prob_scores=prob_scores,
        confidence=confidence,
        confidence_band=band,
        low_confidence_note=note,
        factors=factors,
    )
