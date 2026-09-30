"use client";

import { FormEvent, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { UserSession, logoutUser, signinUser, signupUser } from "@/lib/auth";

export function UserNav() {
  const [session, setSession] = useState<UserSession | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [tab, setTab] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    // Check if session was saved in local state
    const saved = localStorage.getItem("mentora_user_session");
    if (saved) {
      try {
        setSession(JSON.parse(saved) as UserSession);
      } catch {
        localStorage.removeItem("mentora_user_session");
      }
    }
  }, []);

  async function handleAuth(e: FormEvent) {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);
    setIsLoading(true);

    try {
      if (tab === "signin") {
        const userSession = await signinUser({ email, password });
        setSession(userSession);
        localStorage.setItem("mentora_user_session", JSON.stringify(userSession));
        setSuccessMsg("Login realizado com sucesso!");
        setTimeout(() => {
          setShowModal(false);
          setSuccessMsg(null);
          window.location.reload();
        }, 1000);
      } else {
        if (!displayName.trim()) {
          setErrorMsg("Por favor, informe seu nome.");
          setIsLoading(false);
          return;
        }
        const userSession = await signupUser({
          email,
          password,
          display_name: displayName.trim(),
        });
        setSession(userSession);
        localStorage.setItem("mentora_user_session", JSON.stringify(userSession));
        setSuccessMsg("Conta criada com sucesso!");
        setTimeout(() => {
          setShowModal(false);
          setSuccessMsg(null);
          window.location.reload();
        }, 1000);
      }
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Erro na autenticação.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleLogout() {
    await logoutUser();
    setSession(null);
    localStorage.removeItem("mentora_user_session");
    window.location.href = "/";
  }

  return (
    <>
      {session ? (
        <div className="flex items-center gap-2.5">
          <div className="px-3 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800 text-xs font-medium text-indigo-950 dark:text-indigo-200 flex items-center gap-1.5">
            <span>👤</span>
            <span className="font-semibold">{session.display_name || session.email?.split("@")[0] || "Usuário"}</span>
            <span className="text-[10px] text-indigo-600 dark:text-indigo-400">({session.role})</span>
          </div>
          <button
            onClick={() => void handleLogout()}
            type="button"
            className="px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-red-50 dark:hover:bg-red-950/50 hover:text-red-600 dark:hover:text-red-400 text-slate-700 dark:text-slate-300 text-xs font-medium transition-colors"
          >
            Sair
          </button>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              setTab("signin");
              setErrorMsg(null);
              setSuccessMsg(null);
              setShowModal(true);
            }}
            type="button"
            className="px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-semibold transition-colors"
          >
            Entrar
          </button>
          <button
            onClick={() => {
              setTab("signup");
              setErrorMsg(null);
              setSuccessMsg(null);
              setShowModal(true);
            }}
            type="button"
            className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-xs transition-colors"
          >
            Criar Conta
          </button>
        </div>
      )}

      {/* Authentication Modal with Portal to body to avoid parent clipping/backdrop containment */}
      {showModal && mounted && createPortal(
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-5 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <span className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-bold text-xs">
                  M
                </span>
                <h2 className="text-base font-bold text-slate-900 dark:text-white">
                  {tab === "signin" ? "Acessar Mentora AI" : "Criar Nova Conta"}
                </h2>
              </div>
              <button
                onClick={() => setShowModal(false)}
                type="button"
                className="text-slate-400 hover:text-slate-600 dark:hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            {/* Tabs */}
            <div className="flex rounded-xl bg-slate-100 dark:bg-slate-950 p-1 border border-slate-200 dark:border-slate-800">
              <button
                onClick={() => {
                  setTab("signin");
                  setErrorMsg(null);
                  setSuccessMsg(null);
                }}
                type="button"
                className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                  tab === "signin"
                    ? "bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-xs"
                    : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
                }`}
              >
                Já tenho conta (Entrar)
              </button>
              <button
                onClick={() => {
                  setTab("signup");
                  setErrorMsg(null);
                  setSuccessMsg(null);
                }}
                type="button"
                className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                  tab === "signup"
                    ? "bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-xs"
                    : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
                }`}
              >
                Criar Nova Conta
              </button>
            </div>

            {errorMsg && (
              <div role="alert" className="p-3 rounded-lg bg-red-50 dark:bg-red-950/60 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-300 text-xs">
                {errorMsg}
              </div>
            )}

            {successMsg && (
              <div role="status" className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 text-emerald-600 dark:text-emerald-300 text-xs font-semibold text-center">
                {successMsg}
              </div>
            )}

            <form onSubmit={handleAuth} className="space-y-4">
              {tab === "signup" && (
                <div>
                  <label htmlFor="displayName" className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Nome Completo *
                  </label>
                  <input
                    id="displayName"
                    type="text"
                    required
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    placeholder="Ex: Prof. Carlos ou Ana Clara"
                    className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-white text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              )}

              <div>
                <label htmlFor="email" className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  E-mail institucional ou pessoal *
                </label>
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="usuario@escola.edu.br"
                  className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-white text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label htmlFor="password" className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Senha *
                </label>
                <input
                  id="password"
                  type="password"
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Mínimo 8 caracteres"
                  className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-white text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold text-xs transition-colors shadow-sm"
                >
                  {isLoading
                    ? "Processando..."
                    : tab === "signin"
                    ? "Entrar na Plataforma"
                    : "Finalizar Cadastro"}
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}
    </>
  );
}
