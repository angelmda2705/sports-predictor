"use client";

import { useEffect, useState } from "react";

import { MockBanner } from "@/components/MockBanner";
import { ReliabilityDiagram } from "@/components/ReliabilityDiagram";
import { ApiError, apiFetch } from "@/lib/api";
import type { Performance } from "@/lib/types";

function MetricCard({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <div className="text-xs text-slate-500 dark:text-slate-400">{label}</div>
      <div className="mt-1 text-2xl font-bold tabular-nums">{value}</div>
      {hint && <div className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{hint}</div>}
    </div>
  );
}

export default function PerformancePage() {
  const [data, setData] = useState<Performance | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    apiFetch<Performance>("/performance")
      .then((p) => active && setData(p))
      .catch((e: unknown) => {
        if (!active) return;
        setError(
          e instanceof ApiError
            ? `Error ${e.status}: ${e.message}`
            : "No se pudo conectar con la API.",
        );
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="space-y-6">
      <section className="space-y-2">
        <h1 className="text-2xl font-bold">Rendimiento del modelo</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Backtest <strong>walk-forward</strong> (point-in-time): cada partido se predijo
          usando solo el historial previo a su inicio. <strong>No se ocultan los fallos.</strong>
        </p>
      </section>

      {loading && <div className="h-64 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-900" />}

      {error && (
        <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
          {error}
        </div>
      )}

      {data && (
        <>
          {data.is_mock && <MockBanner />}

          {/* Veredicto honesto vs baseline */}
          <div
            className={`rounded-xl border px-4 py-3 text-sm ${
              data.beats_baseline
                ? "border-brand-300 bg-brand-50 text-brand-800 dark:border-brand-700/60 dark:bg-brand-900/20 dark:text-brand-300"
                : "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-700/60 dark:bg-amber-900/20 dark:text-amber-200"
            }`}
          >
            {data.beats_baseline ? (
              <>
                ✅ El modelo <strong>supera</strong> al baseline ingenuo (Brier {data.brier} vs{" "}
                {data.baseline_brier}).
              </>
            ) : (
              <>
                ⚠️ El modelo <strong>aún no supera</strong> al baseline ingenuo (Brier {data.brier}{" "}
                vs {data.baseline_brier}). Es lo esperado: sobre datos mock con marcadores
                aleatorios no hay señal real que aprender. Así se ve la transparencia.
              </>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            <MetricCard label="Predicciones" value={String(data.n_predictions)} />
            <MetricCard label="Accuracy" value={`${Math.round(data.accuracy * 100)}%`} />
            <MetricCard label="Brier" value={String(data.brier)} hint={`baseline ${data.baseline_brier}`} />
            <MetricCard label="Log Loss" value={String(data.log_loss)} hint={`baseline ${data.baseline_log_loss}`} />
            <MetricCard label="ECE" value={String(data.ece)} hint="error de calibración" />
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
              <h2 className="mb-3 font-semibold">Curva de calibración</h2>
              <ReliabilityDiagram bins={data.calibration} />
              <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                Cerca de la diagonal = bien calibrado. El tamaño del punto refleja cuántas
                observaciones cayeron en ese rango.
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
              <h2 className="mb-3 font-semibold">Por banda de confianza</h2>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-slate-500 dark:text-slate-400">
                    <th className="pb-2 font-medium">Banda</th>
                    <th className="pb-2 font-medium tabular-nums">n</th>
                    <th className="pb-2 font-medium tabular-nums">Accuracy</th>
                    <th className="pb-2 font-medium tabular-nums">Brier</th>
                  </tr>
                </thead>
                <tbody>
                  {data.by_band.map((b) => (
                    <tr key={b.band} className="border-t border-slate-100 dark:border-slate-800">
                      <td className="py-2 capitalize">{b.band}</td>
                      <td className="py-2 tabular-nums">{b.n}</td>
                      <td className="py-2 tabular-nums">{Math.round(b.accuracy * 100)}%</td>
                      <td className="py-2 tabular-nums">{b.brier}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
                Idealmente, mayor confianza ⇒ mejor accuracy y menor Brier.
              </p>
            </div>
          </div>

          <p className="text-xs text-slate-500 dark:text-slate-400">{data.disclaimer}</p>
        </>
      )}
    </div>
  );
}
