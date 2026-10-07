"""Modelo Dixon-Coles (Poisson bivariado) para fútbol soccer.

Modela los GOLES (no solo quién gana). Cada equipo tiene una fuerza ofensiva
(attack) y defensiva (defense); hay una ventaja de localía global y un parámetro
rho que corrige la dependencia en marcadores bajos (0-0, 1-0, 0-1, 1-1), el aporte
clásico de Dixon & Coles (1997).

    λ_local   = exp(attack_local + defense_visita + ventaja_local)
    μ_visita  = exp(attack_visita + defense_local)
    P(x,y)    = τ(x,y) · Poisson(x; λ) · Poisson(y; μ)

Se ajusta por máxima verosimilitud (scipy L-BFGS-B), con decaimiento temporal
opcional (los partidos recientes pesan más). De la matriz de marcadores se derivan
1X2, goles esperados, Over/Under y BTTS.

Requiere numpy/scipy (extra [pipeline] de packages/ml).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np
from scipy.optimize import minimize
from scipy.stats import poisson


@dataclass(frozen=True)
class DixonColesPrediction:
    prob_home: float
    prob_draw: float
    prob_away: float
    exp_home_goals: float
    exp_away_goals: float
    likely_scoreline: str
    # Probabilidad de "más de" cada línea de goles totales: ((línea, p_over), ...).
    over_under: tuple[tuple[float, float], ...]
    prob_btts: float  # ambos anotan


# Líneas de goles totales para Over/Under.
OVER_UNDER_LINES: tuple[float, ...] = (0.5, 1.5, 2.5, 3.5, 4.5)


@dataclass(frozen=True)
class MatchObservation:
    home: str
    away: str
    home_goals: int
    away_goals: int
    kickoff: datetime


def _tau_vec(hg, ag, lam, mu, rho):
    """Corrección Dixon-Coles para marcadores bajos (vectorizada)."""
    tau = np.ones_like(lam)
    m00 = (hg == 0) & (ag == 0)
    m01 = (hg == 0) & (ag == 1)
    m10 = (hg == 1) & (ag == 0)
    m11 = (hg == 1) & (ag == 1)
    tau[m00] = 1.0 - lam[m00] * mu[m00] * rho
    tau[m01] = 1.0 + lam[m01] * rho
    tau[m10] = 1.0 + mu[m10] * rho
    tau[m11] = 1.0 - rho
    return np.clip(tau, 1e-10, None)


class DixonColesModel:
    def __init__(
        self,
        *,
        max_goals: int = 10,
        half_life_days: float | None = 180.0,
        ridge: float = 1e-3,
    ):
        self.max_goals = max_goals
        self.half_life_days = half_life_days
        # Regularización L2 sobre ataque/defensa: encoge hacia el promedio de la
        # liga. Valores altos = más conservador (útil con datos dispersos).
        self.ridge = ridge
        self._teams: list[str] = []
        self._idx: dict[str, int] = {}
        self._attack: dict[str, float] = {}
        self._defense: dict[str, float] = {}
        self._home_adv: float = 0.0
        self._rho: float = 0.0

    def fit(self, matches: list[MatchObservation]) -> DixonColesModel:
        if not matches:
            return self
        teams = sorted({m.home for m in matches} | {m.away for m in matches})
        self._teams = teams
        self._idx = {t: i for i, t in enumerate(teams)}
        n = len(teams)

        home_idx = np.array([self._idx[m.home] for m in matches])
        away_idx = np.array([self._idx[m.away] for m in matches])
        hg = np.array([m.home_goals for m in matches], dtype=float)
        ag = np.array([m.away_goals for m in matches], dtype=float)

        # Pesos por decaimiento temporal (half-life): partidos recientes pesan más.
        if self.half_life_days:
            latest = max(m.kickoff for m in matches)
            age_days = np.array([(latest - m.kickoff).days for m in matches], dtype=float)
            weights = 0.5 ** (age_days / self.half_life_days)
        else:
            weights = np.ones(len(matches))

        def neg_log_lik(params: np.ndarray) -> float:
            attack = params[:n]
            defense = params[n : 2 * n]
            home_adv = params[2 * n]
            rho = params[2 * n + 1]
            lam = np.exp(attack[home_idx] + defense[away_idx] + home_adv)
            mu = np.exp(attack[away_idx] + defense[home_idx])
            tau = _tau_vec(hg, ag, lam, mu, rho)
            ll = weights * (np.log(tau) + poisson.logpmf(hg, lam) + poisson.logpmf(ag, mu))
            # Identificabilidad: ancla la media de attack a 0; ridge encoge fuerzas.
            penalty = 1e3 * attack.mean() ** 2 + self.ridge * (attack @ attack + defense @ defense)
            return -ll.sum() + penalty

        x0 = np.concatenate([np.zeros(n), np.zeros(n), [0.25], [-0.05]])
        bounds = [(-3, 3)] * (2 * n) + [(-1, 2), (-0.2, 0.2)]
        res = minimize(neg_log_lik, x0, method="L-BFGS-B", bounds=bounds)

        attack = res.x[:n]
        defense = res.x[n : 2 * n]
        self._attack = {t: float(attack[i]) for t, i in self._idx.items()}
        self._defense = {t: float(defense[i]) for t, i in self._idx.items()}
        self._home_adv = float(res.x[2 * n])
        self._rho = float(res.x[2 * n + 1])
        return self

    def strength(self, team: str) -> tuple[float, float]:
        """(ataque, defensa) ajustados del equipo. Ataque mayor = más goles a favor;
        defensa menor = menos goles en contra."""
        return self._attack.get(team, 0.0), self._defense.get(team, 0.0)

    @property
    def home_advantage(self) -> float:
        return self._home_adv

    def _lambdas(self, home: str, away: str) -> tuple[float, float]:
        # Equipos sin historial → fuerza media (0).
        ah = self._attack.get(home, 0.0)
        dh = self._defense.get(home, 0.0)
        aa = self._attack.get(away, 0.0)
        da = self._defense.get(away, 0.0)
        lam = float(np.exp(ah + da + self._home_adv))
        mu = float(np.exp(aa + dh))
        return lam, mu

    def predict(self, home: str, away: str) -> DixonColesPrediction:
        lam, mu = self._lambdas(home, away)
        g = np.arange(self.max_goals + 1)
        p_home_goals = poisson.pmf(g, lam)
        p_away_goals = poisson.pmf(g, mu)
        matrix = np.outer(p_home_goals, p_away_goals)
        # Corrección DC en los cuatro marcadores bajos.
        matrix[0, 0] *= 1.0 - lam * mu * self._rho
        matrix[0, 1] *= 1.0 + lam * self._rho
        matrix[1, 0] *= 1.0 + mu * self._rho
        matrix[1, 1] *= 1.0 - self._rho
        matrix = np.clip(matrix, 0.0, None)
        matrix /= matrix.sum()

        idx = np.indices(matrix.shape)
        home_i, away_j = idx[0], idx[1]
        total = home_i + away_j
        p_home = float(matrix[home_i > away_j].sum())
        p_draw = float(np.trace(matrix))
        p_away = float(matrix[home_i < away_j].sum())
        btts = float(matrix[(home_i >= 1) & (away_j >= 1)].sum())

        # P(más de L) = P(total >= L+0.5 redondeado hacia arriba) para cada línea.
        over_under = tuple(
            (line, round(float(matrix[total >= int(line) + 1].sum()), 4))
            for line in OVER_UNDER_LINES
        )

        ij = np.unravel_index(np.argmax(matrix), matrix.shape)
        return DixonColesPrediction(
            prob_home=round(p_home, 4),
            prob_draw=round(p_draw, 4),
            prob_away=round(p_away, 4),
            exp_home_goals=round(lam, 2),
            exp_away_goals=round(mu, 2),
            likely_scoreline=f"{ij[0]}-{ij[1]}",
            over_under=over_under,
            prob_btts=round(btts, 4),
        )
