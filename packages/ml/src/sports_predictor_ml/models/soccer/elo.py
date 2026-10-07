"""Modelo Elo baseline para fútbol soccer.

Elo es el baseline obligatorio: barato, robusto e interpretable. Cualquier modelo
más complejo debe DEMOSTRAR que lo supera en validación temporal y calibración
antes de promoverse (ver estrategia de ML en el documento técnico).

Mapeo a probabilidades 1X2
--------------------------
A partir de la diferencia de rating (con ventaja de localía) se obtiene la
"cuota esperada de puntos" del local, ``expected ∈ [0, 1]``, que corresponde a
``p_home + 0.5 * p_draw`` (victoria=1, empate=0.5, derrota=0).

Para separar el empate se usa un modelo de empate paramétrico que alcanza su
máximo cuando los equipos están parejos (``expected = 0.5``) y tiende a 0 en los
extremos::

    p_draw = draw_max * (1 - 2 * |expected - 0.5|)
    p_home = expected - 0.5 * p_draw
    p_away = (1 - expected) - 0.5 * p_draw

Por construcción ``p_home + p_draw + p_away = 1``. Es un baseline deliberadamente
simple; la calibración fina del empate llega con Dixon-Coles en Fase 2.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EloConfig:
    """Parámetros del modelo Elo.

    Attributes:
        k: factor de actualización (cuánto se mueve el rating por partido).
        home_advantage: ventaja de localía en puntos Elo.
        base_rating: rating inicial de un equipo sin historia.
        draw_max: probabilidad de empate cuando los equipos están parejos.
    """

    k: float = 20.0
    home_advantage: float = 60.0
    base_rating: float = 1500.0
    draw_max: float = 0.30

    def __post_init__(self) -> None:
        if not 0.0 <= self.draw_max < 1.0:
            raise ValueError("draw_max debe estar en [0, 1).")
        if self.k <= 0:
            raise ValueError("k debe ser positivo.")


@dataclass
class EloModel:
    """Sistema de rating Elo con estado mutable de ratings por equipo."""

    config: EloConfig = field(default_factory=EloConfig)
    ratings: dict[str, float] = field(default_factory=dict)

    def get_rating(self, team: str) -> float:
        """Rating actual del equipo (``base_rating`` si no tiene historia)."""
        return self.ratings.get(team, self.config.base_rating)

    def expected_score(self, home_team: str, away_team: str) -> float:
        """Cuota esperada de puntos del local en ``[0, 1]``.

        Equivale a ``p_home + 0.5 * p_draw``. Incluye la ventaja de localía.
        """
        diff = self.get_rating(home_team) + self.config.home_advantage - self.get_rating(away_team)
        return 1.0 / (1.0 + 10.0 ** (-diff / 400.0))

    def match_probabilities(self, home_team: str, away_team: str) -> tuple[float, float, float]:
        """Probabilidades ``(p_home, p_draw, p_away)`` que suman 1."""
        expected = self.expected_score(home_team, away_team)
        p_draw = self.config.draw_max * (1.0 - 2.0 * abs(expected - 0.5))
        p_home = expected - 0.5 * p_draw
        p_away = (1.0 - expected) - 0.5 * p_draw
        # Clamp defensivo ante errores de coma flotante; renormaliza para sumar 1.
        p_home, p_draw, p_away = (max(0.0, p) for p in (p_home, p_draw, p_away))
        total = p_home + p_draw + p_away
        return (p_home / total, p_draw / total, p_away / total)

    def update(
        self, home_team: str, away_team: str, home_goals: int, away_goals: int
    ) -> tuple[float, float]:
        """Actualiza los ratings tras un resultado y devuelve ``(nuevo_local, nuevo_visita)``.

        La actualización es de suma cero: lo que gana un equipo lo pierde el otro.
        """
        if home_goals > away_goals:
            actual = 1.0
        elif home_goals == away_goals:
            actual = 0.5
        else:
            actual = 0.0

        expected = self.expected_score(home_team, away_team)
        delta = self.config.k * (actual - expected)

        new_home = self.get_rating(home_team) + delta
        new_away = self.get_rating(away_team) - delta
        self.ratings[home_team] = new_home
        self.ratings[away_team] = new_away
        return new_home, new_away
