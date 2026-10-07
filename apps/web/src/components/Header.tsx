"use client";

import Link from "next/link";

import { useAuth } from "./AuthProvider";
import { ThemeToggle } from "./ThemeToggle";

export function Header() {
  const { user, loading, logout } = useAuth();

  return (
    <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/80 backdrop-blur dark:border-slate-800 dark:bg-slate-950/80">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
        <Link href="/" className="flex items-center gap-2 font-bold">
          <span className="text-xl">📊</span>
          <span>
            sports<span className="text-brand-600">predictor</span>
          </span>
        </Link>

        <nav className="flex items-center gap-3 text-sm">
          <Link href="/" className="hidden font-medium text-slate-600 hover:text-brand-600 sm:inline dark:text-slate-300">
            Partidos
          </Link>
          <Link
            href="/performance"
            className="hidden font-medium text-slate-600 hover:text-brand-600 sm:inline dark:text-slate-300"
          >
            Rendimiento
          </Link>
          <Link
            href="/historial"
            className="hidden font-medium text-slate-600 hover:text-brand-600 sm:inline dark:text-slate-300"
          >
            Historial
          </Link>
          <ThemeToggle />
          {loading ? (
            <span className="text-slate-400">…</span>
          ) : user ? (
            <>
              <span className="hidden text-slate-500 sm:inline dark:text-slate-400">
                {user.email} · {user.plan}
              </span>
              <button
                type="button"
                onClick={() => void logout()}
                className="rounded-lg bg-slate-200 px-3 py-1.5 font-medium transition hover:bg-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700"
              >
                Salir
              </button>
            </>
          ) : (
            <Link
              href="/login"
              className="rounded-lg bg-brand-600 px-3 py-1.5 font-medium text-white transition hover:bg-brand-700"
            >
              Iniciar sesión
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
