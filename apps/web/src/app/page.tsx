import { getApiMeta } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const result = await getApiMeta();

  return (
    <main>
      <h1>Mentora AI</h1>
      <p>Em construção.</p>
      <p>
        <a href="/documents">Abrir biblioteca</a>
      </p>
      <p>
        <a href="/tutor">Abrir tutor</a>
      </p>
      {result.ok ? (
        <dl>
          <dt>API</dt>
          <dd>{result.meta.service}</dd>
          <dt>Versão</dt>
          <dd>{result.meta.version}</dd>
          <dt>Ambiente</dt>
          <dd>{result.meta.environment}</dd>
          <dt>Trace ID</dt>
          <dd>{result.meta.trace_id ?? "não amostrado"}</dd>
        </dl>
      ) : (
        <p role="alert">API indisponível: {result.message}</p>
      )}
    </main>
  );
}
