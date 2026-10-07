"""Cliente del proveedor de PAGO API-Football (api-sports.io, API v3).

Aporta lo que las fuentes abiertas no tienen: **alineaciones confirmadas** y
**lesiones** (lo que el usuario pidió para el contexto de rotaciones), además de
fixtures en vivo.

Seguridad: la API key se recibe por configuración (variable de entorno que pone el
usuario). Nunca se hardcodea ni se registra. Si no hay key, el proveedor no se
instancia (queda desactivado).

Las funciones de parseo (``parse_*``) son puras para poder probarlas con payloads
de ejemplo sin llamar a la red ni necesitar la key.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass

_BASE = "https://v3.football.api-sports.io"


class ApiFootballError(Exception):
    """Fallo al llamar a API-Football (red, autenticación o error de la API)."""


@dataclass(frozen=True)
class ProviderAccount:
    name: str | None
    email: str | None
    plan: str | None
    active: bool
    requests_today: int | None
    daily_limit: int | None


@dataclass(frozen=True)
class LineupPlayer:
    name: str
    number: int | None
    position: str | None


@dataclass(frozen=True)
class TeamLineup:
    team: str
    formation: str | None
    starters: list[LineupPlayer]


@dataclass(frozen=True)
class InjuryReport:
    player: str
    team: str
    reason: str | None


@dataclass(frozen=True)
class FixtureRef:
    """Referencia ligera a un partido (para construir el historial de un jugador)."""

    fixture_id: int
    kickoff: str  # ISO8601, p. ej. "2022-11-22T16:00:00+00:00"
    league: str
    season: int | None
    home: str
    away: str
    status: str | None  # "FT", "NS", "AET"...


@dataclass(frozen=True)
class PlayerMatchStats:
    """Estadísticas de un jugador en UN partido (materia prima del módulo de jugadores).

    Normalizable por minutos (per-90) para no comparar acumulados sin contexto.
    """

    player: str
    team: str
    minutes: int | None
    started: bool
    position: str | None
    rating: float | None
    goals: int
    assists: int
    shots: int
    shots_on: int
    key_passes: int
    passes: int
    pass_accuracy: float | None
    tackles: int
    interceptions: int


class ApiFootballClient:
    def __init__(self, api_key: str, *, timeout: int = 20) -> None:
        if not api_key:
            raise ValueError("Se requiere una API key de API-Football.")
        self._key = api_key
        self._timeout = timeout

    def _get(self, path: str, params: dict | None = None) -> dict:
        url = f"{_BASE}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(
            url, headers={"x-apisports-key": self._key, "Accept": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:  # noqa: S310
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise ApiFootballError(f"No se pudo llamar a API-Football: {exc}") from exc
        errors = data.get("errors")
        # API-Football devuelve {"errors": {...}} o {"errors": []} si todo va bien.
        if isinstance(errors, dict) and errors:
            raise ApiFootballError(f"API-Football devolvió errores: {errors}")
        return data

    # --- Llamadas en vivo (requieren key válida) ---------------------------
    def account_status(self) -> ProviderAccount:
        return self.parse_account(self._get("/status"))

    def lineups(self, fixture_id: int) -> list[TeamLineup]:
        return self.parse_lineups(self._get("/fixtures/lineups", {"fixture": fixture_id}))

    def injuries(self, fixture_id: int) -> list[InjuryReport]:
        return self.parse_injuries(self._get("/injuries", {"fixture": fixture_id}))

    def find_team_id(self, name: str, *, national: bool | None = None) -> int | None:
        """Busca el id de un equipo por nombre. national=True restringe a selecciones."""
        data = self._get("/teams", {"search": name})
        candidates = []
        for entry in data.get("response", []) or []:
            team = entry.get("team") or {}
            if national is not None and bool(team.get("national")) != national:
                continue
            candidates.append(team)
        # Coincidencia exacta primero; si no, el primer candidato.
        for team in candidates:
            if (team.get("name") or "").lower() == name.lower():
                return team.get("id")
        return candidates[0].get("id") if candidates else None

    def team_fixtures(self, team_id: int, season: int, *, league: int | None = None) -> list[FixtureRef]:
        """Partidos de un equipo en una temporada (filtro por season, NO por `last`).

        El plan Free bloquea el parámetro `last`, por eso se filtra por temporada
        (y opcionalmente por liga, p. ej. league=1 = Copa del Mundo).
        """
        params: dict = {"team": team_id, "season": season}
        if league is not None:
            params["league"] = league
        return self.parse_fixtures(self._get("/fixtures", params))

    def find_fixture_id(self, *, date: str, home: str, away: str, league: int, season: int) -> int | None:
        """Busca el fixture de API-Football que corresponde a nuestro partido."""
        data = self._get("/fixtures", {"date": date, "league": league, "season": season})
        for fx in data.get("response", []):
            teams = fx.get("teams", {})
            h = (teams.get("home") or {}).get("name", "")
            a = (teams.get("away") or {}).get("name", "")
            if home.lower() in h.lower() and away.lower() in a.lower():
                return (fx.get("fixture") or {}).get("id")
        return None

    # --- Parsing puro (testeable con payloads de ejemplo) ------------------
    @staticmethod
    def parse_account(payload: dict) -> ProviderAccount:
        r = payload.get("response", {}) or {}
        account = r.get("account", {}) or {}
        sub = r.get("subscription", {}) or {}
        reqs = r.get("requests", {}) or {}
        name = " ".join(x for x in (account.get("firstname"), account.get("lastname")) if x) or None
        return ProviderAccount(
            name=name,
            email=account.get("email"),
            plan=sub.get("plan"),
            active=bool(sub.get("active")),
            requests_today=reqs.get("current"),
            daily_limit=reqs.get("limit_day"),
        )

    @staticmethod
    def parse_lineups(payload: dict) -> list[TeamLineup]:
        out: list[TeamLineup] = []
        for team_block in payload.get("response", []) or []:
            team = (team_block.get("team") or {}).get("name", "?")
            starters = []
            for entry in team_block.get("startXI", []) or []:
                p = entry.get("player", {}) or {}
                starters.append(
                    LineupPlayer(
                        name=p.get("name", "?"),
                        number=p.get("number"),
                        position=p.get("pos"),
                    )
                )
            out.append(TeamLineup(team=team, formation=team_block.get("formation"), starters=starters))
        return out

    @staticmethod
    def parse_fixtures(payload: dict) -> list[FixtureRef]:
        out: list[FixtureRef] = []
        for fx in payload.get("response", []) or []:
            fixture = fx.get("fixture") or {}
            league = fx.get("league") or {}
            teams = fx.get("teams") or {}
            status = (fixture.get("status") or {}).get("short")
            out.append(
                FixtureRef(
                    fixture_id=fixture.get("id"),
                    kickoff=fixture.get("date", ""),
                    league=league.get("name", "?"),
                    season=league.get("season"),
                    home=(teams.get("home") or {}).get("name", "?"),
                    away=(teams.get("away") or {}).get("name", "?"),
                    status=status,
                )
            )
        return out

    @staticmethod
    def parse_injuries(payload: dict) -> list[InjuryReport]:
        out: list[InjuryReport] = []
        for entry in payload.get("response", []) or []:
            player = (entry.get("player") or {}).get("name", "?")
            team = (entry.get("team") or {}).get("name", "?")
            reason = (entry.get("player") or {}).get("reason") or entry.get("reason")
            out.append(InjuryReport(player=player, team=team, reason=reason))
        return out

    def fixture_player_stats(self, fixture_id: int) -> list[PlayerMatchStats]:
        """Estadísticas de cada jugador en un partido (/fixtures/players)."""
        return self.parse_fixture_players(self._get("/fixtures/players", {"fixture": fixture_id}))

    @staticmethod
    def parse_fixture_players(payload: dict) -> list[PlayerMatchStats]:
        def _i(value) -> int:
            return int(value) if isinstance(value, (int, float)) else 0

        def _f(value) -> float | None:
            try:
                return float(value) if value not in (None, "") else None
            except (TypeError, ValueError):
                return None

        out: list[PlayerMatchStats] = []
        for team_block in payload.get("response", []) or []:
            team = (team_block.get("team") or {}).get("name", "?")
            for entry in team_block.get("players", []) or []:
                p = entry.get("player", {}) or {}
                stats = (entry.get("statistics") or [{}])[0] or {}
                games = stats.get("games") or {}
                shots = stats.get("shots") or {}
                goals = stats.get("goals") or {}
                passes = stats.get("passes") or {}
                tackles = stats.get("tackles") or {}
                out.append(
                    PlayerMatchStats(
                        player=p.get("name", "?"),
                        team=team,
                        minutes=games.get("minutes"),
                        started=not bool(games.get("substitute")),
                        position=games.get("position"),
                        rating=_f(games.get("rating")),
                        goals=_i(goals.get("total")),
                        assists=_i(goals.get("assists")),
                        shots=_i(shots.get("total")),
                        shots_on=_i(shots.get("on")),
                        key_passes=_i(passes.get("key")),
                        passes=_i(passes.get("total")),
                        pass_accuracy=_f(passes.get("accuracy")),
                        tackles=_i(tackles.get("total")),
                        interceptions=_i(tackles.get("interceptions")),
                    )
                )
        return out
