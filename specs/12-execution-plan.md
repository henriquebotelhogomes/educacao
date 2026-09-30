# Spec 12 — Plano de Execução (Arquitetura física, marcos, gates)

> **Documento:** `specs/12-execution-plan.md` · **Status:** RECONSTRUÍDO · **Data:** 2026-08-30
> **Nota de proveniência:** o original **foi perdido** (nunca existiu no histórico git). Esta versão
> foi reconstruída **do zero** a partir apenas de evidência sobrevivente: código em `apps/`, `infra/`,
> `evals/`, `.github/`, `.importlinter`, o dataset dourado e o `PRD.md`. Seções cujo conteúdo original
> era esforço/custo/estimativa estão marcadas **IRRECUPERÁVEL** e não foram inventadas.
> **Precedência** (`PRD.md` §10): sobre arquitetura e execução, este documento prevalece; sobre
> decisões técnicas, os ADRs em `specs/11`.

---

## 0) Estado dos marcos (controle espelhado do `PRD.md` §11)

| Marco | Estado | Evidência |
|---|---|---|
| 0.5 Higiene do repositório | ✅ | `pyproject.toml`, `uv.lock`, ruff/mypy/pre-commit, `import-linter` |
| 0 Fundação reproduzível | ✅ | workspace uv; `apps/{api,web,worker}`; `infra/compose`; CI |
| 1 Identidade e isolamento | ✅ | modelos `tenant/user/membership`; cookie httpOnly; RBAC; RLS; testes cross-tenant |
| 2 Documentos (walking skeleton) | ✅ | upload S3/MinIO + SHA-256 + outbox; Redis Streams; worker Docling idempotente |
| 3 Tutor confiável | ✅ | threads; retrieval tenant-safe; citações por chunk id; banda; fallback; SSE; feedback |
| 3.5 Calibração baseada em evidência | 🟡 parcial | ADR-018/012 ratificados; RAG Triad provisória (4 casos); **ADR-009 bloqueado** |
| 4 Gerador profissional | ⬜ | exercícios com grounding; exportação DOCX |

> **`packages/contracts` (resolvido em 2026-08-30):** o pacote foi reconstruído
> (`package.json`, `openapi.json`, `schema.d.ts` regenerados); geração verificada determinística
> e `npm ci` restaura o workspace sem drift de lock. Resta apenas versionar os artefatos para o
> gate `git diff --exit-code` do CI deixar de ser vacuamente verdadeiro.

---

## 1) Arquitetura implementada (verdade do repositório)

### 1.1 Topologia de serviços

- **`apps/api`** — FastAPI (service `mentora-api`). Config tipada, logs JSON, OpenTelemetry,
  Alembic, `import-linter`. Endpoints:
  - `GET /healthz`, `GET /readyz` (TCP-probe de postgres/redis/qdrant/minio), `GET /api/v1/meta`
  - Identidade: `GET /api/v1/auth/csrf`, `POST /signup`, `POST /signin`, `POST /refresh`,
    `POST /logout`, `GET /oauth/google`, `GET /oauth/google/callback`
  - Tenancy: `GET /api/v1/tenants/current`, `/current/membership`, `/current/audit-log`
  - Documentos: `POST /api/v1/documents`, `GET /api/v1/documents`,
    `GET /api/v1/documents/{id}/status`, `POST /api/v1/documents/{id}/reprocess`,
    `DELETE /api/v1/documents/{id}` (soft delete)
  - Tutor: `POST /api/v1/chat/threads`, `GET /api/v1/chat/threads`,
    `POST /api/v1/chat/threads/{id}/messages` (**SSE**), `POST /api/v1/feedback`
- **`apps/worker`** — consumidor de ingestão (Docling → chunking → embeddings → Qdrant) +
  dispatcher outbox.
- **`apps/web`** — Next.js App Router (`page.tsx`, `documents/page.tsx`, `tutor/page.tsx`),
  consumindo `/api/v1/meta`.
- **`legacy/streamlit`** — protótipo isolado em coleção `legacy_*`; mantido só para referência.

### 1.2 Infra (`infra/compose`)

