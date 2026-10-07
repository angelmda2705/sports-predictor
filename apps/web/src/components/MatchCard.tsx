import Link from "next/link";

import { STATUS_CLASS, STATUS_LABEL, formatKickoff } from "@/lib/format";
import type { Match } from "@/lib/types";

function TeamRow({ name, score, won }: { name: string; score: number | null; won: boolean }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className={won ? "font-semibold" : ""}>{name}</span>
      {score !== null && (
        <span className={`tabular-nums ${won ? "font-semibold" : ""}`}>{score}</span>
      )}
    </div>
  );
}

export function MatchCard({ match }: { match: Match }) {
  const finished = match.status === "finished";
  const homeWon = finished && (match.home_score ?? 0) > (match.away_score ?? 0);
  const awayWon = finished && (match.away_score ?? 0) > (match.home_score ?? 0);

  return (
    <Link
      href={`/matches/${match.id}`}
      className="block rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-brand-400 hover:shadow-md dark:border-slate-800 dark:bg-slate-900"
    >
      <div className="mb-3 flex items-center justify-between text-xs">
        <span className="rounded-full bg-slate-100 px-2 py-0.5 font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          {match.competition_code}
        </span>
        <span className={`rounded-full px-2 py-0.5 font-medium ${STATUS_CLASS[match.status]}`}>
          {STATUS_LABEL[match.status]}
        </span>
      </div>

      <div className="space-y-1 text-sm">
        <TeamRow name={match.home_team.name} score={match.home_score} won={homeWon} />
        <TeamRow name={match.away_team.name} score={match.away_score} won={awayWon} />
      </div>

      {match.stage && (
        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">{match.stage}</p>
      )}

      <div className="mt-3 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
        <span>{formatKickoff(match.kickoff_utc)}</span>
        {match.is_mock && (
          <span className="rounded bg-amber-100 px-1.5 py-0.5 font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
            mock
          </span>
        )}
      </div>

      {!finished && (
        <p className="mt-2 text-xs font-medium text-brand-600 dark:text-brand-400">
          Ver predicción del modelo →
        </p>
      )}
    </Link>
  );
}
