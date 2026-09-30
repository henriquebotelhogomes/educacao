"use client";

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Classroom,
  ClassroomMember,
  LearningGapMetric,
  PedagogicalMode,
  getClassroom,
  getLearningGapRadar,
  listClassroomMembers,
  updateClassroom,
} from "@/lib/classes";

export default function EducatorDashboardPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: classroomId } = use(params);
  const [classroom, setClassroom] = useState<Classroom | null>(null);
  const [members, setMembers] = useState<ClassroomMember[]>([]);
  const [radarMetrics, setRadarMetrics] = useState<LearningGapMetric[]>([]);
  const [loading, setLoading] = useState(true);
  const [isUpdatingMode, setIsUpdatingMode] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [cls, mems, radar] = await Promise.all([
        getClassroom(classroomId),
        listClassroomMembers(classroomId),
        getLearningGapRadar(classroomId),
      ]);
      setClassroom(cls);
      setMembers(mems);
      setRadarMetrics(radar);
    } catch {
      setFeedbackMsg("Erro ao carregar dados do painel do educador.");
    } finally {
      setLoading(false);
    }
  }, [classroomId]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  async function handleToggleMode(newMode: PedagogicalMode) {
    if (!classroom || isUpdatingMode || classroom.pedagogical_mode === newMode) return;
    try {
      setIsUpdatingMode(true);
      const updated = await updateClassroom(classroomId, { pedagogical_mode: newMode });
      setClassroom(updated);
      setFeedbackMsg(
        `Modo pedagógico alterado para: ${
          newMode === "SOCRATIC" ? "Socrático (Anti-Cola)" : "Explicação Direta"
        }`
      );
      setTimeout(() => setFeedbackMsg(null), 3500);
    } catch {
      setFeedbackMsg("Falha ao atualizar o modo pedagógico.");
    } finally {
      setIsUpdatingMode(false);
    }
  }

  function copyInviteCode() {
    if (!classroom) return;
    void navigator.clipboard.writeText(classroom.code);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2500);
  }

  if (loading) {
    return (
      <div className="text-center py-16 text-slate-500 text-sm">
        Carregando painel docente e radar de aprendizagem...
      </div>
    );
  }

  if (!classroom) {
    return (
      <div className="text-center py-16 text-red-600 dark:text-red-400 text-sm">
        Turma não encontrada ou permissão insuficiente.
      </div>
    );
  }

  return (
    <main className="space-y-8">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mb-1">
            <Link href="/classes" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">
              ← Minhas Turmas
            </Link>
            <span>/</span>
            <span>Painel do Educador</span>
          </div>
          <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white flex items-center gap-3">
            <span>{classroom.name}</span>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-purple-50 dark:bg-purple-950 border border-purple-200 dark:border-purple-800 text-purple-700 dark:text-purple-300 uppercase font-semibold">
              Cockpit Docente
            </span>
          </h1>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Disciplina: <strong className="text-slate-800 dark:text-slate-200">{classroom.subject ?? "Geral"}</strong> • Criada em:{" "}
            {new Date(classroom.created_at).toLocaleDateString("pt-BR")}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href={`/classes/${classroomId}/tutor`}
            className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition-colors shadow-sm"
          >
            💬 Abrir Tutor da Turma
          </Link>
        </div>
      </div>

      {feedbackMsg && (
        <div
          role="status"
          className="p-4 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800 text-indigo-900 dark:text-indigo-300 text-xs font-medium"
        >
          {feedbackMsg}
        </div>
      )}

      {/* Row 1: 6-Character Invitation Code & Pedagogical Mode Controller */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Invitation Code Card */}
        <section className="bg-white dark:bg-gradient-to-br dark:from-slate-900 dark:to-indigo-950/30 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 space-y-4 shadow-xs dark:shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Código de Acesso dos Alunos
            </span>
            <span className="px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 text-[10px] font-mono border border-indigo-200 dark:border-indigo-800 font-semibold">
              Padrão Google Classroom
            </span>
          </div>

          <div className="flex items-center justify-between bg-slate-50 dark:bg-slate-950 p-4 rounded-xl border border-slate-200 dark:border-slate-800">
            <div>
              <span className="font-mono text-3xl sm:text-4xl font-black text-indigo-600 dark:text-indigo-400 tracking-widest">
                {classroom.code}
              </span>
              <p className="text-[11px] text-slate-500 mt-1">
                Sem necessidade de convite por e-mail ou aprovação manual.
              </p>
            </div>
            <button
              onClick={copyInviteCode}
              type="button"
              className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition-all shadow-sm"
            >
              {copiedCode ? "✓ Copiado!" : "Copiar Código"}
            </button>
          </div>
        </section>

        {/* Pedagogical Mode Controller */}
        <section className="bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 space-y-4 shadow-xs dark:shadow-lg">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 block mb-1">
              Controle Pedagógico da Turma
            </span>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Defina como a IA deve interagir com os alunos desta turma.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => void handleToggleMode("SOCRATIC")}
              disabled={isUpdatingMode}
              type="button"
              className={`p-3 rounded-xl border text-left transition-all ${
                classroom.pedagogical_mode === "SOCRATIC"
                  ? "bg-indigo-50 dark:bg-indigo-950 border-indigo-500 text-indigo-950 dark:text-white ring-2 ring-indigo-500/30"
                  : "bg-slate-50 dark:bg-slate-950/40 border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-700"
              }`}
            >
              <div className="font-bold text-sm flex items-center gap-1.5">
                <span>🦉</span> Socrático
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                Anti-cola: conduz o aluno por perguntas norteadoras.
              </p>
            </button>

            <button
              onClick={() => void handleToggleMode("EXPLANATION")}
              disabled={isUpdatingMode}
              type="button"
              className={`p-3 rounded-xl border text-left transition-all ${
                classroom.pedagogical_mode === "EXPLANATION"
                  ? "bg-indigo-50 dark:bg-indigo-950 border-indigo-500 text-indigo-950 dark:text-white ring-2 ring-indigo-500/30"
                  : "bg-slate-50 dark:bg-slate-950/40 border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-700"
              }`}
            >
              <div className="font-bold text-sm flex items-center gap-1.5">
                <span>📖</span> Explicação
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                Respostas diretas e didáticas fundamentadas no texto.
              </p>
            </button>
          </div>
        </section>
      </div>

      {/* Row 2: Learning Gap Radar (Zero PII Pedagogical Diagnostics) */}
      <section className="bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 space-y-6 shadow-xs dark:shadow-lg">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200 dark:border-slate-800 pb-4">
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <span>📊</span> Radar de Lacunas de Aprendizagem
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Diagnóstico pedagógico agregado em tempo real • <strong>Zero PII (100% livre de identificadores individuais de alunos)</strong>
            </p>
          </div>
          <span className="text-xs px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-mono border border-slate-200 dark:border-slate-700">
            {radarMetrics.length} tópicos monitorados
          </span>
        </div>

        {radarMetrics.length === 0 ? (
          <div className="text-center py-12 border border-dashed border-slate-300 dark:border-slate-800 rounded-xl p-6 space-y-2 bg-slate-50/50 dark:bg-transparent">
            <span className="text-3xl block">🎯</span>
            <p className="text-slate-800 dark:text-slate-300 font-medium">Nenhuma lacuna crítica detectada na turma até o momento.</p>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              Conforme os alunos enviarem perguntas ao tutor e avaliarem respostas, o sistema agregará os temas de maior dúvida nesta visualização.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {radarMetrics.map((metric) => {
                const percentage = Math.min(100, Math.round(metric.gap_score * 100));
                const isCritical = percentage >= 70;
                const isModerate = percentage >= 40 && percentage < 70;

                return (
                  <div
                    key={metric.topic}
                    className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 space-y-2"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-slate-900 dark:text-white truncate max-w-[200px]">
                        {metric.topic}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="text-slate-500 dark:text-slate-400">{metric.query_count} dúvidas</span>
                        <span
                          className={`px-2 py-0.5 rounded font-mono font-bold text-[10px] ${
                            isCritical
                              ? "bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800"
                              : isModerate
                              ? "bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800"
                              : "bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
                          }`}
                        >
                          Índice: {percentage}%
                        </span>
                      </div>
                    </div>

                    {/* Progress Bar Meter */}
                    <div className="w-full bg-slate-200 dark:bg-slate-800 rounded-full h-2 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${
                          isCritical
                            ? "bg-red-500"
                            : isModerate
                            ? "bg-amber-500"
                            : "bg-emerald-500"
                        }`}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>

                    <div className="text-[10px] text-slate-500 flex justify-between">
                      <span>Última ocorrência: {new Date(metric.last_occurred_at).toLocaleDateString("pt-BR")}</span>
                      <span>{isCritical ? "⚠️ Revisão recomendada" : "Compreensão estável"}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* AI Actionable Suggestion */}
            <div className="p-4 rounded-xl bg-indigo-50/70 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-900/60 text-xs text-indigo-900 dark:text-indigo-200 flex items-start gap-3">
              <span className="text-xl">💡</span>
              <div>
                <strong className="block text-slate-900 dark:text-white mb-0.5">Sugestão Pedagógica para a Próxima Aula</strong>
                <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
                  Os dados agregados indicam que o tópico principal de dúvida dos alunos está concentrado nas lacunas destacadas acima.
                  Recomendamos dedicar os primeiros 15 minutos da próxima aula para recapitular esses conceitos fundamentais.
                </p>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* Row 3: Enrolled Students Roster */}
      <section className="bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 space-y-4 shadow-xs dark:shadow-lg">
        <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
          <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <span>👥</span> Alunos e Membros da Turma ({members.length})
          </h2>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400">
                <th className="py-2.5 px-3">Identificador do Membro</th>
                <th className="py-2.5 px-3">Papel na Turma</th>
                <th className="py-2.5 px-3">Data de Ingresso</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
              {members.map((member) => (
                <tr key={member.user_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/30">
                  <td className="py-2.5 px-3 font-mono text-slate-700 dark:text-slate-300">
                    {member.user_id.slice(0, 8)}...{member.user_id.slice(-4)}
                  </td>
                  <td className="py-2.5 px-3">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                        member.role === "EDUCATOR"
                          ? "bg-purple-50 dark:bg-purple-950 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800"
                          : "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700"
                      }`}
                    >
                      {member.role === "EDUCATOR" ? "Educador" : "Aluno"}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-slate-500 dark:text-slate-400">
                    {new Date(member.joined_at).toLocaleDateString("pt-BR")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