Postgres, Redis, Qdrant, MinIO, OTel Collector e stack Grafana/Tempo/Loki/Prometheus com
healthchecks. Variáveis em `.env.example` ( portas: API 8000, web 3001→3000, Postgres 5433, etc.).

### 1.3 Persistência (Alembic)

| Revisão | Cria |
|---|---|
| `20260803_0001` | reserva de histórico (vazio) |
| `20260803_0002` | `user`, `tenant`, `membership`, `audit_log` + funções `mentora_current_user_id()`, `mentora_current_tenant_id()`, bootstrap; **RLS completo**; CHECK de papéis `Owner/Admin/Educator/Student` |
| `20260803_0003` | `knowledge_base`, `document`, `document_version`, `ingestion_job`, `outbox`; bypass de worker no outbox; estados `UPLOADED/QUEUED/PROCESSING/INDEXED/FAILED/QUARANTINED/SUPERSEDED` |
| `20260803_0004` | `chat_thread`, `message`, `citation`, `feedback`, `usage_event`; CHECK banda `high/medium/low`; CHECK rating `-1/1`; RLS |

### 1.4 Fila e ingestão

- Stream Redis `mentora:ingestion`, grupo `workers`, DLQ `mentora:ingestion:dlq`;
  XAUTOCLAIM a partir de 30 s; máx. 3 retries (ADR-017).
- Outbox: `FOR UPDATE SKIP LOCKED` → XADD → `published_at`; eventos
  `ingestion.requested`, `document.delete_requested` (batch 50, poll 1 s).
- Worker: `Docling` (`DocumentConverter`), `StructuralChunker` 512/64 (ADR-012),
  `E5Embedder` 384 dim com prefixos (ADR-018/021), Qdrant coleção `multilingual-e5-small_v1`
  com IDs determinísticos e filtro forçado de tenant (ADR-011).

### 1.5 Tutor

- SSE com eventos `token`, `fallback`, `error`, `citations`, `confidence`, `complete`.
- Bandas provisórias hardcoded: `HIGH` se `max(score) ≥ 0.8`; fallback/`LOW` se `max(score) < 0.5`
  (`tutor_min_retrieval_score` padrão 0.5; `tutor_retrieval_limit` 5) — **não ratificadas** (ADR-009).
- Modelo de geração: `llama-3.3-70b-versatile` (Groq).

---

## 2) §4.2 — Matriz RBAC (recuperada de `apps/api/.../platform/rbac.py`)

Papéis: `Owner`, `Admin`, `Educator`, `Student`.

| Permissão | Owner | Admin | Educator | Student |
|---|:--:|:--:|:--:|:--:|
| `tenant.manage` | ✅ | | | |
| `membership.manage` | ✅ | ✅ | | |
| `knowledge_base.create` | ✅ | ✅ | ✅ | |
| `document.manage` | ✅ | ✅ | ✅ | |
| `document.read` | ✅ | ✅ | ✅ | ✅ |
| `tutor.chat` | ✅ | ✅ | ✅ | ✅ |
| `exercise.generate` | ✅ | ✅ | ✅ | |
| `analytics.read` | ✅ | ✅ | ✅ | |
| `audit_log.read` | ✅ | ✅ | | |

> **Racional original** (negação por padrão, planos de papéis futuros): **IRRECUPERÁVEL**. A matriz
> acima é a implementação; a justificativa por permissão deve ser re-decidida se necessário.

---

## 3) §7.3 — Especificação do dataset dourado v1 (reconstruída do artefato congelado)

**Artefatos:** `evals/datasets/v1/{golden.jsonl, manifest.json, lock.json}`.
**Imutável por hash** (`lock.json` `dataset_sha256 cd7b41d2…f7146f`,
`manifest_sha256 e15ab7f2…5ea66d7`). Alterar exige novo dataset `v2` + novo freeze.

- **120 itens**; composição **72 respondíveis / 30 não respondíveis / 18 ambíguos-parciais**.
- **6 documentos** fonte, exatamente **20 itens por documento** (12 respondíveis + 5 não respondíveis
  + 3 ambíguos por doc). `doc_type` por documento: `narrative`, `table_heavy`, `dense`, `poor_scan`.
  O `poor_scan` tem fixture image-only derivada com `page_map` (18 páginas).
