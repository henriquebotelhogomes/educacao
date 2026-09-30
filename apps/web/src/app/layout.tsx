import type { Metadata } from "next";
import type { ReactNode } from "react";
import Link from "next/link";
import { ThemeToggle } from "@/components/ThemeToggle";
import { UserNav } from "@/components/UserNav";
import "./globals.css";

export const metadata: Metadata = {
  title: "Mentora AI — Plataforma Educacional Inteligente",
  description: "Tutor inteligente fundamentado no seu material com turmas interativas, modo socrático e radar de aprendizagem."
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 antialiased flex flex-col transition-colors duration-200">
        <header className="border-b border-slate-200 dark:border-slate-800 bg-white/90 dark:bg-slate-900/90 backdrop-blur sticky top-0 z-50 transition-colors duration-200 shadow-2xs">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <div className="flex items-center space-x-6">
              <Link href="/" className="flex items-center space-x-2 font-bold text-xl tracking-tight text-slate-900 dark:text-white hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">
                <span className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-white font-black text-lg shadow-md shadow-indigo-500/20">
                  M
                </span>
                <span>Mentora AI</span>
              </Link>
              <nav className="hidden md:flex space-x-2 text-sm font-medium">
                <Link
                  href="/classes"
                  className="px-3 py-2 rounded-lg text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                >
                  🏫 Minhas Turmas
                </Link>
                <Link
                  href="/documents"
                  className="px-3 py-2 rounded-lg text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                >
                  📚 Biblioteca
                </Link>
                <Link
                  href="/tutor"
                  className="px-3 py-2 rounded-lg text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                >
                  💬 Tutor Livre
                </Link>
              </nav>
            </div>

            <div className="flex items-center space-x-3">
              {/* Theme Selector Toggle (Defaults to Light) */}
              <ThemeToggle />

              {/* Login / Register / User Profile Session */}
              <UserNav />

              <a
                href="http://localhost:8000/docs"
                target="_blank"
                rel="noreferrer"
                className="hidden lg:inline-flex text-xs text-slate-500 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-300 underline decoration-slate-300 dark:decoration-slate-700 underline-offset-4"
              >
                Docs API
              </a>
            </div>
          </div>
        </header>

        <div className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </div>

        <footer className="border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 py-6 text-center text-xs text-slate-500 dark:text-slate-400 transition-colors duration-200">
          <p>© 2026 Mentora AI. Arquitetura Educacional Multi-Tenant com RLS e OpenCode Go Fleet.</p>
        </footer>
      </body>
    </html>
  );
}
