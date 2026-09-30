"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Classroom,
  PedagogicalMode,
  createClassroom,
  joinClassroom,
  listClassrooms,
} from "@/lib/classes";

export default function ClassesHubPage() {
  const [classrooms, setClassrooms] = useState<Classroom[]>([]);
  const [loading, setLoading] = useState(true);
  const [joinCode, setJoinCode] = useState("");
  const [isJoining, setIsJoining] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [newSubject, setNewSubject] = useState("");
  const [newMode, setNewMode] = useState<PedagogicalMode>("SOCRATIC");
  const [statusMessage, setStatusMessage] = useState<{
    text: string;
    type: "success" | "error" | "info";
  } | null>(null);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  const loadClasses = useCallback(async () => {
    try {
      setLoading(true);
      const data = await listClassrooms();
      setClassrooms(data);
    } catch (err) {
      setStatusMessage({
        text: err instanceof Error ? err.message : "Erro ao carregar turmas.",
        type: "error",
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadClasses();
  }, [loadClasses]);

  async function handleJoin(e: FormEvent) {
    e.preventDefault();
    if (!joinCode.trim()) return;
    try {
      setIsJoining(true);
      setStatusMessage(null);
      const joined = await joinClassroom(joinCode);
      setStatusMessage({
        text: `Sucesso! Você entrou na turma "${joined.name}".`,
        type: "success",
      });
      setJoinCode("");
      await loadClasses();
    } catch (err) {
      setStatusMessage({
        text: err instanceof Error ? err.message : "Código de turma inválido ou expirado.",
        type: "error",
      });
    } finally {
      setIsJoining(false);
    }
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    try {
      setIsCreating(true);
      setStatusMessage(null);
      const created = await createClassroom({
        name: newName,
        subject: newSubject.trim() || undefined,
        pedagogical_mode: newMode,
      });
      setStatusMessage({
        text: `Turma "${created.name}" criada com sucesso! Código de convite: ${created.code}`,
        type: "success",
      });
      setNewName("");
      setNewSubject("");
      setShowCreateModal(false);
      await loadClasses();
    } catch (err) {
      setStatusMessage({
        text: err instanceof Error ? err.message : "Erro ao criar turma.",
        type: "error",
      });
    } finally {
      setIsCreating(false);
    }
  }

  function copyCode(code: string) {
    void navigator.clipboard.writeText(code);
    setCopiedCode(code);
    setTimeout(() => setCopiedCode(null), 2500);
  }

  return (
    <main className="space-y-8">
      {/* Top Heading & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white">Minhas Turmas</h1>
          <p className="text-sm text-slate-400 mt-1">
            Espaço de aprendizagem conectada. Acesse o tutor personalizado da sua classe ou gerencie alunos e relatórios.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowCreateModal(!showCreateModal)}
            className="inline-flex items-center px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold shadow-lg shadow-indigo-600/20 transition-all"
            type="button"
          >
            ➕ Nova Turma
          </button>
        </div>
      </div>

      {/* Status Alert */}
      {statusMessage && (
        <div
          role="status"
          className={`p-4 rounded-xl border text-sm transition-all ${
            statusMessage.type === "success"
              ? "bg-emerald-950/60 border-emerald-800 text-emerald-300"
              : statusMessage.type === "error"
              ? "bg-red-950/60 border-red-800 text-red-300"
              : "bg-slate-900 border-slate-700 text-slate-300"
          }`}
        >
          {statusMessage.text}
        </div>
      )}

      {/* Join with Code Card */}
      <section className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 shadow-md">
        <h2 className="text-base font-bold text-white mb-2">Entrar em uma Turma com Código</h2>
        <p className="text-xs text-slate-400 mb-4">
          Digite o código de 6 caracteres fornecido pelo seu professor (exemplo: <code className="text-indigo-400 font-mono">ABC123</code>).
        </p>
        <form onSubmit={handleJoin} className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 max-w-lg">
          <input
            type="text"
            maxLength={6}
            value={joinCode}
            onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
            placeholder="CÓDIGO (6 DÍGITOS)"
            className="px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-700 text-white font-mono tracking-widest text-center sm:text-left text-lg placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 uppercase"
          />
          <button
            type="submit"
            disabled={isJoining || joinCode.trim().length !== 6}
            className="px-6 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-white text-sm font-semibold border border-slate-700 transition-colors"
          >
            {isJoining ? "Entrando..." : "Entrar na Turma"}
          </button>
        </form>
      </section>

      {/* Modal / Form: Create Classroom */}
      {showCreateModal && (
        <section className="bg-slate-900/90 border border-indigo-900/60 rounded-2xl p-6 shadow-2xl space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h2 className="text-lg font-bold text-white">Criar Nova Turma</h2>
            <button
              onClick={() => setShowCreateModal(false)}
              className="text-slate-400 hover:text-white text-sm"
              type="button"
            >
              ✕ Fechar
            </button>
          </div>
          <form onSubmit={handleCreate} className="space-y-4 max-w-xl">
            <div>
              <label htmlFor="className" className="block text-xs font-semibold text-slate-300 mb-1">
                Nome da Turma *
              </label>
              <input
                id="className"
                type="text"
                required
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Ex: Biologia 3º Ano B"
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label htmlFor="classSubject" className="block text-xs font-semibold text-slate-300 mb-1">
                Disciplina / Matéria (Opcional)
              </label>
              <input
                id="classSubject"
                type="text"
                value={newSubject}
                onChange={(e) => setNewSubject(e.target.value)}
                placeholder="Ex: Genética e Ecologia"
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <span className="block text-xs font-semibold text-slate-300 mb-1">
                Modo Pedagógico da Turma
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setNewMode("SOCRATIC")}
                  className={`p-3 rounded-xl border text-left transition-all ${
                    newMode === "SOCRATIC"
                      ? "bg-indigo-950/70 border-indigo-500 text-white ring-1 ring-indigo-500"
                      : "bg-slate-950/50 border-slate-800 text-slate-400 hover:border-slate-700"
                  }`}
                >
                  <div className="font-semibold text-sm flex items-center gap-1.5">
                    <span>🦉</span> Socrático (Anti-Cola)
                  </div>
                  <p className="text-xs text-slate-400 mt-1">
                    Faz perguntas reflexivas para o aluno construir a resposta.
                  </p>
                </button>
                <button
                  type="button"
                  onClick={() => setNewMode("EXPLANATION")}
                  className={`p-3 rounded-xl border text-left transition-all ${
                    newMode === "EXPLANATION"
                      ? "bg-indigo-950/70 border-indigo-500 text-white ring-1 ring-indigo-500"
                      : "bg-slate-950/50 border-slate-800 text-slate-400 hover:border-slate-700"
                  }`}
                >
                  <div className="font-semibold text-sm flex items-center gap-1.5">
                    <span>📖</span> Explicação Direta
                  </div>
                  <p className="text-xs text-slate-400 mt-1">
                    Fornece respostas didáticas estruturadas diretamente.
                  </p>
                </button>
              </div>
            </div>
            <div className="pt-2 flex gap-3">
              <button
                type="submit"
                disabled={isCreating || !newName.trim()}
                className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-semibold transition-colors"
              >
                {isCreating ? "Criando..." : "Confirmar e Criar Turma"}
              </button>
              <button
                type="button"
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-sm hover:bg-slate-700 transition-colors"
              >
                Cancelar
              </button>
            </div>
          </form>
        </section>
      )}

      {/* Classroom List Grid */}
      <section className="space-y-4">
        <h2 className="text-xl font-bold text-white">Turmas Conectadas</h2>
        {loading ? (
          <div className="text-center py-12 text-slate-500 text-sm">Carregando suas turmas...</div>
        ) : classrooms.length === 0 ? (
          <div className="text-center py-12 rounded-2xl border border-dashed border-slate-800 p-8 space-y-3">
            <span className="text-4xl block">🏫</span>
            <p className="text-slate-300 font-medium">Você ainda não está matriculado em nenhuma turma.</p>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              Utilize o formulário acima para entrar em uma turma usando um código de 6 dígitos ou crie sua própria turma caso seja educador.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {classrooms.map((cls) => {
              const isEducator = cls.my_role === "EDUCATOR" || cls.my_role === "ADMIN";
              return (
                <div
                  key={cls.id}
                  className="rounded-2xl bg-slate-900/70 border border-slate-800 hover:border-slate-700 transition-all flex flex-col justify-between p-6 shadow-lg"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between gap-2">
                      <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-slate-800 text-slate-300">
                        {cls.subject ?? "Geral"}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded-md text-xs font-medium ${
                          isEducator
                            ? "bg-purple-950/80 text-purple-300 border border-purple-800"
                            : "bg-emerald-950/80 text-emerald-300 border border-emerald-800"
                        }`}
                      >
                        {isEducator ? "Professor" : "Aluno"}
                      </span>
                    </div>

                    <h3 className="text-xl font-bold text-white line-clamp-1">{cls.name}</h3>

                    {/* Pedagogical Mode Indicator */}
                    <div className="flex items-center gap-1.5 text-xs text-slate-400">
                      <span>{cls.pedagogical_mode === "SOCRATIC" ? "🦉" : "📖"}</span>
                      <span>
                        Modo:{" "}
                        <strong className="text-slate-200">
                          {cls.pedagogical_mode === "SOCRATIC" ? "Socrático" : "Explicação"}
                        </strong>
                      </span>
                    </div>

                    {/* Code Card for Educator */}
                    {isEducator && (
                      <div className="bg-slate-950/70 rounded-xl p-3 border border-slate-800/80 flex items-center justify-between">
                        <div>
                          <span className="text-[10px] uppercase font-bold text-slate-500 block">
                            Código de Convite
                          </span>
                          <span className="font-mono text-base font-bold text-indigo-400 tracking-wider">
                            {cls.code}
                          </span>
                        </div>
                        <button
                          onClick={() => copyCode(cls.code)}
                          type="button"
                          className="px-2.5 py-1 text-xs rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                        >
                          {copiedCode === cls.code ? "✓ Copiado" : "Copiar"}
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Navigation Links */}
                  <div className="pt-6 mt-6 border-t border-slate-800/80 grid grid-cols-2 gap-2">
                    <Link
                      href={`/classes/${cls.id}/tutor`}
                      className="col-span-2 text-center py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition-colors shadow-sm"
                    >
                      💬 Abrir Tutor da Turma
                    </Link>
                    <Link
                      href={`/classes/${cls.id}/flashcards`}
                      className="text-center py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium text-xs transition-colors"
                    >
                      🃏 Flashcards
                    </Link>
                    {isEducator ? (
                      <Link
                        href={`/classes/${cls.id}/educator`}
                        className="text-center py-2 rounded-lg bg-purple-950/60 hover:bg-purple-900/60 border border-purple-800/60 text-purple-200 font-medium text-xs transition-colors"
                      >
                        📊 Painel Docente
                      </Link>
                    ) : (
                      <div className="text-center py-2 text-slate-600 text-xs flex items-center justify-center">
                        Turma Ativa
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </main>
  );
}
