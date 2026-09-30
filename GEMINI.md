# 🧠 Diretrizes Locais de Engenharia & Governança: Mentora AI (Tier 2)

> **Instanciado Automaticamente pelo Harness Antigravity** — Baseado em `rules-ai-engineer.md` e adaptado para a plataforma educacional Mentora AI (FastAPI + Next.js + RAG Avançado + Multi-Agentes).

---

## 1. Stack & Padrões Normativos do Backend de IA (Python)
* **Gerenciador & Ambiente:** Uso obrigatório de **`uv`** com workspace (`pyproject.toml` PEP 621) e lockfile determinístico (`uv.lock`). Proibido `requirements.txt` solto ou comandos globais com `pip`.
* **Framework Web & Lifespan:** **FastAPI** assíncrono. Clientes de LLM, pools de embeddings, conexões de banco e grafos devem ser gerenciados estritamente via **`@asynccontextmanager lifespan`**. Proibido usar eventos legados `@app.on_event`.
* **Structured Outputs & Schema Enforcement:** Validação estrita via **Pydantic v2** (`BaseSettings` com fail-fast). Para extração de dados e structured outputs de LLMs, usar Pydantic v2 com schemas rígidos ou SDKs nativos (`google-genai` com `response_schema`), proibindo extração por regex frágil.
* **Documentação de API:** **Scalar obrigatório** servido em `/docs` ou `/api/docs`. Proibido Swagger UI clássico.
* **Logging Estruturado:** **`structlog`** (formato JSON) injetando obrigatoriamente `trace_id`, `tenant_id`, `session_id`, `model_name` e contadores de tokens em todas as interações.

---

## 2. Arquitetura Multi-Agentes, RAG Avançado & Modelos Especializados
* **Orquestração de Agentes:** Uso de **LangGraph** para o fluxo do tutor e gerador de exercícios. Lógica modelada como `StateGraph` cíclico e previsível:
  * Estado do grafo estritamente tipado via `TypedDict` ou `Pydantic`.
  * Nós assíncronos e idempotentes com tratamento de exceções.
  * Checkpointer de conversação e time-travel com suporte a HITL (*Human-in-the-Loop*).
* **Decision Models & Roteamento Especializado (Jev First):**
  * Para nós de triagem, arestas condicionais de grafos (`conditional_edges`), guardrails pré-execução e verificação de relevância de contexto/grounding (sem geração de texto livre), avaliar e priorizar **Jev (`typesafe/jev-latest` via OpenRouter)** com latência sub-50ms e custo de output $0.00.
* **RAG Avançado de Produção (Hybrid Retrieval + Re-ranking):**
  * **Chunking Estratégico:** Manter o chunking estrutural 512/64 ratificado (ADR-012) preservando metadados de origem (`document_id`, `page_number`, `chunk_id`).
  * **Recuperação Híbrida:** Combinação de busca densa vetorial (embeddings E5-small ratificado no ADR-018) com busca esparsa lexical (BM25 ou Tantivy FTS).
  * **Re-ranking:** Reclassificação do Top-K recuperado via Cross-Encoder / Re-ranker antes da injeção no prompt final, eliminando ruído e garantindo respostas de alta precisão.
  * **Padrão CRAG / Self-RAG:** Avaliar a suficiência do contexto documental recuperado antes de sintetizar a resposta, disparando o fallback educacional de forma precisa quando não houver evidência (meta de fallback recall ≥ 0,90).

---

