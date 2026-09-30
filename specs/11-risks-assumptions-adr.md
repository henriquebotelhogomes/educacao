# Spec 11 — Riscos, Suposições e Registro de ADRs

> **Documento:** `specs/11-risks-assumptions-adr.md` · **Status:** RECONSTRUÍDO · **Data:** 2026-08-30
> **Nota de proveniência:** o original deste arquivo **foi perdido** — ele nunca existiu em nenhum
> commit, branch, stash ou blob do histórico git. Esta versão foi reconstruída **do zero** a partir
> apenas de evidência sobrevivente no repositório (código, relatórios de avaliação, dataset dourado,
> `PRD.md`). Cada item indica se o racional foi recuperado da evidência ou é **IRRECUPERÁVEL**.
> Divergências são resolvidas registrando um ADR novo e marcando o anterior como
> `Superseded by ADR-XXX` (regra do `PRD.md` §10).

---

## 0) Estado do registro

| Faixa de IDs | Estado |
|---|---|
| ADR-001 … ADR-004, ADR-006 … ADR-008, ADR-010, ADR-013, ADR-019, ADR-020 | **IRRECUPERÁVEIS** — nenhum rastro em código, relatórios ou PRD. Recriar do zero ou declarar lacuna. |
| ADR-005, ADR-009, ADR-011, ADR-012, ADR-014 … ADR-018, ADR-021, ADR-022 | **Sobreviventes** — referenciados em código/relatórios; decisão recuperável, racional parcial. |

---

## 1) ADRs sobreviventes

### ADR-005 — Pipeline de ingestão idempotente · `Ratificado` (implementado)

- **Decisão:** orquestrar ingestão como `scan → extract → chunk → embed → index` com gestão de
  estado idempotente (`claim_for_processing`), de modo que reprocessar o mesmo documento não
  duplica vetores nem reativa estados terminais.
- **Evidência:** `apps/worker/src/mentora_worker/ingestion/pipeline.py:1`,
  `ingestion/repository.py:1`; `legacy/streamlit/app.py:30,128`.
- **Racional original:** **IRRECUPERÁVEL** (formato do pipeline, escolha dos estados e motivo da
  idempotência por claim). A implementação sobrevive; o registro de decisão, não.

### ADR-009 — Bandas de confiança e calibração de fallback · `BLOQUEADO`

- **Decisão pretendida:** bandas `high | medium | low`, regra de cobertura de citação e
  precision/recall do fallback. **Nenhuma banda/threshold final foi declarada.**
- **Estado provisório no código (placeholders, NÃO ratificados):**
  `HIGH` quando `max(score) ≥ 0.8`; fallback/`LOW` quando `max(score) < 0.5`
  (`apps/api/src/tutor_ai/ai/tutor.py:90-94,49-57`). Esses valores são **hardcoded** e não vêm de
  configuração.
- **Por que bloqueado:** exige avaliação Ragas representativa e calibração contra os 30 itens não
  respondíveis do dataset v1. Metas: **fallback recall ≥ 0,90** e **faithfulness ≥ 0,85** no dataset
  v1 congelado. Não derivar threshold apenas de score de similaridade.
- **Evidência:** `PRD.md:369-370,411-412,455,493,502,508,514`;
  `evals/reports/rag-triad-v1-sample-4.md:8-9`; `evals/rag_triad_runner.py:51,173,639`.
- **Ação:** ratificar somente após o run completo do Marco 3.5 (ver `PRD.md` §13.6).

### ADR-011 — Coleção Qdrant compartilhada com filtro de tenant forçado + IDs determinísticos · `Ratificado`

- **Decisão:** uma coleção compartilhada (`multilingual-e5-small_v1`, 384 dim, COSINE) com isolamento
  por **filtro forçado** de `tenant_id` + `knowledge_base_id` em toda leitura/escrita/exclusão, e
  point IDs determinísticos `uuid5(document_version_id, chunk_index)` para upsert idempotente.
- **Evidência:** `apps/worker/src/mentora_worker/vectorstore/qdrant_adapter.py:1,60`;
  `apps/worker/tests/test_deterministic_ids.py:1`; `PRD.md:71,351`.
- **Racional original (compartilhada vs por-tenant; por que UUID5):** **IRRECUPERÁVEL**.

### ADR-012 — Estratégia de chunking · `Ratificado`

