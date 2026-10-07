"""Snapshots de catálogo: serializan un dataset ingerido a JSON inmutable.

Permiten reproducibilidad (un dataset fijo, datado) y arrancar la API sin pegarle
a la red en cada inicio. La ruta por defecto vive en ``db/snapshots/catalog.json``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ...domain.catalog import Competition, Match, MatchStatus, Sport, Team

_DEFAULT_REL = Path("db") / "snapshots" / "catalog.json"


def default_snapshot_path() -> Path:
    """Ruta por defecto del snapshot, relativa a la raíz del repo."""
    override = os.environ.get("CATALOG_SNAPSHOT")
    if override:
        return Path(override)
    # snapshot.py → ingestion → infrastructure → src → api → apps → sports-predictor
    repo_root = Path(__file__).resolve().parents[5]
    return repo_root / _DEFAULT_REL


def write_snapshot(
    competitions: list[Competition],
    teams: list[Team],
    matches: list[Match],
    *,
    source: str,
    seed_ratings: dict[str, float] | None = None,
    seed_counts: dict[str, int] | None = None,
    path: Path | None = None,
) -> Path:
    path = path or default_snapshot_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "snapshot_id": f"{source}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        "source": source,
        "generated_at": datetime.now(UTC).isoformat(),
        "is_mock": any(c.is_mock for c in competitions),
        # Ratings Elo de selecciones sembrados con historial internacional real.
        "seed_ratings": seed_ratings or {},
        "seed_counts": seed_counts or {},
        "competitions": [
            {
                "code": c.code,
                "name": c.name,
                "sport": c.sport.value,
                "country": c.country,
                "tier": c.tier,
                "is_mock": c.is_mock,
                "is_international": c.is_international,
            }
            for c in competitions
        ],
        "teams": [
            {
                "code": t.code,
                "name": t.name,
                "sport": t.sport.value,
                "short_name": t.short_name,
                "country": t.country,
                "is_mock": t.is_mock,
            }
            for t in teams
        ],
        "matches": [
            {
                "id": m.id,
                "sport": m.sport.value,
                "competition_code": m.competition_code,
                "season_label": m.season_label,
                "home_team_code": m.home_team.code,
                "away_team_code": m.away_team.code,
                "kickoff_utc": m.kickoff_utc.isoformat(),
                "status": m.status.value,
                "home_score": m.home_score,
                "away_score": m.away_score,
                "venue_name": m.venue_name,
                "stage": m.stage,
                "is_mock": m.is_mock,
            }
            for m in matches
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


@dataclass(frozen=True)
class LoadedSnapshot:
    competitions: list[Competition]
    teams: list[Team]
    matches: list[Match]
    seed_ratings: dict[str, float]
    seed_counts: dict[str, int]


def load_snapshot(path: Path | None = None) -> LoadedSnapshot:
    path = path or default_snapshot_path()
    payload = json.loads(path.read_text(encoding="utf-8"))

    competitions = [
        Competition(
            code=c["code"],
            name=c["name"],
            sport=Sport(c["sport"]),
            country=c["country"],
            tier=c["tier"],
            is_mock=c["is_mock"],
            is_international=c.get("is_international", False),
        )
        for c in payload["competitions"]
    ]
    teams = [
        Team(
            code=t["code"],
            name=t["name"],
            sport=Sport(t["sport"]),
            short_name=t["short_name"],
            country=t["country"],
            is_mock=t["is_mock"],
        )
        for t in payload["teams"]
    ]
    by_code = {t.code: t for t in teams}
    matches = [
        Match(
            id=m["id"],
            sport=Sport(m["sport"]),
            competition_code=m["competition_code"],
            season_label=m["season_label"],
            home_team=by_code[m["home_team_code"]],
            away_team=by_code[m["away_team_code"]],
            kickoff_utc=datetime.fromisoformat(m["kickoff_utc"]),
            status=MatchStatus(m["status"]),
            home_score=m["home_score"],
            away_score=m["away_score"],
            venue_name=m["venue_name"],
            stage=m["stage"],
            is_mock=m["is_mock"],
        )
        for m in payload["matches"]
    ]
    return LoadedSnapshot(
        competitions=competitions,
        teams=teams,
        matches=matches,
        seed_ratings={k: float(v) for k, v in payload.get("seed_ratings", {}).items()},
        seed_counts={k: int(v) for k, v in payload.get("seed_counts", {}).items()},
    )
