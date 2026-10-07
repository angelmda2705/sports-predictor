"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { MockBanner } from "@/components/MockBanner";
import { PredictionPanel } from "@/components/PredictionPanel";
import { ApiError, apiFetch } from "@/lib/api";
import { SPORT_LABEL, STATUS_CLASS, STATUS_LABEL, formatKickoff } from "@/lib/format";
import type { Match } from "@/lib/types";

export default function MatchDetailPage({ params }: { params: { id: string } }) {
  const [match, setMatch] = useState<Match | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    apiFetch<Match>(`/matches/${params.id}`)
      .then((m) => active && setMatch(m))
      .catch((e: unknown) => {
        if (!active) return;
        setError(
          e instanceof ApiError && e.status === 404
            ? "Partido no encontrado."
            : "No se pudo cargar el partido.",
        );
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [params.id]);

  return (
    <div className="space-y-6">
      <Link href="/" className="text-sm text-brand-600 hover:underline">
        ← Volver a partidos
      </Link>

      {loading && <div className="h-40 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-900" />}

      {error && (
        <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
          {error}
        </div>
      )}

      {match && (
        <>
          {match.is_mock && <MockBanner />}

          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="mb-4 flex items-center justify-between text-xs">
              <span className="rounded-full bg-slate-100 px-2 py-0.5 font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                {match.competition_code} · {SPORT_LABEL[match.sport]}
              </span>
              <span
                className={`rounded-full px-2 py-0.5 font-medium ${STATUS_CLASS[match.status]}`}
              >
                {STATUS_LABEL[match.status]}
              </span>
            </div>

            <div className="grid grid-cols-3 items-center gap-2 text-center">
              <div className="font-semibold">{match.home_team.name}</div>
              <div className="text-2xl font-bold tabular-nums">
                {match.status === "finished"
                  ? `${match.home_score} – ${match.away_score}`
                  : "vs"}
              </div>
              <div className="font-semibold">{match.away_team.name}</div>
            </div>

            <dl className="mt-6 grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-slate-500 dark:text-slate-400">Fecha</dt>
                <dd>{formatKickoff(match.kickoff_utc)}</dd>
              </div>
              <div>
                <dt className="text-slate-500 dark:text-slate-400">Estadio</dt>
                <dd>{match.venue_name ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-slate-500 dark:text-slate-400">Temporada</dt>
                <dd>{match.season_label}</dd>
              </div>
              {match.stage && (
                <div>
                  <dt className="text-slate-500 dark:text-slate-400">Fase</dt>
                  <dd>{match.stage}</dd>
                </div>
              )}
            </dl>
          </div>

          <PredictionPanel
            matchId={match.id}
            homeName={match.home_team.name}
            awayName={match.away_team.name}
          />
        </>
      )}
    </div>
  );
}
