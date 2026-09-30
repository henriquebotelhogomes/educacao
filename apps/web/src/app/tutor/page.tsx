"use client";

import { FormEvent, useState } from "react";

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

  async function ensureThread(): Promise<string> {
    if (threadId) return threadId;
    const response = await fetch("/api/v1/chat/threads", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": await csrfToken() },
      body: JSON.stringify({})
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
    setStatus("Consultando seu material...");

    try {
      const id = await ensureThread();
      const response = await fetch(`/api/v1/chat/threads/${id}/messages`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": await csrfToken() },
        body: JSON.stringify({ content: question })
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
    await fetch("/api/v1/feedback", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": await csrfToken() },
      body: JSON.stringify({ message_id: messageId, rating })
    });
    setStatus("Feedback registrado.");
  }

  return (
    <main>
      <h1>Tutor</h1>
      <p>Pergunte apenas sobre o material que você carregou.</p>
      <form onSubmit={ask}>
        <label htmlFor="question">Sua dúvida</label>
        <textarea
          id="question"
          onChange={(event) => setQuestion(event.target.value)}
          value={question}
        />
        <button type="submit">Perguntar</button>
      </form>
      {status ? <p role="status">{status}</p> : null}
      {fallback ? <p role="alert">{fallback} <a href="/documents">Carregar material</a></p> : null}
      {answer ? <article><p>{answer}</p></article> : null}
      {confidence ? <p>Confiança: {confidence}</p> : null}
      {citations.length > 0 ? (
        <aside>
          <h2>Fontes</h2>
          <ol>
            {citations.map((citation) => (
              <li key={citation.chunk_id}>
                Página {citation.page}: {citation.snippet}
              </li>
            ))}
          </ol>
        </aside>
      ) : null}
      {messageId ? (
        <p>
          Esta resposta foi útil?{" "}
          <button onClick={() => void feedback(1)} type="button">👍</button>{" "}
          <button onClick={() => void feedback(-1)} type="button">👎</button>
        </p>
      ) : null}
    </main>
  );
}
