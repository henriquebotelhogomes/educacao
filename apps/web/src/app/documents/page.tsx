"use client";

import { ChangeEvent, FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";

type DocumentItem = {
  id: string;
  filename: string;
  status: string;
  error_message: string | null;
};

async function csrfToken(): Promise<string> {
  const response = await fetch("/api/v1/auth/csrf", { credentials: "include" });
  if (!response.ok) {
    throw new Error("Não foi possível preparar o upload.");
  }
  return (await response.json()).csrf_token as string;
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const loadDocuments = useCallback(async () => {
    const response = await fetch("/api/v1/documents", { credentials: "include" });
    if (response.status === 401) {
      setMessage("Faça login para acessar sua biblioteca de documentos.");
      return;
    }
    if (!response.ok) {
      setMessage("Não foi possível carregar os documentos.");
      return;
    }
    setDocuments((await response.json()) as DocumentItem[]);
  }, []);

  useEffect(() => {
    void loadDocuments();
    const interval = window.setInterval(() => void loadDocuments(), 4000);
    return () => window.clearInterval(interval);
  }, [loadDocuments]);

  async function submitUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setMessage("Por favor, selecione um arquivo PDF.");
      return;
    }

    setLoading(true);
    setMessage(null);
    try {
      const form = new FormData();
      form.set("file", file);
      const response = await fetch("/api/v1/documents", {
        method: "POST",
        credentials: "include",
        headers: { "X-CSRF-Token": await csrfToken() },
        body: form,
      });
      const payload = (await response.json()) as { detail?: string; message?: string };
      if (!response.ok) {
        setMessage(payload.message ?? payload.detail ?? "O upload não foi aceito.");
        return;
      }
      setFile(null);
      setMessage("Upload aceito! A indexação vetorial foi enfileirada.");
      await loadDocuments();
    } catch {
      setMessage("Falha de conexão ao enviar o documento.");
    } finally {
      setLoading(false);
    }
  }

  async function reprocess(documentId: string) {
    setMessage(null);
    try {
      const response = await fetch(`/api/v1/documents/${documentId}/reprocess`, {
        method: "POST",
        credentials: "include",
        headers: { "X-CSRF-Token": await csrfToken() },
      });
      if (!response.ok) {
        setMessage("Não foi possível reprocessar o documento.");
        return;
      }
      setMessage("Reprocessamento enfileirado com sucesso.");
      await loadDocuments();
    } catch {
      setMessage("Erro ao solicitar reprocessamento.");
    }
  }

  function getStatusBadge(status: string) {
    switch (status) {
      case "INDEXED":
        return { text: "✓ Indexado", cls: "bg-emerald-50 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800" };
      case "PROCESSING":
        return { text: "⏳ Processando", cls: "bg-blue-50 dark:bg-blue-950/80 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-800" };
      case "FAILED":
        return { text: "✕ Falhou", cls: "bg-red-50 dark:bg-red-950/80 text-red-700 dark:text-red-300 border-red-200 dark:border-red-800" };
      case "QUARANTINED":
        return { text: "⚠️ Quarentena", cls: "bg-amber-50 dark:bg-amber-950/80 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800" };
      default:
        return { text: status, cls: "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700" };
    }
  }

  return (
    <main className="space-y-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="border-b border-slate-200 dark:border-slate-800 pb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
            Biblioteca de Documentos
          </h1>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Envie materiais didáticos em PDF. A IA realiza a extração, chunking (512/64) e indexação vetorial com isolamento de tenant.
          </p>
        </div>
        <Link
          href="/tutor"
          className="inline-flex items-center px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-semibold border border-slate-200 dark:border-slate-700 transition-colors"
        >
          💬 Ir para o Tutor Livre →
        </Link>
      </div>

      {/* Message notification */}
      {message && (
        <div
          role="status"
          className="p-4 rounded-xl border border-indigo-200 dark:border-indigo-900/60 bg-indigo-50/70 dark:bg-indigo-950/50 text-indigo-900 dark:text-indigo-200 text-sm"
        >
          {message}
        </div>
      )}

      {/* Upload Card */}
      <section className="bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-xs dark:shadow-md space-y-4">
        <h2 className="text-lg font-bold text-slate-900 dark:text-white">Enviar Novo Documento</h2>
        <form onSubmit={submitUpload} className="space-y-4">
          <div>
            <label htmlFor="document" className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">
              Selecione o arquivo PDF da aula ou disciplina *
            </label>
            <input
              id="document"
              type="file"
              accept="application/pdf,.pdf"
              onChange={(event: ChangeEvent<HTMLInputElement>) =>
                setFile(event.target.files?.[0] ?? null)
              }
              className="block w-full text-sm text-slate-600 dark:text-slate-300 file:mr-4 file:py-2.5 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 dark:file:bg-indigo-950 file:text-indigo-700 dark:file:text-indigo-300 hover:file:bg-indigo-100 dark:hover:file:bg-indigo-900 file:cursor-pointer cursor-pointer border border-slate-300 dark:border-slate-700 rounded-xl p-2 bg-slate-50 dark:bg-slate-950"
            />
          </div>
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={loading || !file}
              className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold text-xs shadow-md shadow-indigo-600/20 transition-all"
            >
              {loading ? "Enviando arquivo..." : "Fazer Upload e Indexar"}
            </button>
          </div>
        </form>
      </section>

      {/* Document List */}
      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          Documentos Cadastrados ({documents.length})
        </h2>
        {documents.length === 0 ? (
          <div className="text-center py-12 rounded-2xl border border-dashed border-slate-300 dark:border-slate-800 p-8 space-y-2 bg-white dark:bg-transparent">
            <span className="text-4xl block">📚</span>
            <p className="text-slate-800 dark:text-slate-300 font-medium">Nenhum documento cadastrado ainda.</p>
            <p className="text-xs text-slate-500">Envie um arquivo PDF acima para alimentar o conhecimento do seu tutor.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-200 dark:divide-slate-800 bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-xs overflow-hidden">
            {documents.map((doc) => {
              const badge = getStatusBadge(doc.status);
              return (
                <div key={doc.id} className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">📄</span>
                      <strong className="text-slate-900 dark:text-white font-semibold text-sm">{doc.filename}</strong>
                    </div>
                    {doc.error_message && (
                      <p className="text-xs text-red-600 dark:text-red-400 pl-7">
                        Erro: {doc.error_message}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-3 self-end sm:self-center">
                    <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${badge.cls}`}>
                      {badge.text}
                    </span>
                    {(doc.status === "FAILED" || doc.status === "QUARANTINED") && (
                      <button
                        onClick={() => void reprocess(doc.id)}
                        type="button"
                        className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-medium border border-slate-300 dark:border-slate-700 transition-colors"
                      >
                        Reprocessar
                      </button>
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