- **Campos de um item:** `id` (prefixo `v1-`), `pergunta`, `resposta_referencia`, `documento`,
  `paginas_esperadas`, `evidence_quotes`, `tipo`, `dificuldade`, `review_status`, `notas`.
- **Invariantes impostas pelos testes** (`evals/tests/test_golden_dataset.py`, `test_manifest.py`):
  todos `review_status == approved`; IDs únicos; `evidence_quotes` ≥ 15 chars; perguntas ≥ 10 chars;
  sem frases cloze/tautologia; dificuldade em `{facil, medio, dificil}` com cada nível ≥ 20%
  (≥ 24 itens); respondíveis exigem citação/páginas/resposta; não respondíveis têm resposta nula e
  `notas`; licenças restritas a `user_attestation` (proibido `cc`, `creative_commons`,
  `public_domain`, `cc0`); hashes SHA-256 dos PDFs verificados contra `support/ebooks`.
- **Especificação formal original** (metodologia de amostragem, protocolo de revisão):
  **IRRECUPERÁVEL** — sobrevive o artefato congelado e seus testes.

---

## 4) §8.1 — Resolução de citação

A citação é resolvida **a partir dos chunks recuperados**, nunca do texto gerado pelo modelo.
`citation` persiste `document_version_id`, `chunk_id` (= point id do Qdrant), `page_number`,
`snippet` e `retrieval_score`. (Requisito derivado do AC-02 do PRD.)

---

## 5) §12 — Gates de aceitação (verdade do CI + DoD do PRD)

O que o CI (`.github/workflows/ci.yml`) executa:

- **backend:** `uv sync --frozen`; compose up postgres; `alembic upgrade head`;
  `ruff check apps/api apps/worker`; `ruff format --check apps/api apps/worker`;
  `mypy --config-file=pyproject.toml`; `pytest --package mentora-api`;
  `lint-imports --package mentora-api`.
- **frontend:** `npm ci`; `npm run web:lint`; `npm run web:build`.
- **contracts:** `npm run contracts:generate` + `git diff --exit-code` em `packages/contracts/`
  ✅ **restaurado em 2026-08-30** — pacote reconstruído e geração determinística; gate pleno só
  com os artefatos versionados.

**Definition of Done do Marco 3.5** (`PRD.md` §13.6): dataset v1 congelado; ADR-018, ADR-012 e
ADR-009 ratificados por números reproduzíveis; relatórios em `evals/reports/`; produção alinhada a
E5-small + estrutural 512/64; e gates `ruff check .`, `ruff format --check .`, `mypy`,
`pytest -q`, `pre-commit run --all-files` aprovados.

> **Definições de gate originais** por marco (critérios de saída detalhados, testes de aceitação):
> **IRRECUPERÁVEL** em detalhe; acima está o que o CI e o PRD evidenciam.

---

## 6) §13.2 — Corte mínimo do V1

O corte mínimo do V1 é definido pelo `PRD.md` §3 (tabela de escopo) e §7 (não-escopo). Marcos 5 e 6
são explicitamente condicionais. Este plano **não** reintroduz itens cortados.

---

## 7) Lacunas conhecidas deste documento reconstruído

| Item | Estado |
|---|---|
| Esforço, custo e cronograma originais | **IRRECUPERÁVEL** — não inventado |
| Definições de gate por marco em detalhe | **IRRECUPERÁVEL** |
| `packages/contracts` e pipeline de geração | **resolvido** (2026-08-30); pendente apenas versionar artefatos |
| Especificação formal do dataset (§7.3 original) | **IRRECUPERÁVEL** (sobrevive o artefato) |
| Racional da matriz RBAC por permissão | **IRRECUPERÁVEL** |

---

## 8) Registro de mudanças

| Versão | Data | Mudança |
|---|---|---|
| reconstruído-v0 | 2026-08-30 | Reconstrução do zero a partir de evidência. Arquitetura, RBAC (§4.2), dataset (§7.3), citação (§8.1) e gates (§12) recuperados; esforço/custo marcados irrecuperáveis. |
| reconstruído-v0.1 | 2026-08-30 | `packages/contracts` reconstruído (job `contracts` do CI operacional); esqueletos `specs/01/02/03/09` adicionados como rascunhos. |
