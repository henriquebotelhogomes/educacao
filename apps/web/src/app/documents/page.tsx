"use client";

import { ChangeEvent, FormEvent, useCallback, useEffect, useState } from "react";

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
      setMessage("Faça login para acessar sua biblioteca.");
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
    const interval = window.setInterval(() => void loadDocuments(), 3000);
    return () => window.clearInterval(interval);
  }, [loadDocuments]);

  async function submitUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setMessage("Selecione um PDF.");
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
        body: form
      });
      const payload = (await response.json()) as { detail?: string; message?: string };
      if (!response.ok) {
        setMessage(payload.message ?? "O upload não foi aceito.");
        return;
      }
      setFile(null);
      setMessage("Upload aceito. A indexação foi iniciada.");
      await loadDocuments();
    } finally {
      setLoading(false);
    }
  }

  async function reprocess(documentId: string) {
    setMessage(null);
    const response = await fetch(`/api/v1/documents/${documentId}/reprocess`, {
      method: "POST",
      credentials: "include",
      headers: { "X-CSRF-Token": await csrfToken() }
    });
    if (!response.ok) {
      setMessage("Não foi possível reprocessar o documento.");
      return;
    }
    setMessage("Reprocessamento enfileirado.");
    await loadDocuments();
  }

  return (
    <main>
      <h1>Minha biblioteca</h1>
      <p>Envie PDFs para a Mentora AI indexar de forma segura.</p>

      <form onSubmit={submitUpload}>
        <label htmlFor="document">PDF</label>
        <input
          accept="application/pdf,.pdf"
          id="document"
          onChange={(event: ChangeEvent<HTMLInputElement>) =>
            setFile(event.target.files?.[0] ?? null)
          }
          type="file"
        />
        <button disabled={loading} type="submit">
          {loading ? "Enviando..." : "Enviar PDF"}
        </button>
      </form>

      {message ? <p role="status">{message}</p> : null}

      <h2>Documentos</h2>
      {documents.length === 0 ? <p>Nenhum documento enviado.</p> : null}
      <ul>
        {documents.map((document) => (
          <li key={document.id}>
            <strong>{document.filename}</strong> — {document.status}
            {document.error_message ? <p>Falha: {document.error_message}</p> : null}
            {document.status === "FAILED" || document.status === "QUARANTINED" ? (
              <button onClick={() => void reprocess(document.id)} type="button">
                Reprocessar
              </button>
            ) : null}
          </li>
        ))}
      </ul>
    </main>
  );
}
