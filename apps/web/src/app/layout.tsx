import type { Metadata } from "next";
import type { ReactNode } from "react";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Mentora AI — Plataforma Educacional Inteligente",
  description: "Tutor inteligente fundamentado no seu material com turmas interativas, modo socrático e radar de aprendizagem."
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="pt-BR" className="dark">
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased flex flex-col">
        <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <div className="flex items-center space-x-6">
              <Link href="/" className="flex items-center space-x-2 font-bold text-xl tracking-tight text-white hover:text-indigo-400 transition-colors">
                <span className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center text-white font-black text-lg shadow-lg shadow-indigo-500/30">
                  M
                </span>
                <span>Mentora AI</span>
              </Link>
              <nav className="hidden md:flex space-x-4 text-sm font-medium">
                <Link
                  href="/classes"
                  className="px-3 py-2 rounded-md text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
                >
                  🏫 Minhas Turmas
                </Link>
                <Link
                  href="/documents"
                  className="px-3 py-2 rounded-md text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
                >
                  📚 Biblioteca
                </Link>
                <Link
                  href="/tutor"
                  className="px-3 py-2 rounded-md text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
                >
                  💬 Tutor Livre
                </Link>
              </nav>
            </div>
            <div className="flex items-center space-x-3">
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-950 text-indigo-300 border border-indigo-800">
                v2.0 Pro
              </span>
              <a
                href="/docs"
                target="_blank"
                rel="noreferrer"
                className="text-xs text-slate-400 hover:text-slate-200 underline decoration-slate-600 underline-offset-4"
              >
                API Docs (Scalar)
              </a>
            </div>
          </div>
        </header>

        <div className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </div>

        <footer className="border-t border-slate-800/80 bg-slate-950 py-6 text-center text-xs text-slate-500">
          <p>© 2026 Mentora AI. Arquitetura Educacional Multi-Tenant com RLS e OpenCode Go Fleet.</p>
        </footer>
      </body>
    </html>
  );
}
