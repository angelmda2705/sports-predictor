"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ApiError, apiFetch } from "@/lib/api";
import { formatKickoff } from "@/lib/format";
import type { StoredPrediction, TrackRecord } from "@/lib/types";

function Metric({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <div className="text-xs text-slate-500 dark:text-slate-400">{label}</div>
      <div className="mt-1 text-2xl font-bold tabular-nums">{value}</div>
      {hint && <div className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{hint}</div>}
    </div>
  );
}

function pct(probs: { home: number; draw: number; away: number }) {
  return `${Math.round(probs.home * 100)}/${Math.round(probs.draw * 100)}/${Math.round(probs.away * 100)}`;
}

export default function HistorialPage() {
  const [track, setTrack] = useState<TrackRecord | null>(null);
  const [items, setItems] = useState<StoredPrediction[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([
      apiFetch<TrackRecord>("/predictions/track-record"),
      apiFetch<{ items: StoredPrediction[] }>("/predictions/recent?limit=40"),
    ])
      .then(([tr, rec]) => {
        if (!active) return;
        setTrack(tr);
        setItems(rec.items);
      })
      .catch((e: unknown) => {
        if (active)
          setError(e instanceof ApiError ? `Error ${e.status}` : "No se pudo cargar el historial.");
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="space-y-6">
      <section className="space-y-2">
        <h1 className="text-2xl font-bold">Historial de predicciones</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Cada predicción se guarda con su versión de modelo y, al terminar el partido, su
          resultado real. <strong>No se ocultan los fallos.</strong>
        </p>
      </section>

      {error && (
        <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
          {error}
        </div>
      )}

      {track && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            <Metric label="Predicciones" value={String(track.n_predictions)} />
            <Metric label="Resueltas" value={String(track.n_resolved)} hint="ya con resultado" />
            <Metric label="Accuracy" value={`${Math.round(track.accuracy * 100)}%`} />
            <Metric label="Brier" value={String(track.brier)} hint="menor = mejor" />
            <Metric label="Log Loss" value={String(track.log_loss)} />
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">{track.note}</p>
        </>
      )}

      {items && (
        <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-slate-500 dark:bg-slate-900 dark:text-slate-400">
              <tr>
                <th className="px-3 py-2 font-medium">Partido</th>
                <th className="px-3 py-2 font-medium">Liga</th>
                <th className="px-3 py-2 font-medium">1X2 (%)</th>
                <th className="px-3 py-2 font-medium">Resultado</th>
                <th className="px-3 py-2 font-medium">¿Acertó?</th>
              </tr>
            </thead>
            <tbody>
              {items.map((v) => (
                <tr
                  key={`${v.match_id}-${v.model}`}
                  className="border-t border-slate-100 dark:border-slate-800"
                >
                  <td className="px-3 py-2">
                    <Link href={`/matches/${v.match_id}`} className="hover:text-brand-600">
                      {v.home_name} vs {v.away_name}
                    </Link>
                    <div className="text-xs text-slate-400">{formatKickoff(v.kickoff_utc)}</div>
                  </td>
                  <td className="px-3 py-2 text-slate-500 dark:text-slate-400">
                    {v.competition_code}
                  </td>
                  <td className="px-3 py-2 tabular-nums">{pct(v.probabilities)}</td>
                  <td className="px-3 py-2 tabular-nums">
                    {v.resolved ? `${v.home_score}–${v.away_score}` : "—"}
                  </td>
                  <td className="px-3 py-2">
                    {!v.resolved ? (
                      <span className="text-slate-400">pendiente</span>
                    ) : v.correct_pick ? (
                      <span className="font-medium text-brand-600 dark:text-brand-400">✓ sí</span>
                    ) : (
                      <span className="font-medium text-red-600 dark:text-red-400">✗ no</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
