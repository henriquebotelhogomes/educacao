import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import { resourceFromAttributes } from "@opentelemetry/resources";
import { BatchSpanProcessor } from "@opentelemetry/sdk-trace-base";
import { NodeTracerProvider } from "@opentelemetry/sdk-trace-node";
import { ATTR_SERVICE_NAME } from "@opentelemetry/semantic-conventions";

let registered = false;

export function registerServerTelemetry(): void {
  if (registered) {
    return;
  }

  const exporter = new OTLPTraceExporter({
    url:
      process.env.OTEL_EXPORTER_OTLP_TRACES_ENDPOINT ??
      "http://localhost:4318/v1/traces"
  });
  const provider = new NodeTracerProvider({
    resource: resourceFromAttributes({
      [ATTR_SERVICE_NAME]: "mentora-web"
    }),
    spanProcessors: [new BatchSpanProcessor(exporter)]
  });

  provider.register();
  registered = true;
  console.info("mentora-web telemetry initialized");
}
