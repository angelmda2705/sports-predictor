import type { Metadata } from "next";

import { AuthProvider } from "@/components/AuthProvider";
import { Header } from "@/components/Header";

import "./globals.css";

export const metadata: Metadata = {
  title: "sports-predictor — predicciones probabilísticas",
  description:
    "Plataforma de analítica deportiva con predicciones probabilísticas para fútbol soccer y NFL. No es una casa de apuestas.",
};

// Evita el parpadeo de tema: aplica la clase 'dark' antes de pintar.
const themeScript = `
  (function () {
    try {
      var t = localStorage.getItem('theme');
      var m = window.matchMedia('(prefers-color-scheme: dark)').matches;
      if (t === 'dark' || (!t && m)) document.documentElement.classList.add('dark');
    } catch (e) {}
  })();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        <AuthProvider>
          <Header />
          <main className="mx-auto max-w-5xl px-4 py-6">{children}</main>
          <footer className="mx-auto max-w-5xl px-4 py-8 text-xs text-slate-400 dark:text-slate-600">
            Las predicciones son estimaciones probabilísticas, no certezas. El
            rendimiento pasado no garantiza resultados futuros. Esta plataforma no
            ofrece asesoría financiera ni garantiza ganancias.
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
