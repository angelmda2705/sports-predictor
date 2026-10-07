"use client";

import { useEffect, useState } from "react";

import { ApiError, apiFetch } from "@/lib/api";
import type { Prediction } from "@/lib/types";

const BAND_CLASS: Record<string, string> = {
  baja: "bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  media: "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300",
  alta: "bg-brand-100 text-brand-700 dark:bg-brand-700/30 dark:text-brand-400",
};

function ProbBar({ label, value, accent }: { label: string; value: number; accent: string }) {
  const pct = Math.round(value * 100);
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-sm">
        <span>{label}</span>
        <span className="font-semibold tabular-nums">{pct}%</span>
      </div>
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
        <div className={`h-full rounded-full ${accent}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function PredictionPanel({
  matchId,
  homeName,
  awayName,
}: {
  matchId: number;
  homeName: string;
  awayName: string;
}) {
  const [pred, setPred] = useState<Prediction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    setUnavailable(null);
    apiFetch<Prediction>(`/matches/${matchId}/prediction`)
      .then((p) => active && setPred(p))
      .catch((e: unknown) => {
        if (!active) return;
        if (e instanceof ApiError && e.status === 422) setUnavailable(e.message);
        else setError("No se pudo cargar la predicción.");
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [matchId]);

  if (loading) {
    return <div className="h-48 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-900" />;
  }

  if (unavailable) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-900/50 dark:text-slate-400">
        <h2 className="mb-1 font-semibold text-slate-700 dark:text-slate-200">
          Predicción del modelo
        </h2>
        {unavailable}
      </div>
    );
  }

  if (error || !pred) {
    return (
      <div className="rounded-xl border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
        {error ?? "Sin predicción."}
      </div>
    );
  }

  return (
    <div className="space-y-5 rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-bold">Predicción del modelo</h2>
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          {pred.model.name} v{pred.model.version}
        </span>
      </div>

      {/* Advertencias de contexto (p. ej. selección ya clasificada) */}
      {pred.context.length > 0 && (
        <div className="space-y-2 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-700/60 dark:bg-amber-900/20 dark:text-amber-200">
          {pred.context.map((c, i) => (
            <p key={i}>
              <strong>⚠ Contexto:</strong> {c.message}
            </p>
          ))}
        </div>
      )}

      {/* Probabilidades 1X2 */}
      <div className="space-y-3">
        <ProbBar label={`Gana ${homeName}`} value={pred.probabilities.home} accent="bg-brand-500" />
        <ProbBar label="Empate" value={pred.probabilities.draw} accent="bg-slate-400" />
        <ProbBar label={`Gana ${awayName}`} value={pred.probabilities.away} accent="bg-sky-500" />
      </div>

      {/* Marcador esperado + confianza */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800/50">
          <div className="text-slate-500 dark:text-slate-400">Marcador esperado</div>
          <div className="text-lg font-semibold tabular-nums">
            {pred.expected_goals.home} – {pred.expected_goals.away}
          </div>
          <div className="text-xs text-slate-500 dark:text-slate-400">
            más probable: {pred.likely_scoreline}
          </div>
        </div>
        <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800/50">
          <div className="text-slate-500 dark:text-slate-400">Nivel de confianza</div>
          <div className="mt-0.5">
            <span
              className={`rounded-full px-2 py-0.5 text-sm font-semibold capitalize ${BAND_CLASS[pred.confidence.band]}`}
            >
              {pred.confidence.band}
            </span>
            <span className="ml-2 text-xs tabular-nums text-slate-500 dark:text-slate-400">
              ({pred.confidence.score})
            </span>
          </div>
          <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            datos: {pred.history_counts.home}/{pred.history_counts.away} partidos previos
          </div>
        </div>
      </div>

      {/* Mercados derivados (solo Dixon-Coles) */}
      {pred.markets.over_under.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-semibold">Goles totales (Over / Under)</h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 dark:text-slate-400">
                <th className="pb-1 font-medium">Línea</th>
                <th className="pb-1 font-medium tabular-nums">Más de</th>
                <th className="pb-1 font-medium tabular-nums">Menos de</th>
              </tr>
            </thead>
            <tbody>
              {pred.markets.over_under.map((ou) => (
                <tr key={ou.line} className="border-t border-slate-100 dark:border-slate-800">
                  <td className="py-1.5">{ou.line.toFixed(1)}</td>
                  <td className="py-1.5 tabular-nums">{Math.round(ou.over * 100)}%</td>
                  <td className="py-1.5 tabular-nums">{Math.round(ou.under * 100)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
          {pred.markets.btts !== null && (
            <p className="mt-2 text-sm">
              Ambos equipos anotan: <strong>{Math.round((pred.markets.btts ?? 0) * 100)}%</strong>
            </p>
          )}
        </div>
      )}

      {/* Factores */}
      <div>
        <h3 className="mb-2 text-sm font-semibold">Factores principales</h3>
        <ul className="space-y-1.5 text-sm">
          {pred.factors.map((f, i) => (
            <li key={i} className="flex gap-2">
              <span aria-hidden className="mt-0.5">
                {f.favors === "home" ? "🏠" : f.favors === "away" ? "✈️" : "•"}
              </span>
              <span>
                <strong>{f.label}.</strong>{" "}
                <span className="text-slate-600 dark:text-slate-300">{f.detail}</span>
              </span>
            </li>
          ))}
        </ul>
      </div>

      <p className="border-t border-slate-200 pt-3 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400">
        <strong>Criterio de confianza:</strong> {pred.confidence.criterion}
        <br />
        {pred.disclaimer}
      </p>
    </div>
  );
}