- **Decisão:** `structural-v1-t512-o64` (512 tokens, overlap 64).
- **Números decisivos** (`evals/reports/adr-012-chunking-v1.md`, `PUBLISHABLE`, corpus SHA-256
  `7371bb50…45a638`, e5-small):

  | Estratégia | Recall@10 | MRR@10 | NDCG@10 | p95 query ms | Chunking ms | Chunks |
  |---|---|---|---|---|---|---|
  | semantic t256/o32 | 0.8000 | 0.6199 | 0.6636 | 68.52 | 2.513e+06 | 5955 |
  | semantic t512/o64 | 0.7556 | 0.5575 | 0.6053 | 82.73 | 2.505e+06 | 3286 |
  | structural t256/o32 | 0.7889 | 0.5804 | 0.6296 | 111.1 | 1.564e+05 | 5480 |
  | **structural t512/o64** | **0.8222** | 0.5339 | 0.6029 | **47.81** | **1.887e+05** | 3329 |

- **Justificativa:** maior Recall@10 válido (0,8222), p95 47,81 ms, chunking em 3,15 min CPU.
  `SemanticChunker` 256/32 tem MRR/NDCG maiores mas 41,88 min de chunking e 5.955 vetores — fica
  como alternativa para corpus narrativo quando o orçamento de ingestão permitir. Variantes
  1024/128 excluídas por exceder o limite de 512 tokens do E5-small.
- **Limite E5-small:** 512 tokens **já incluindo** o prefixo `passage: `; o chunker reserva o
  prefixo. Resultados com truncagem são inválidos.
- **Evidência:** `evals/reports/adr-012-chunking-v1.md`; `apps/worker/.../chunking/structural.py:1`;
  `evals/benchmark/chunking_experiment.py`.

### ADR-014 — Redação de conteúdo em telemetria/tracing · `Ratificado`

- **Decisão:** nunca enviar a Langfuse texto-fonte, contextos, prompts, identidades, respostas ou
  chaves; apenas metadados agregados e métricas.
- **Evidência:** `PRD.md:358,453`; `evals/rag_triad_runner.py:45,449`;
  `evals/reports/rag-triad-v1-sample-4.md:13`.

### ADR-015 — Autenticação via cookie httpOnly · `Ratificado`

- **Decisão:** sessão em cookie `httpOnly`, `Secure`, `SameSite=Lax`, com CSRF double-submit e
  rotação de refresh token.
- **Evidência:** `PRD.md:343`; `apps/api/src/tutor_ai/identity/api.py:32`.

### ADR-016 — Streaming SSE + bandas de confiança · `Ratificado`

- **Decisão:** streaming token a token via SSE com emissão de banda de confiança. Sem streaming a
  latência do tutor fica inaceitável (por isso C5 foi promovido a `MUST` no PRD).
- **Evidência:** `PRD.md:357`; `README.md:82`; `apps/api/src/tutor_ai/chat/api.py` (eventos
  `token`, `fallback`, `error`, `citations`, `confidence`, `complete`).

### ADR-017 — Fila Redis Streams com retry, XAUTOCLAIM e DLQ · `Ratificado`

- **Decisão:** consumer group nativo de Redis Streams + dispatcher outbox.
  Stream `mentora:ingestion`, grupo `workers`, DLQ `mentora:ingestion:dlq`,
  `autoclaim_min_idle_ms=30000`, `stream_max_retries=3`, `stream_block_ms=5000`. Outbox lê a tabela
  `outbox` com `FOR UPDATE SKIP LOCKED`, faz XADD e marca `published_at`.
- **Evidência:** `apps/worker/src/mentora_worker/queue/{streams,outbox,messages}.py`; `PRD.md:350`.
- **Racional original (por que Streams e não BullMQ/Celery/SQS; por que outbox):** **IRRECUPERÁVEL**.

### ADR-018 — Modelo de embedding · `Ratificado`

