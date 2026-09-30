# Spec 03 — Especificação Técnica (stack, contratos, NFRs, segurança, observabilidade)

> **Documento:** `specs/03-technical-spec.md` · **Status:** RASCUNHO RECONSTRUÍDO (esqueleto) · **Data:** 2026-08-30
> **Nota de proveniência:** o original **foi perdido** (nunca existiu no histórico git). O `PRD.md`
> mapeia "Stack, contratos, NFRs, segurança, observabilidade, UX" para a faixa `specs/03`–`09`;
> deste conjunto apenas **03** e **09** estão sendo re-esqueletados agora — **04 a 08 não foram
> reconstruídos** e sua numeração/temas originais são **IRRECUPERÁVEIS**.
> A **verdade de arquitetura** do repositório vive em [`12-execution-plan.md`](./12-execution-plan.md)
> §1; este esqueleto aponta para ela em vez de duplicá-la. Decisões técnicas vivem nos ADRs em
> [`11-risks-assumptions-adr.md`](./11-risks-assumptions-adr.md).

---

## 1) Stack (fundamentado no código e em `specs/12` §1)

| Camada | Tecnologia | Evidência |
|---|---|---|
| API | FastAPI (pacote `mentora-api`, módulo `tutor_ai`), config tipada `pydantic-settings` | `apps/api` |
| Persistência | Postgres + RLS; SQLModel/SQLAlchemy + Alembic (4 revisões) | `specs/12` §1.3 |
| Fila | Redis Streams com outbox, XAUTOCLAIM, DLQ | ADR-017; `specs/12` §1.4 |
| Vetores | Qdrant, coleção compartilhada `multilingual-e5-small_v1` com filtro forçado de tenant | ADR-011 |
| Objetos | MinIO (S3-compatible) | `apps/api/src/tutor_ai/documents/storage.py` |
| Ingestão | Docling → chunking estrutural 512/64 → embeddings | ADR-012 |
| Embedding | `intfloat/multilingual-e5-small` (384 dim, prefixos `query:`/`passage:`) | ADR-018, ADR-021 |
| LLM | Groq `llama-3.3-70b-versatile` (tutor e judge de evals) | `platform/config.py`; `PRD` §13.4 |
| Frontend | Next.js App Router (`@mentora/web`) | `apps/web` |
| Contratos | OpenAPI exportado → `openapi-typescript` → `packages/contracts/schema.d.ts` | job `contracts` do CI |
| Tooling | uv workspace (`apps/api`, `apps/worker`, `legacy/streamlit`), npm workspaces | `pyproject.toml`, `package.json` |

## 2) Contratos de API (fundamentado)

- Fonte de verdade do contrato: o OpenAPI gerado pelo FastAPI (`tutor_ai.export_openapi`).
- Pipeline: `npm run contracts:generate` regenera `packages/contracts/openapi.json` e
  `schema.d.ts`; o CI falha se houver diff (`git diff --exit-code`).
- Autenticação por **cookie httpOnly** + token CSRF (ADR-015); nunca bearer token no V1.
- Catálogo de endpoints: `specs/12` §1.1.

## 3) NFRs

Texto original de NFRs: **IRRECUPERÁVEL**. Âncoras mensuráveis sobreviventes:

| NFR | Valor fundamentado | Fonte |
|---|---|---|
| Latência do tutor | Streaming token a token é `MUST` (sem ele a latência é inaceitável) | PRD §3 (C5) |
| Tempo de encoding | p95 121,1 ms (E5-small, CPU) | `evals/reports/adr-018-embedding-v1.md` |
| Recall@10 retrieval | 0,8222 com estrutural 512/64 + E5-small | `evals/reports/adr-012-chunking-v1.md` |
| Tamanho de arquivo | 10 MB (Free) / 50 MB (Pro); configurável `document_max_size_bytes` | PRD §5; `platform/config.py` |
| Disponibilidade | `/healthz` sem dependências; `/readyz` com TCP-probe de Postgres/Redis/Qdrant/MinIO | `main.py`; `specs/12` §1.1 |

> Metas originais de disponibilidade, escalabilidade e capacidade: **IRRECUPERÁVEL**.

## 4) Segurança (fundamentado)

- **AuthN:** cookie `httpOnly` + refresh rotativo em Redis; Google OAuth com `state` vinculado ao
  navegador (remediação P1 do Marco 3). ADR-015.
- **CSRF:** middleware dedicado (`platform/csrf.py`).
- **AuthZ:** RBAC por papéis (`specs/12` §4.2) + **RLS no Postgres** com
  `mentora_current_tenant_id()`; testes negativos cross-tenant precederam armazenamento real
  (Marco 1).
- **Isolamento vetorial:** filtro de tenant forçado em toda busca (ADR-011); point IDs
  determinísticos (UUID5).
- **Upload:** validação de MIME/tamanho/cota; hash SHA-256 para deduplicação idempotente; scan
  EICAR provisório (ADR-022).
- **Segredos:** `SecretStr` em config; `MENTORA_COOKIE_SECURE` não pode ser `false` fora de
  development/test (`platform/config.py`).

## 5) Observabilidade (fundamentado)

- Logs JSON com `request_id`/`trace_id` (`platform/logging.py`); OpenTelemetry com export OTLP
  (`platform/telemetry.py`).
- Stack local: OTel Collector + Grafana/Tempo/Loki/Prometheus (`infra/compose`).
- **Langfuse** para evals com **redação de conteúdo bruto** — apenas metadados e métricas
  agregadas (ADR-014).
- Metering de custo: `usage_event` persistido; cota mensal reservada **antes** da chamada ao LLM
  (AC-05; remediação P1).

## 6) Exemplo superseded conhecido

O exemplo original de exibição de confiança deste documento (percentual) foi superseded por
`PRD` **D3** — banda `Alta/Média/Baixa`, nunca percentual.

## 7) Lacunas conhecidas deste rascunho

| Item | Estado |
|---|---|
| NFRs originais (disponibilidade, escala, capacidade) | **IRRECUPERÁVEL** |
| Conteúdo e temas de `specs/04`–`specs/08` | **IRRECUPERÁVEL**; não reconstruídos |
| Diagramas de arquitetura originais | **IRRECUPERÁVEL** (topologia textual em `specs/12` §1) |

## Registro de mudanças

| Versão | Data | Mudança |
|---|---|---|
| rascunho-v0 | 2026-08-30 | Esqueleto reconstruído do zero a partir de evidência (PRD v1.7, specs 11/12, código). |
