import { context, propagation, trace } from "@opentelemetry/api";

type MetaResponse = {
  environment: string;
  service: string;
  trace_id: string | null;
  version: string;
};

type ApiMetaResult =
  | { ok: true; meta: MetaResponse }
  | { ok: false; message: string };

const apiBaseUrl = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

export async function getApiMeta(): Promise<ApiMetaResult> {
  const tracer = trace.getTracer("mentora-web");

  const operation = async (span: import("@opentelemetry/api").Span): Promise<ApiMetaResult> => {
    const carrier: Record<string, string> = {};
    propagation.inject(context.active(), carrier);

    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/meta`, {
        cache: "no-store",
        headers: carrier
      });
      span.setAttribute("http.response.status_code", response.status);

      if (!response.ok) {
        return { ok: false, message: `status HTTP ${response.status}` };
      }

      return { ok: true, meta: (await response.json()) as MetaResponse };
    } catch (error) {
      const message = error instanceof Error ? error.message : "erro desconhecido";
      span.recordException(error instanceof Error ? error : new Error(message));
      return { ok: false, message };
    } finally {
      span.end();
    }
  };

  return tracer.startActiveSpan("http.client GET /api/v1/meta", operation);
}
