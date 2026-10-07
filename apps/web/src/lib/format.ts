import type { MatchStatus, Sport } from "./types";

export function formatKickoff(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("es-MX", {
    weekday: "short",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export const SPORT_LABEL: Record<Sport, string> = {
  soccer: "Fútbol soccer",
  american_football: "Fútbol americano",
};

export const STATUS_LABEL: Record<MatchStatus, string> = {
  scheduled: "Programado",
  live: "En vivo",
  finished: "Finalizado",
  postponed: "Pospuesto",
};

export const STATUS_CLASS: Record<MatchStatus, string> = {
  scheduled: "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300",
  live: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
  finished: "bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  postponed: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
};
