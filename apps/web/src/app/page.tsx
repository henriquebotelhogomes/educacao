import Link from "next/link";
import { getApiMeta } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const result = await getApiMeta();

  return (
    <main className="space-y-12">
      {/* Hero Section with Dual-Theme Gradients */}
      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-indigo-50/80 via-white to-purple-50/60 dark:from-indigo-950/50 dark:via-slate-900 dark:to-slate-900 border border-indigo-100 dark:border-indigo-900/40 p-8 sm:p-12 shadow-sm dark:shadow-2xl transition-colors">
        <div className="max-w-3xl space-y-6">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/20 text-indigo-700 dark:text-indigo-300 text-xs font-semibold">
            <span>✨ Versão 2.0 com Turmas, Modo Socrático & Radar de Lacunas</span>
          </div>
          <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-slate-900 dark:text-white leading-tight">
            Educação Elevada por IA com{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 dark:from-indigo-400 dark:via-purple-300 dark:to-pink-400">
              Rigor Pedagógico & Evidência
            </span>
          </h1>
          <p className="text-base sm:text-lg text-slate-600 dark:text-slate-300 leading-relaxed">
            Conecte turmas escolares via código de 6 caracteres, configure o modo pedagógico anti-cola
            (Socrático vs. Explicação) e acompanhe o Radar de Lacunas de Aprendizagem com zero exposição de PII.
          </p>
          <div className="flex flex-wrap gap-4 pt-2">
            <Link
              href="/classes"
              className="inline-flex items-center justify-center px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm shadow-md shadow-indigo-600/25 transition-all hover:scale-[1.02]"
            >
              🏫 Acessar Minhas Turmas
            </Link>
            <Link
              href="/documents"
              className="inline-flex items-center justify-center px-6 py-3 rounded-xl bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 border border-slate-300 dark:border-slate-700 font-semibold text-sm shadow-2xs transition-all"
            >
              📚 Enviar Material (PDFs)
            </Link>
            <Link
              href="/tutor"
              className="inline-flex items-center justify-center px-6 py-3 rounded-xl bg-slate-100 dark:bg-slate-800/60 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 font-medium text-sm transition-all"
            >
              💬 Tutor Livre
            </Link>
          </div>
        </div>
      </section>

      {/* Feature Cards Grid */}
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="rounded-xl bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 p-6 space-y-3 hover:border-indigo-500/40 shadow-xs dark:shadow-none transition-all">
          <div className="w-10 h-10 rounded-lg bg-indigo-50 dark:bg-indigo-950 border border-indigo-200 dark:border-indigo-800 flex items-center justify-center text-xl">
            🎫
          </div>
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">Código de 6 Dígitos</h2>
          <p className="text-sm text-slate-600 dark:text-slate-400 leading-normal">
            Alunos entram na turma em segundos sem atrito. Educadores geram turmas com código único no padrão Google Classroom.
          </p>
        </div>

        <div className="rounded-xl bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 p-6 space-y-3 hover:border-indigo-500/40 shadow-xs dark:shadow-none transition-all">
          <div className="w-10 h-10 rounded-lg bg-purple-50 dark:bg-purple-950 border border-purple-200 dark:border-purple-800 flex items-center justify-center text-xl">
            🦉
          </div>
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">Modo Socrático Anti-Cola</h2>
          <p className="text-sm text-slate-600 dark:text-slate-400 leading-normal">
            O professor decide se a IA atua como tutora maiêutica guiando a linha de raciocínio ou se fornece explicações diretas.
          </p>
        </div>

        <div className="rounded-xl bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 p-6 space-y-3 hover:border-indigo-500/40 shadow-xs dark:shadow-none transition-all">
          <div className="w-10 h-10 rounded-lg bg-emerald-50 dark:bg-emerald-950 border border-emerald-200 dark:border-emerald-800 flex items-center justify-center text-xl">
            📊
          </div>
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">Radar de Lacunas</h2>
          <p className="text-sm text-slate-600 dark:text-slate-400 leading-normal">
            Mapeamento em tempo real dos temas com maior dúvida agregada na turma, com 100% de anonimização (Zero PII).
          </p>
        </div>

        <div className="rounded-xl bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 p-6 space-y-3 hover:border-indigo-500/40 shadow-xs dark:shadow-none transition-all">
          <div className="w-10 h-10 rounded-lg bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 flex items-center justify-center text-xl">
            🃏
          </div>
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">Flashcards de Fixação</h2>
          <p className="text-sm text-slate-600 dark:text-slate-400 leading-normal">
            O aluno transforma qualquer resposta do tutor em um flashcard interativo com repetição espaçada e níveis de domínio.
          </p>
        </div>
      </section>

      {/* Backend Health & Telemetry */}
      <section className="rounded-xl bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800/80 p-6 shadow-xs">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-4">
          Status dos Serviços do Cluster
        </h2>
        {result.ok ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
            <div className="bg-slate-50 dark:bg-slate-950/60 p-3 rounded-lg border border-slate-200 dark:border-slate-800">
              <span className="text-xs text-slate-500 block">Serviço</span>
              <span className="font-mono text-emerald-600 dark:text-emerald-400 font-medium">{result.meta.service}</span>
            </div>
            <div className="bg-slate-50 dark:bg-slate-950/60 p-3 rounded-lg border border-slate-200 dark:border-slate-800">
              <span className="text-xs text-slate-500 block">Versão</span>
              <span className="font-mono text-slate-800 dark:text-slate-300 font-medium">{result.meta.version}</span>
            </div>
            <div className="bg-slate-50 dark:bg-slate-950/60 p-3 rounded-lg border border-slate-200 dark:border-slate-800">
              <span className="text-xs text-slate-500 block">Ambiente</span>
              <span className="font-mono text-slate-800 dark:text-slate-300 font-medium">{result.meta.environment}</span>
            </div>
            <div className="bg-slate-50 dark:bg-slate-950/60 p-3 rounded-lg border border-slate-200 dark:border-slate-800">
              <span className="text-xs text-slate-500 block">OpenTelemetry Trace</span>
              <span className="font-mono text-xs text-slate-600 dark:text-slate-400 truncate block">
                {result.meta.trace_id ?? "amostragem ativa"}
              </span>
            </div>
          </div>
        ) : (
          <div role="alert" className="p-4 rounded-lg bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm">
            ⚠️ API offline ou inacessível: {result.message}
          </div>
        )}
      </section>
    </main>
  );
}
