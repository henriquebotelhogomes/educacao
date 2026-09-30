"use client";

import { FormEvent, use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Classroom,
  createStudentFlashcard,
  fetchCsrfToken,
  getClassroom,
} from "@/lib/classes";

type Citation = {
  chunk_id: string;
  document_id: string;
  page: number;
  snippet: string;
  score: number;
};

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  confidence?: string;
  messageId?: string;
};

export default function ClassroomTutorPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: classroomId } = use(params);
  const [classroom, setClassroom] = useState<Classroom | null>(null);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputQuestion, setInputQuestion] = useState("");
  const [streamingResponse, setStreamingResponse] = useState("");
  const [streamingCitations, setStreamingCitations] = useState<Citation[]>([]);
  const [streamingConfidence, setStreamingConfidence] = useState<string | null>(null);
  const [streamingFallback, setStreamingFallback] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [statusText, setStatusText] = useState<string | null>(null);
  const [flashcardConcept, setFlashcardConcept] = useState("");
  const [flashcardExplanation, setFlashcardExplanation] = useState("");
  const [showFlashcardModal, setShowFlashcardModal] = useState(false);
  const [flashcardFeedback, setFlashcardFeedback] = useState<string | null>(null);

  const loadDetails = useCallback(async () => {
    try {
      const cls = await getClassroom(classroomId);
      setClassroom(cls);
    } catch {
      setStatusText("Falha ao carregar informações da turma.");
    }
  }, [classroomId]);

  useEffect(() => {
    void loadDetails();
  }, [loadDetails]);

  async function ensureThread(): Promise<string> {
    if (threadId) return threadId;
    const csrf = await fetchCsrfToken();
    const response = await fetch("/api/v1/chat/threads", {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrf,
      },
      body: JSON.stringify({ classroom_id: classroomId }),
    });
    if (!response.ok) {
      throw new Error("Não foi possível inicializar a conversa desta turma.");
    }
    const thread = (await response.json()) as { id: string };
    setThreadId(thread.id);
    return thread.id;
  }

  async function handleSend(e: FormEvent) {
    e.preventDefault();
    if (!inputQuestion.trim() || isStreaming) return;

    const userText = inputQuestion.trim();
    setInputQuestion("");
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: userText,
    };
    setMessages((prev) => [...prev, userMsg]);

    setStreamingResponse("");
    setStreamingCitations([]);
    setStreamingConfidence(null);
    setStreamingFallback(null);
    setIsStreaming(true);
    setStatusText(null);

    try {
      const id = await ensureThread();
      const csrf = await fetchCsrfToken();
      const response = await fetch(`/api/v1/chat/threads/${id}/messages`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrf,
        },
        body: JSON.stringify({ content: userText }),
      });

      if (!response.body) {
        throw new Error("O stream da resposta não pôde ser iniciado.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let fullAssistantText = "";
      let citationsReceived: Citation[] = [];
      let finalConfidence: string | undefined = undefined;
      let finalMsgId: string | undefined = undefined;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() ?? "";

        for (const raw of events) {
          const typeMatch = raw.match(/^event: (.+)$/m);
          const dataMatch = raw.match(/^data: (.+)$/m);
          if (!typeMatch || !dataMatch) continue;

          const type = typeMatch[1];
          const data = JSON.parse(dataMatch[1]) as Record<string, unknown>;

          if (type === "token") {
            const token = String(data.token ?? "");
            fullAssistantText += token;
            setStreamingResponse((prev) => prev + token);
          } else if (type === "citations") {
            citationsReceived = (data.citations ?? []) as Citation[];
            setStreamingCitations(citationsReceived);
          } else if (type === "confidence") {
            finalConfidence = String(data.band ?? "");
            setStreamingConfidence(finalConfidence);
          } else if (type === "fallback") {
            setStreamingFallback(String(data.message ?? ""));
          } else if (type === "complete") {
            finalMsgId = String(data.message_id ?? "");
          } else if (type === "error") {
            setStatusText(String(data.message ?? "Erro no tutor."));
          }
        }
      }

      // Add assistant response to messages
      if (fullAssistantText) {
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: fullAssistantText,
            citations: citationsReceived,
            confidence: finalConfidence,
            messageId: finalMsgId,
          },
        ]);
      }
    } catch (err) {
      setStatusText(err instanceof Error ? err.message : "Erro ao consultar tutor.");
    } finally {
      setIsStreaming(false);
      setStreamingResponse("");
    }
  }

  async function handleFeedback(messageId: string, rating: 1 | -1) {
    try {
      const csrf = await fetchCsrfToken();
      await fetch("/api/v1/feedback", {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrf,
        },
        body: JSON.stringify({ message_id: messageId, rating }),
      });
      setStatusText(rating === 1 ? "Obrigado! Feedback positivo registrado." : "Feedback registrado. Revisaremos este tópico!");
      setTimeout(() => setStatusText(null), 3000);
    } catch {
      setStatusText("Falha ao registrar feedback.");
    }
  }

  function openSaveFlashcard(content: string) {
    setFlashcardConcept(inputQuestion.slice(0, 80) || "Conceito Principal");
    setFlashcardExplanation(content);
    setShowFlashcardModal(true);
    setFlashcardFeedback(null);
  }

  async function handleSaveFlashcard(e: FormEvent) {
    e.preventDefault();
    if (!flashcardConcept.trim() || !flashcardExplanation.trim()) return;

    try {
      await createStudentFlashcard(classroomId, {
        concept: flashcardConcept.trim(),
        explanation: flashcardExplanation.trim(),
      });
      setFlashcardFeedback("✓ Flashcard salvo no seu deck desta turma!");
      setTimeout(() => {
        setShowFlashcardModal(false);
        setFlashcardFeedback(null);
      }, 2000);
    } catch {
      setFlashcardFeedback("Erro ao salvar flashcard.");
    }
  }

  const isSocratic = classroom?.pedagogical_mode === "SOCRATIC";

  return (
    <main className="max-w-4xl mx-auto space-y-6">
      {/* Header with Navigation & Pedagogical Badge */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mb-1">
            <Link href="/classes" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">
              ← Todas as Turmas
            </Link>
            <span>/</span>
            <span>{classroom?.subject ?? "Geral"}</span>
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white flex items-center gap-2">
            <span>{classroom ? classroom.name : "Carregando Turma..."}</span>
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href={`/classes/${classroomId}/flashcards`}
            className="px-3.5 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-medium border border-slate-300 dark:border-slate-700 transition-colors flex items-center gap-1.5"
          >
            <span>🃏</span> Meus Flashcards
          </Link>
          {classroom && (classroom.my_role === "EDUCATOR" || classroom.my_role === "ADMIN") && (
            <Link
              href={`/classes/${classroomId}/educator`}
              className="px-3.5 py-1.5 rounded-lg bg-purple-50 hover:bg-purple-100 dark:bg-purple-950 dark:hover:bg-purple-900 border border-purple-200 dark:border-purple-800 text-purple-700 dark:text-purple-200 text-xs font-semibold transition-colors flex items-center gap-1.5"
            >
              <span>📊</span> Painel do Educador
            </Link>
          )}
        </div>
      </div>

      {/* Pedagogical Mode Banner */}
      <div
        className={`p-4 rounded-2xl border flex items-start gap-3 transition-colors ${
          isSocratic
            ? "bg-indigo-50/80 dark:bg-indigo-950/40 border-indigo-200 dark:border-indigo-800 text-indigo-900 dark:text-indigo-200"
            : "bg-slate-50 dark:bg-slate-900/60 border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-300"
        }`}
      >
        <span className="text-2xl">{isSocratic ? "🦉" : "📖"}</span>
        <div className="space-y-0.5">
          <h2 className="text-sm font-bold text-slate-900 dark:text-white">
            {isSocratic
              ? "Modo Socrático Ativo (Configurado pelo Educador)"
              : "Modo Explicação Direta (Configurado pelo Educador)"}
          </h2>
          <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
            {isSocratic
              ? "O tutor não entregará respostas prontas ou gabaritos. Ele fará perguntas investigativas, indicará trechos dos textos e ajudará você a raciocinar até a solução!"
              : "O tutor fornecerá explicações conceituais claras e estruturadas com base nos textos e documentos indicados pelo professor da turma."}
          </p>
        </div>
      </div>

      {/* Status Alert */}
      {statusText && (
        <div role="status" className="p-3 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs text-slate-800 dark:text-slate-300">
          {statusText}
        </div>
      )}

      {/* Fallback Alert if context is insufficient */}
      {streamingFallback && (
        <div role="alert" className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/50 border border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-300 text-xs">
          ⚠️ {streamingFallback}
        </div>
      )}

      {/* Chat Messages Container */}
      <div className="space-y-4 min-h-[300px]">
        {messages.length === 0 && !isStreaming && (
          <div className="text-center py-16 rounded-2xl border border-dashed border-slate-300 dark:border-slate-800 p-8 space-y-2 bg-white dark:bg-transparent">
            <span className="text-3xl block">💡</span>
            <p className="text-slate-800 dark:text-slate-300 font-medium">Nenhuma dúvida registrada nesta turma ainda.</p>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              Digite sua pergunta abaixo. O tutor responderá estritamente fundamentado no material didático cadastrado pelo professor.
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`p-5 rounded-2xl shadow-xs ${
              msg.role === "user"
                ? "bg-indigo-50 dark:bg-slate-900 border border-indigo-100 dark:border-slate-800 ml-auto max-w-2xl text-slate-900 dark:text-slate-100"
                : "bg-white dark:bg-slate-900/90 border border-slate-200 dark:border-indigo-950 mr-auto max-w-3xl space-y-3"
            }`}
          >
            <div className="flex items-center justify-between text-[11px] font-semibold tracking-wider text-slate-500 dark:text-slate-400 uppercase">
              <span>{msg.role === "user" ? "Sua Dúvida" : "Tutor Mentora AI"}</span>
              {msg.confidence && (
                <span className="px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-indigo-700 dark:text-indigo-300 text-[10px]">
                  Confiança: {msg.confidence}
                </span>
              )}
            </div>

            <p className="text-sm text-slate-800 dark:text-slate-200 whitespace-pre-wrap leading-relaxed">
              {msg.content}
            </p>

            {/* Citations block */}
            {msg.citations && msg.citations.length > 0 && (
              <div className="pt-3 border-t border-slate-100 dark:border-slate-800/80 space-y-1.5">
                <span className="text-[11px] font-bold text-slate-500 dark:text-slate-400 block uppercase">
                  📖 Evidências Citadas:
                </span>
                <div className="space-y-1">
                  {msg.citations.map((c) => (
                    <div
                      key={c.chunk_id}
                      className="p-2 rounded-lg bg-slate-50 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800/80 text-xs text-slate-700 dark:text-slate-300"
                    >
                      <span className="font-semibold text-indigo-600 dark:text-indigo-400">Pág. {c.page}:</span>{" "}
                      <span className="text-slate-600 dark:text-slate-400 italic font-mono text-[11px]">
                        &ldquo;{c.snippet}&rdquo;
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Actions: Feedback & Save as Flashcard */}
            {msg.role === "assistant" && (
              <div className="pt-3 border-t border-slate-100 dark:border-slate-800/60 flex flex-wrap items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-2">
                  <span className="text-slate-500 text-[11px]">Esta resposta ajudou?</span>
                  {msg.messageId && (
                    <>
                      <button
                        onClick={() => void handleFeedback(msg.messageId!, 1)}
                        className="px-2 py-1 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300"
                        title="Útil"
                        type="button"
                      >
                        👍
                      </button>
                      <button
                        onClick={() => void handleFeedback(msg.messageId!, -1)}
                        className="px-2 py-1 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300"
                        title="Não foi útil (registra lacuna de aprendizagem)"
                        type="button"
                      >
                        👎
                      </button>
                    </>
                  )}
                </div>

                <button
                  onClick={() => openSaveFlashcard(msg.content)}
                  type="button"
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-950/80 hover:bg-indigo-100 dark:hover:bg-indigo-900 border border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-200 text-xs font-semibold transition-colors"
                >
                  <span>🃏</span> Salvar como Flashcard
                </button>
              </div>
            )}
          </div>
        ))}

        {/* Live Streaming Message Box */}
        {isStreaming && (
          <div className="p-5 rounded-2xl bg-white dark:bg-slate-900/90 border border-indigo-200 dark:border-indigo-900/80 mr-auto max-w-3xl space-y-3 shadow-md">
            <div className="flex items-center justify-between text-[11px] font-semibold tracking-wider text-indigo-600 dark:text-indigo-400 uppercase">
              <span className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-indigo-600 animate-ping" />
                Tutor Mentora AI (Respondendo...)
              </span>
              {streamingConfidence && (
                <span className="px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-indigo-700 dark:text-indigo-300 text-[10px]">
                  Confiança: {streamingConfidence}
                </span>
              )}
            </div>
            <p className="text-sm text-slate-800 dark:text-slate-200 whitespace-pre-wrap leading-relaxed">
              {streamingResponse || "Analisando referências documentais..."}
            </p>

            {streamingCitations.length > 0 && (
              <div className="pt-3 border-t border-slate-100 dark:border-slate-800 space-y-1">
                <span className="text-[11px] font-bold text-slate-500 dark:text-slate-400 block uppercase">
                  📖 Evidências identificadas ({streamingCitations.length}):
                </span>
                <div className="space-y-1">
                  {streamingCitations.map((c) => (
                    <div
                      key={c.chunk_id}
                      className="p-1.5 rounded bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs text-slate-600 dark:text-slate-400"
                    >
                      Pág. {c.page}: &ldquo;{c.snippet.slice(0, 100)}...&rdquo;
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Question Input Form */}
      <form onSubmit={handleSend} className="space-y-3 pt-4 border-t border-slate-200 dark:border-slate-800">
        <label htmlFor="studentQuestion" className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
          Sua dúvida sobre o conteúdo da turma
        </label>
        <div className="relative">
          <textarea
            id="studentQuestion"
            rows={3}
            value={inputQuestion}
            onChange={(e) => setInputQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void handleSend(e);
              }
            }}
            placeholder={
              isSocratic
                ? "Ex: Por que a rotação de culturas melhora a retenção de nitrogênio no solo?"
                : "Ex: Explique o conceito de sucessão ecológica primária."
            }
            className="w-full p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 placeholder:text-slate-400 dark:placeholder:text-slate-600 resize-none pr-32 shadow-xs"
          />
          <button
            type="submit"
            disabled={isStreaming || !inputQuestion.trim()}
            className="absolute right-3 bottom-4 px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold text-xs shadow-md transition-all"
          >
            {isStreaming ? "Aguarde..." : "Perguntar ➔"}
          </button>
        </div>
        <p className="text-[11px] text-slate-500">
          Dica: Pressione <kbd className="px-1 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 font-mono">Enter</kbd> para enviar ou <kbd className="px-1 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 font-mono">Shift + Enter</kbd> para nova linha.
        </p>
      </form>

      {/* Save Flashcard Modal */}
      {showFlashcardModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-indigo-900/80 rounded-2xl p-6 max-w-lg w-full space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <span>🃏</span> Salvar Flashcard na Turma
              </h3>
              <button
                onClick={() => setShowFlashcardModal(false)}
                type="button"
                className="text-slate-400 hover:text-slate-600 dark:hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            {flashcardFeedback ? (
              <div className="p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/80 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300 text-sm font-medium text-center">
                {flashcardFeedback}
              </div>
            ) : (
              <form onSubmit={handleSaveFlashcard} className="space-y-4">
                <div>
                  <label htmlFor="concept" className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Frente: Pergunta ou Conceito Chave *
                  </label>
                  <input
                    id="concept"
                    type="text"
                    required
                    value={flashcardConcept}
                    onChange={(e) => setFlashcardConcept(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label htmlFor="explanation" className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Verso: Resposta ou Explicação *
                  </label>
                  <textarea
                    id="explanation"
                    rows={4}
                    required
                    value={flashcardExplanation}
                    onChange={(e) => setFlashcardExplanation(e.target.value)}
                    className="w-full p-3 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div className="pt-2 flex justify-end gap-3">
                  <button
                    type="button"
                    onClick={() => setShowFlashcardModal(false)}
                    className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs border border-slate-200 dark:border-slate-700"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-xs"
                  >
                    Salvar Flashcard
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </main>
  );
}
