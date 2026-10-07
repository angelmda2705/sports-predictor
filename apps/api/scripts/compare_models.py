"""Comparación honesta Elo vs Dixon-Coles (validación temporal walk-forward).

Backtest sobre la Premier League real: entrena con temporadas previas y predice la
2023-24 jornada por jornada (point-in-time). Reporta Brier/LogLoss/Accuracy de cada
modelo + el baseline ingenuo. Solo se promueve un modelo si REALMENTE gana.

Uso (desde apps/api, con el venv que tiene numpy/scipy):
    python -m scripts.compare_models
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sports_predictor_ml.evaluation.metrics import (  # noqa: E402
    BacktestSample,
    accuracy,
    brier_score,
    log_loss,
)
from sports_predictor_ml.models.soccer.dixon_coles import (  # noqa: E402
    DixonColesModel,
    MatchObservation,
)
from sports_predictor_ml.prediction.soccer_baseline import (  # noqa: E402
    MatchResult,
    SoccerEloBaseline,
)

from src.infrastructure.ingestion.snapshot import load_snapshot  # noqa: E402

TEST_SEASON = "2023-24"


def _outcome(hg: int, ag: int) -> str:
    return "H" if hg > ag else "D" if hg == ag else "A"


def main() -> None:
    snap = load_snapshot()
    pl = [
        m
        for m in snap.matches
        if m.competition_code == "ENG_PL"
        and m.home_score is not None
        and m.away_score is not None
    ]
    pl.sort(key=lambda m: m.kickoff_utc)
    test = [m for m in pl if m.season_label == TEST_SEASON]
    print(f"PL total={len(pl)} | entrenamiento previo + walk-forward sobre {TEST_SEASON} ({len(test)} partidos)")

    test_ids = {m.id for m in test}

    # --- Elo: single-pass walk-forward (predice antes de actualizar) ---
    elo = SoccerEloBaseline()
    elo_probs: dict[int, tuple[float, float, float]] = {}
    for m in pl:
        if m.id in test_ids:
            p = elo.predict(m.home_team.code, m.away_team.code)
            elo_probs[m.id] = (p.prob_home, p.prob_draw, p.prob_away)
        elo.fit([
            MatchResult(m.home_team.code, m.away_team.code, m.kickoff_utc, m.home_score, m.away_score)
        ])

    # --- Dixon-Coles: reentrena por jornada con todo lo anterior ---
    dc_probs: dict[int, tuple[float, float, float]] = {}
    by_round: dict[str, list] = {}
    for m in test:
        by_round.setdefault(m.stage or "?", []).append(m)
    rounds = sorted(by_round.values(), key=lambda g: min(x.kickoff_utc for x in g))
    for i, group in enumerate(rounds, 1):
        cutoff = min(x.kickoff_utc for x in group)
        train = [m for m in pl if m.kickoff_utc < cutoff]
        model = DixonColesModel(half_life_days=180.0).fit([
            MatchObservation(m.home_team.code, m.away_team.code, m.home_score, m.away_score, m.kickoff_utc)
            for m in train
        ])
        for m in group:
            p = model.predict(m.home_team.code, m.away_team.code)
            dc_probs[m.id] = (p.prob_home, p.prob_draw, p.prob_away)
        print(f"  jornada {i}/{len(rounds)} reentrenada (train={len(train)})", end="\r")
    print()

    def samples(probs: dict[int, tuple[float, float, float]]) -> list[BacktestSample]:
        out = []
        for m in test:
            ph, pd, pa = probs[m.id]
            out.append(BacktestSample(ph, pd, pa, _outcome(m.home_score, m.away_score), "na", "ENG_PL"))
        return out

    elo_s = samples(elo_probs)
    dc_s = samples(dc_probs)

    print(f"\n{'Modelo':<16}{'Accuracy':>10}{'Brier':>10}{'LogLoss':>10}")
    print("-" * 46)
    for name, s in (("Elo", elo_s), ("Dixon-Coles", dc_s)):
        print(f"{name:<16}{accuracy(s):>10.4f}{brier_score(s):>10.4f}{log_loss(s):>10.4f}")

    # Veredicto honesto: menor Brier = mejores probabilidades.
    print()
    if brier_score(dc_s) < brier_score(elo_s):
        print(f"[OK] Dixon-Coles MEJORA el Brier ({brier_score(dc_s):.4f} < {brier_score(elo_s):.4f}).")
    else:
        print(f"[--] Dixon-Coles NO mejora el Brier ({brier_score(dc_s):.4f} >= {brier_score(elo_s):.4f}).")


if __name__ == "__main__":
    main()