## 3. FinOps, AI Gateway & Observabilidade (LLMOps)
* **Alocação Inteligente de Modelos (FinOps & Frota OpenCode Go):**
  * **Tier 0 (Decisões & Guardrails):** Jev (`typesafe/jev-latest` via OpenRouter) para roteamento de intenção, arestas condicionais e verificação de relevância/grounding sub-30ms com custo de saída $0.00.
  * **Tier 1 (Tutor em Tempo Real & Multimodal — OpenCode Go):** **DeepSeek V4.1 Flash** (alta velocidade, ~26.000 req/5h, streaming SSE imediato) para o tutor textual; **DeepSeek V4 Flash Vision Exp** (~6.500 req/5h) para extração multimodal de fotos de cadernos e exercícios físicos; e **Qwen 3.8 Flash** como alternativa de alto vocabulário pt-BR.
  * **Tier 2 (Evals, Judge Ragas & Fallbacks):** Modelos `:free` do OpenRouter (desbloqueados pelo saldo permanente > $10, consultando dinamicamente `https://openrouter.ai/collections/free-models`), resolvendo o gargalo de quota da Groq.
  * **Tier 3 (Raciocínio Pedagógico Profundo & Gerador de Provas — OpenCode Go):** **DeepSeek V4 Pro** (~1.050 req/5h) ou **Qwen 3.8 Max** para geração de questões de alta complexidade, gabaritos comentados e distratores pedagógicos (Marco 4).
* **AI Gateway & Semantic Caching:** Centralizar chamadas de LLM através de AI Gateway (**LiteLLM Proxy** / **Portkey**) com *Semantic Caching* habilitado (redução de 30% a 50% de custos e respostas sub-10ms em dúvidas repetidas).
* **APM & Telemetria:**
  * **Datadog Pro (Ativo via GitHub Student):** Instrumentar APM completo da API FastAPI e workers na região `us5.datadoghq.com`.
  * **Sentry:** Rastreamento de erros e exceções em produção.
  * **Langfuse:** APM dedicado para LLM, spans de RAG, métricas de Ragas e gestão centralizada de prompts.

---

## 4. Otimização de Prompts, Guardrails & Evals Contínuos
* **Compilação Algorítmica de Prompts (DSPy):** Otimizar os prompts do tutor e do gerador de exercícios usando `dspy.Signature` e compiladores como `MIPROv2` baseados no dataset dourado v1 congelado.
* **Guardrails Ativos em Runtime:** Interceptação em tempo real (<30ms) com **NeMo Guardrails**, **Guardrails AI** ou **Jev** para bloquear prompt injection, jailbreaks e vazamento de system prompts.
* **Dataset Dourado v1 & Evals (Ragas):** Preservar a imutabilidade do dataset dourado v1 (`evals/datasets/v1/lock.json`). Meta do Marco 3.5: Faithfulness ≥ 0,85 e Fallback Recall ≥ 0,90 ratificando o ADR-009.
* **Red-Teaming Gate (CI/CD):** Executar auditoria automatizada de segurança via **Promptfoo** antes de novos releases.

---

## 5. Padrão Normativo do Frontend (Web)
* **Stack:** Next.js (App Router), React 19, TypeScript estrito.
* **Design System & UI:** **Tailwind CSS** + **Shadcn UI** (Radix Primitives). Proibido HTML cru sem estilização.
* **Componentes Avançados:**
  * Renderização de Markdown rica com KaTeX (fórmulas matemáticas) e Syntax Highlighting de código para materiais acadêmicos.
  * **TanStack Virtual** para virtualização de listas e visualização de grandes bibliotecas de documentos.
  * **React Flow / xyflow** para visualização interativa do grafo de tópicos e mapa de conhecimento do estudante.

---

## 6. Guardrails de Entrega & Qualidade (Anti-Vibe-Coding)
* **Validação Determinística Obrigatória:** Antes de declarar tarefas concluídas, validar no terminal:
  * `uv run ruff check apps/api apps/worker evals`
  * `uv run ruff format --check apps/api apps/worker evals`
  * `uv run mypy --config-file=pyproject.toml`
  * `uv run --package mentora-api pytest`
  * `uv run --package mentora-worker pytest`
  * `npm run web:lint`
* **Commits:** Conventional Commits (`feat:`, `fix:`, `refactor:`, `chore:`, `test:`, `docs:`). Segredos estritamente em `.env` (ignorado no Git).