- **Decisão:** `intfloat/multilingual-e5-small`, 384 dimensões.
- **Números decisivos** (`evals/reports/adr-018-embedding-v1.md`, `PUBLISHABLE`, dataset v1 congelado
  com 120 itens / 1.938 páginas / 3.329 chunks):

  | Modelo | Recall@1 | Recall@5 | Recall@10 | MRR@10 | NDCG@10 | p95 query ms | Encode corpus ms |
  |---|---|---|---|---|---|---|---|
  | bge-m3 | 0.6111 | 0.7889 | 0.8444 | 0.6756 | 0.7159 | 374.1 | 7.147e+06 |
  | e5-base | 0.4778 | 0.6556 | 0.7444 | 0.5605 | 0.6045 | 144 | 1.97e+06 |
  | **e5-small** | 0.4111 | 0.7111 | **0.8222** | 0.5339 | 0.6029 | **121.1** | **6.632e+05** |

- **Justificativa:** BGE-M3 venceu em qualidade, mas E5-small entrega Recall@10 0,8222 com p95
  121,1 ms e encoding em 11,05 min CPU, contra 374,1 ms / 119,11 min do BGE-M3. Prioriza custo e
  latência no V1 sem sacrificar pt-BR. MiniLM-L6-v2 excluído (2.801/3.329 passagens acima do limite
  de 256 tokens). BGE-M3 permanece candidato para futuro deploy em GPU.
- **Evidência:** `evals/reports/adr-018-embedding-v1.md`; `apps/worker/.../embeddings/e5_adapter.py:1`.

### ADR-021 — Convenção de prefixos do E5 · `Ratificado` (implementado)

- **Decisão:** prefixos `passage: ` (documentos) e `query: ` (consultas) aplicados no encoding.
- **Evidência:** `apps/worker/src/mentora_worker/embeddings/e5_adapter.py:1,13`;
  `vectorstore/qdrant_adapter.py:1`; `ingestion/pipeline.py:138`.
- **Racional original (por que este formato de prefixo; alternativas avaliadas):** **IRRECUPERÁVEL**.

### ADR-022 — Varredura de conteúdo (malware/EICAR) · `Provisório`

- **Decisão:** assinatura EICAR em dev/test; **fail-closed** em produção (nenhum motor AV conectado).
  Explicitamente **não é grau de produção** — placeholder.
- **Evidência:** `apps/worker/src/mentora_worker/scanning/content_scan.py:1,25`;
  `ingestion/pipeline.py:95`; `apps/worker/tests/test_eicar.py:1`.
- **Plano original de integração AV em produção:** **IRRECUPERÁVEL**.

---

## 2) ADRs irrecuperáveis

Os IDs abaixo são citados indiretamente pela numeração do registro, mas **não deixaram rastro** em
código, relatórios ou PRD. Ao recriá-los, não invente racional — declare lacuna ou redecida com ADR
novo.

| IDs | Observação |
|---|---|
| ADR-001 … ADR-004 | Tópicos desconhecidos. Provavelmente decisões de fundação (Marco 0). |
| ADR-006 … ADR-008 | Tópicos desconhecidos. |
| ADR-010 | Desconhecido. Entre ADR-009 (confiança) e ADR-011 (Qdrant). |
| ADR-013 | Desconhecido. Entre ADR-012 (chunking) e ADR-014 (telemetria). |
| ADR-019, ADR-020 | Desconhecidos. Entre ADR-018 (embedding) e ADR-021 (prefixos). |

---

## 3) Suposições vigentes (a revalidar)

- **Licenciamento do corpus:** os 6 PDFs do dataset dourado têm `license_basis: user_attestation`
  (atestado em 2026-08-03), **não** licença formal (CC/domínio público são explicitamente proibidos
  pelos testes). Suposição de uso legítimo para avaliação interna.
- **Cota Groq:** o Marco 3.5 assume o free tier de **100.000 tokens/dia**, que já se mostrou
  insuficiente para o run completo (ver `PRD.md` §13.4). Suposição a revalidar antes de qualquer
  execução ratificante.
- **Juiz Ragas:** a amostra provisória usou juiz `llama-3.1-8b-instant` ≠ modelo de geração
  `llama-3.3-70b-versatile`. Trocar o juiz da avaliação ratificante exige ADR novo, não substituição
  silenciosa (`PRD.md` §13.5, estratégia 2).

---

## 4) Registro de mudanças

| Versão | Data | Mudança |
|---|---|---|
| reconstruído-v0 | 2026-08-30 | Reconstrução do zero após perda do original. ADRs sobreviventes recuperados de evidência; ADR-001…004/006…008/010/013/019/020 declarados irrecuperáveis. ADR-009 permanece bloqueado. |
