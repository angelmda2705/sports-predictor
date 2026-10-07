"use client";

import { useEffect, useState } from "react";

import { MatchCard } from "@/components/MatchCard";
import { MockBanner } from "@/components/MockBanner";
import { ApiError, apiFetch } from "@/lib/api";
import type { MatchList } from "@/lib/types";

// Competiciones reales con su vista por defecto. El Mundial 2026 va primero:
// mostramos los PRÓXIMOS partidos (los que importa predecir). La Premier League
// es histórica (ya finalizada), así que mostramos los más recientes.
const TABS: { code: string; label: string; params: Record<string, string>; hint: string }[] = [
  {
    code: "WC_2026",
    label: "Mundial 2026",
    params: { status: "scheduled", order: "asc" },
    hint: "Próximos partidos. Ratings sembrados con historial internacional real.",
  },
  {
    code: "ENG_PL",
    label: "Premier League",
    params: { order: "desc" },
    hint: "Partidos recientes (temporadas reales 2021–2024).",
  },
];

export default function DashboardPage() {
  const [tabIdx, setTabIdx] = useState(0);
  const [data, setData] = useState<MatchList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const tab = TABS[tabIdx];

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    const params = new URLSearchParams({ competition: tab.code, limit: "24", ...tab.params });

    apiFetch<MatchList>(`/matches?${params.toString()}`)
      .then((res) => active && setData(res))
      .catch((e: unknown) => {
        if (!active) return;
        setError(
          e instanceof ApiError
            ? `Error ${e.status}: ${e.message}`
            : "No se pudo conectar con la API. ¿Está corriendo el backend en :8000?",
        );
      })
      .finally(() => active && setLoading(false));

    return () => {
      active = false;
    };
  }, [tab.code, tab.params]);

  return (
    <div className="space-y-6">
      <section className="space-y-2">
        <h1 className="text-2xl font-bold">Partidos</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Toca un partido para ver la predicción del modelo: probabilidades 1X2, marcador
          esperado, nivel de confianza y los factores que influyen.
        </p>
      </section>

      {data?.contains_mock && <MockBanner />}

      <div className="flex flex-wrap gap-2">
        {TABS.map((t, i) => (
          <button
            key={t.code}
            type="button"
            onClick={() => setTabIdx(i)}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition ${
              i === tabIdx
                ? "bg-brand-600 text-white"
                : "bg-slate-200 text-slate-700 hover:bg-slate-300 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      <p className="text-xs text-slate-500 dark:text-slate-400">{tab.hint}</p>

      {loading && <SkeletonGrid />}

      {error && (
        <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
          {error}
        </div>
      )}

      {!loading && !error && data && data.items.length === 0 && (
        <p className="text-slate-500 dark:text-slate-400">No hay partidos en esta vista.</p>
      )}

      {!loading && !error && data && data.items.length > 0 && (
        <>
          <p className="text-xs text-slate-500 dark:text-slate-400">{data.total} partido(s)</p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.items.map((m) => (
              <MatchCard key={m.id} match={m} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function SkeletonGrid() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="h-32 animate-pulse rounded-xl border border-slate-200 bg-slate-100 dark:border-slate-800 dark:bg-slate-900"
        />
      ))}
    </div>
  );
}
