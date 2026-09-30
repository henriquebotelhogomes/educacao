"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";

type Citation = {
  chunk_id: string;
  document_id: string;
  page: number;
  snippet: string;
  score: number;
};

async function csrfToken(): Promise<string> {
  const response = await fetch("/api/v1/auth/csrf", { credentials: "include" });
  return ((await response.json()) as { csrf_token: string }).csrf_token;
}

export default function TutorPage() {
  const [threadId, setThreadId] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [confidence, setConfidence] = useState<string | null>(null);
  const [fallback, setFallback] = useState<string | null>(null);
  const [messageId, setMessageId] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [feedbackSent, setFeedbackSent] = useState(false);

  async function ensureThread(): Promise<string> {
    if (threadId) return threadId;
    const response = await fetch("/api/v1/chat/threads", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": await csrfToken() },
      body: JSON.stringify({}),
    });
    if (!response.ok) throw new Error("Carregue um documento antes de usar o tutor.");
    const thread = (await response.json()) as { id: string };
    setThreadId(thread.id);
    return thread.id;
  }

  async function ask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!question.trim()) return;
    setAnswer("");
    setCitations([]);
    setConfidence(null);
    setFallback(null);
    setMessageId(null);
    setFeedbackSent(false);
    setStatus("Consultando seu material...");

    try {
      const id = await ensureThread();
      const response = await fetch(`/api/v1/chat/threads/${id}/messages`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": await csrfToken() },
        body: JSON.stringify({ content: question }),
      });
      if (!response.body) throw new Error("O stream do tutor não foi iniciado.");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() ?? "";
        for (const raw of events) {
          const type = raw.match(/^event: (.+)$/m)?.[1];
          const rawData = raw.match(/^data: (.+)$/m)?.[1];
          if (!type || !rawData) continue;
          const data = JSON.parse(rawData) as Record<string, unknown>;
          if (type === "token") setAnswer((current) => current + String(data.token));
          if (type === "citations") setCitations(data.citations as Citation[]);
          if (type === "confidence") setConfidence(String(data.band));
          if (type === "fallback") setFallback(String(data.message));
          if (type === "complete") setMessageId(String(data.message_id ?? ""));
          if (type === "error") setStatus(String(data.message));
        }
      }
      setStatus(null);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "O tutor não pôde responder.");
    }
  }

  async function feedback(rating: 1 | -1) {
    if (!messageId) return;
    try {
      await fetch("/api/v1/feedback", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": await csrfToken() },
        body: JSON.stringify({ message_id: messageId, rating }),
      });
      setFeedbackSent(true);
      setStatus("Obrigado pelo feedback!");
    } catch {
      setStatus("Falha ao registrar feedback.");
    }
  }

  return (
    <main className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="border-b border-slate-200 dark:border-slate-800 pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
            <span>💬</span> Tutor Livre
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Tire dúvidas estritamente fundamentadas no acervo de documentos indexados da sua conta.
          </p>
        </div>
        <Link
          href="/documents"
          className="inline-flex items-center px-3.5 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-medium border border-slate-300 dark:border-slate-700 transition-colors"
        >
          📚 Gerenciar PDFs
        </Link>
      </div>

      {/* Question Form */}
      <section className="bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-xs dark:shadow-md space-y-4">
        <form onSubmit={ask} className="space-y-4">
          <div>
            <label htmlFor="question" className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">
              Qual é sua dúvida sobre os materiais?
            </label>
            <textarea
              id="question"
              rows={3}
              required
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ex: Quais são as principais etapas da mitose descritas na apostila?"
              className="w-full px-4 py-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 placeholder:text-slate-400"
            />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500">Fundamentação RAG Híbrida (E5-small + Re-ranking)</span>
            <button
              type="submit"
              className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs shadow-md shadow-indigo-600/20 transition-all hover:scale-[1.01]"
            >
              Perguntar ao Tutor
            </button>
          </div>
        </form>
      </section>

      {/* Status banner */}
      {status && (
        <div
          role="status"
          className="p-3.5 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 text-xs font-medium"
        >
          {status}
        </div>
      )}

      {/* Fallback alert */}
      {fallback && (
        <div
          role="alert"
          className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/50 border border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-200 text-xs flex items-center justify-between"
        >
          <span>⚠️ {fallback}</span>
          <Link href="/documents" className="font-semibold underline ml-2">
            Carregar material
          </Link>
        </div>
      )}

      {/* Answer & Citations Box */}
      {answer && (
        <article className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-5 animate-in fade-in">
          <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-md bg-indigo-600 flex items-center justify-center text-white text-xs font-bold">
                M
              </span>
              <span className="text-xs font-semibold text-slate-900 dark:text-white">Resposta do Tutor Mentora</span>
            </div>
            {confidence && (
              <span className="px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                Confiança: {confidence}
              </span>
            )}
          </div>

          <div className="text-sm text-slate-800 dark:text-slate-200 leading-relaxed whitespace-pre-wrap">
            {answer}
          </div>

          {/* Citations */}
          {citations.length > 0 && (
            <aside className="border-t border-slate-100 dark:border-slate-800 pt-4 space-y-2">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Evidências & Trechos Citados ({citations.length})
              </h2>
              <div className="space-y-2">
                {citations.map((c) => (
                  <div
                    key={c.chunk_id}
                    className="p-3 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs text-slate-600 dark:text-slate-400"
                  >
                    <span className="font-semibold text-indigo-600 dark:text-indigo-400 block mb-1">
                      📄 Documento (Página {c.page}) — Relevância: {(c.score * 100).toFixed(0)}%
                    </span>
                    <p className="italic font-serif">&ldquo;{c.snippet}&rdquo;</p>
                  </div>
                ))}
              </div>
            </aside>
          )}

          {/* Feedback buttons */}
          {messageId && !feedbackSent && (
            <div className="flex items-center justify-between border-t border-slate-100 dark:border-slate-800 pt-3 text-xs text-slate-500">
              <span>Esta resposta foi útil?</span>
              <div className="flex gap-2">
                <button
                  onClick={() => void feedback(1)}
                  type="button"
                  className="px-3 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-emerald-50 dark:hover:bg-emerald-950/50 hover:text-emerald-600 text-slate-700 dark:text-slate-300 transition-colors"
                >
                  👍 Útil
                </button>
                <button
                  onClick={() => void feedback(-1)}
                  type="button"
                  className="px-3 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-red-50 dark:hover:bg-red-950/50 hover:text-red-600 text-slate-700 dark:text-slate-300 transition-colors"
                >
                  👎 Não ajudou
                </button>
              </div>
            </div>
          )}
        </article>
      )}
    </main>
  );
}
