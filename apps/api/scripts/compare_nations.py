"""Valida Dixon-Coles vs Elo para SELECCIONES (datos reales).

Ajusta ambos modelos con el historial internacional anterior al Mundial 2022 y los
compara prediciendo la fase de grupos REAL de Qatar 2022. Solo se promueve el
modelo si gana en Brier/LogLoss.

Uso (desde apps/api, con el venv): python -m scripts.compare_nations
"""

from __future__ import annotations

import csv
import io
import sys
from datetime import datetime
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

from src.infrastructure.ingestion.international import _INTL_URL, _fetch, _nation_code  # noqa: E402

TRAIN_FROM = "2018-01-01"
CUTOFF = "2022-11-20"  # inicio del Mundial 2022
GROUP_END = "2022-12-03"  # fin de la fase de grupos


def _outcome(hg: int, ag: int) -> str:
    return "H" if hg > ag else "D" if hg == ag else "A"


def main() -> None:
    rows = list(csv.DictReader(io.StringIO(_fetch(_INTL_URL, 60).decode("utf-8"))))

    def valid(r):
        return r["home_score"] != "" and r["away_score"] != ""

    train = [r for r in rows if TRAIN_FROM <= r["date"] < CUTOFF and valid(r)]
    test = [
        r
        for r in rows
        if r["tournament"] == "FIFA World Cup" and CUTOFF <= r["date"] < GROUP_END and valid(r)
    ]
    print(f"Entrenamiento: {len(train)} partidos internacionales | Prueba (grupos WC2022): {len(test)}")

    def dt(r):
        return datetime.fromisoformat(r["date"])

    print("Ajustando Elo...")
    elo = SoccerEloBaseline().fit(
        [
            MatchResult(_nation_code(r["home_team"]), _nation_code(r["away_team"]), dt(r),
                        int(r["home_score"]), int(r["away_score"]))
            for r in train
        ]
    )

    obs = [
        MatchObservation(_nation_code(r["home_team"]), _nation_code(r["away_team"]),
                         int(r["home_score"]), int(r["away_score"]), dt(r))
        for r in train
    ]

    def samples(model_predict):
        out = []
        for r in test:
            h, a = _nation_code(r["home_team"]), _nation_code(r["away_team"])
            actual = _outcome(int(r["home_score"]), int(r["away_score"]))
            p = model_predict(h, a)
            out.append(BacktestSample(p.prob_home, p.prob_draw, p.prob_away, actual, "na", "WC"))
        return out

    elo_s = samples(elo.predict)
    print(f"\n{'Modelo':<22}{'Accuracy':>10}{'Brier':>10}{'LogLoss':>10}")
    print("-" * 52)
    print(f"{'Elo sembrado':<22}{accuracy(elo_s):>10.4f}{brier_score(elo_s):>10.4f}{log_loss(elo_s):>10.4f}")

    best = ("Elo sembrado", brier_score(elo_s))
    for ridge in (0.001, 0.02, 0.05, 0.1, 0.2):
        print(f"  ajustando DC ridge={ridge}...", end="", flush=True)
        dc = DixonColesModel(half_life_days=540.0, ridge=ridge).fit(obs)
        s = samples(dc.predict)
        print("\r" + " " * 40 + "\r", end="")
        print(f"{'DC ridge=' + str(ridge):<22}{accuracy(s):>10.4f}{brier_score(s):>10.4f}{log_loss(s):>10.4f}")
        if brier_score(s) < best[1]:
            best = (f"DC ridge={ridge}", brier_score(s))

    print(f"\nMejor por Brier: {best[0]} ({best[1]:.4f})")


if __name__ == "__main__":
    main()
