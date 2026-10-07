"""Ingesta de datos REALES → snapshot de catálogo.

Uso (desde apps/api, con el venv):
    python -m scripts.ingest_real

Combina:
  - Premier League (3 temporadas reales) de openfootball.
  - Mundial 2026: fixtures/resultados reales de openfootball.
  - Siembra de ratings Elo de selecciones con el historial internacional REAL
    (martj42), para predecir los partidos del 2026 con datos de verdad.

Escribe db/snapshots/catalog.json. La API, al reiniciar, sirve estos datos reales.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.infrastructure.ingestion.international import fetch_world_cup_2026  # noqa: E402
from src.infrastructure.ingestion.openfootball import fetch_real_catalog  # noqa: E402
from src.infrastructure.ingestion.snapshot import write_snapshot  # noqa: E402


def main() -> None:
    print("1/2 · Premier League (openfootball)…")
    competitions, teams, matches = fetch_real_catalog()
    print(f"     {len(matches)} partidos de liga.")

    print("2/2 · Mundial 2026 + siembra de ratings internacionales (martj42)…")
    wc = fetch_world_cup_2026(start_match_id=len(matches))
    competitions.append(wc.competition)
    teams.extend(wc.teams)
    matches.extend(wc.matches)
    wc_finished = sum(1 for m in wc.matches if m.status.value == "finished")
    print(
        f"     Mundial 2026: {len(wc.matches)} partidos con selecciones reales "
        f"({wc_finished} jugados, {len(wc.matches) - wc_finished} por jugar). "
        f"Ratings sembrados: {len(wc.seed_ratings)} selecciones."
    )

    if not matches:
        print("⚠️ Sin partidos (¿problema de red?). No se escribió snapshot.")
        raise SystemExit(1)

    path = write_snapshot(
        competitions,
        teams,
        matches,
        source="openfootball+martj42",
        seed_ratings=wc.seed_ratings,
        seed_counts=wc.seed_counts,
    )
    print(f"Snapshot escrito en: {path}")


if __name__ == "__main__":
    main()
