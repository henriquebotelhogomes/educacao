# PRD — Mentora AI · Release V1

> **Documento:** Product Requirements Document · **Status:** Draft v1.1 · **Data:** 2026-08
> **Owner:** Produto · **Codinome:** Mentora AI — *Adaptive Learning & AI Tutoring Platform*

---

## 0) O que este documento é — e o que não é

**É** a fonte de verdade para **escopo, prioridade e critérios de aceite do release V1**.

**Não é** visão de produto, especificação funcional detalhada nem plano de arquitetura. Esses
documentos já existem e continuam válidos:

| Preciso de… | Vá para |
|---|---|
| Por que este produto existe, posicionamento, negócio | [`specs/01-product-vision.md`](./specs/01-product-vision.md) |
| Personas detalhadas, épicos, casos de uso, jornadas | [`specs/02-functional-spec.md`](./specs/02-functional-spec.md) |
| Stack, contratos, NFRs, segurança, observabilidade, UX | [`specs/03`](./specs/03-technical-spec.md) – [`09`](./specs/09-frontend-ux.md) |
| Arquitetura física, marcos, esforço, custo, gates | [`specs/12-execution-plan.md`](./specs/12-execution-plan.md) |
| Decisões e trade-offs (ADRs) | [`specs/11-risks-assumptions-adr.md`](./specs/11-risks-assumptions-adr.md) |
| Recursos inovadores (Classroom V2) | [`specs/14-classroom-innovations-v2.md`](./specs/14-classroom-innovations-v2.md) |
| Especificação mestra de produto & engenharia (V2) | [`specs/15-master-spec-v2.md`](./specs/15-master-spec-v2.md) |

> **Histórico:** a versão anterior deste arquivo continha um plano de engenharia, não um PRD. Aquele
> conteúdo foi preservado, corrigido e ampliado em `specs/12-execution-plan.md`.

---

## 1) Problema e resultado esperado

Estudantes têm material de estudo, mas não têm quem responda dúvidas no contexto certo. Ferramentas
genéricas de IA respondem — e **inventam**, sem citar fonte. Em contexto educacional, uma resposta
errada com aparência de certeza é pior do que nenhuma resposta.

**Resultado esperado do V1:** um estudante carrega seu próprio material e obtém respostas que ou
**citam o trecho de origem**, ou **admitem explicitamente não ter encontrado evidência**. Não existe
terceira opção.

Esse comportamento — recusar em vez de alucinar — é a proposta de valor. Todo o resto do V1 existe
para sustentá-lo.

---

## 2) Decisões de produto do V1

As specs deixaram estas questões abertas. Ficam decididas aqui.

| # | Questão | Decisão | Justificativa |
|---|---|---|---|
| D1 | Qual persona guia o V1? | **Ana (estudante autodidata, B2C)** | Ciclo de feedback mais curto e sem dependência de venda institucional. Prof. Carlos é atendido parcialmente pelo gerador; Beatriz (B2B) fica para o V2. |
| D2 | Como B2C convive com multi-tenancy? | **Tenant pessoal automático** no signup, com membership `Owner` | Evita dois caminhos de autorização. Todo usuário tem tenant; B2B apenas adiciona membros. |
| D3 | Como exibir confiança? | **Banda `Alta / Média / Baixa`** — nunca percentual | Percentual sugere precisão estatística que não temos antes de calibração. **Supersede `02` C3 e o exemplo de `03`.** |
| D4 | Idioma do V1 | **pt-BR apenas** (UI, prompts, material) | i18n/EN adiciona custo sem validar a hipótese central. Consequência técnica: modelo de embedding multilíngue (ADR-018). |
| D5 | Plataforma do V1 | **Web responsiva** (mobile-first), sem app nativo | Já previsto como `WON'T` em `02`; reafirmado. |
| D6 | Cobrança no V1 | **Sem pagamento**; planos existem como **limites técnicos** | Metering e cotas são requisito de custo, não de receita. Stripe só quando houver demanda validada. |

---

## 3) Escopo do release V1

Mapeamento dos épicos de [`specs/02`](./specs/02-functional-spec.md) para este release.

| Épico / item | V1 | Observação |
|---|:--:|---|
| **A1** Login e-mail + Google OAuth | ✅ | SSO/SAML fora |
| **A2** Tenants, membros, papéis | ✅ | Via tenant pessoal (D2); matriz de permissões em `specs/12` §4.2 |
| **A3** Convites e gestão de membros | ⚪ | V2 — só faz sentido com B2B |
| **A4** Planos, limites e metering | ✅ | Como controle de custo (D6); ver §5 |
| **A5** Billing | ❌ | V2 |
| **B1** Upload de múltiplos PDFs | ✅ | Apenas PDF; DOCX/PPTX/URL no V2 |
| **B2** Processamento assíncrono com Docling | ✅ | |
| **B3** Chunking + embeddings + indexação | ✅ | Coleção compartilhada com filtro forçado (ADR-011) |
| **B4** Sem `force_recreate` destrutivo | ✅ | Requisito bloqueante |
| **B5** Status de processamento visível | ✅ | Inclui erro acionável — ver AC-04 |
| **B6** Listar / remover / reprocessar | ✅ | Exclusão é soft delete no V1 |
| **B7** Deduplicação por hash | ✅ | Promovido de `SHOULD` para `MUST`: é o que impede duplicar vetores |
| **C1** Chat sobre a base do usuário | ✅ | |
| **C2** Citação obrigatória de fonte | ✅ | Requisito bloqueante |
| **C3** Confiança + fallback | ✅ | Como **banda** (D3) |
| **C4** Histórico persistido | ✅ | |
| **C5** Streaming token a token | ✅ | Promovido a `MUST`: sem streaming a latência do tutor fica inaceitável |
| **C6** Sugestões de acompanhamento | ❌ | V2 |
| **C7** Múltiplas threads | ✅ | |
| **D1–D3** Exercícios + gabarito + explicações | ✅ | Múltipla escolha apenas; V/F e dissertativo no V2 |
| **D4** Exportação | ✅ | **DOCX apenas**; PDF no V2 |
| **D5** Geração fundamentada no material | ✅ | Promovido a `MUST`: gerar sem grounding contradiz a proposta de valor |
| **D6** Banco de questões | ❌ | V2 |
| **E1–E4** Adaptativo e analytics | ❌ | V2/V3 — depende de volume de uso que ainda não existe |
| **F1** Evals automáticos | ✅ | Offline/nightly, não em produção síncrona |
| **F2** Feedback 👍/👎 | ✅ | |
| **F3** Painel interno de qualidade | ⚪ | Condicional (Marco 5) |

**Legenda:** ✅ no V1 · ⚪ condicional · ❌ fora do V1

### Promoções e cortes relevantes

- **Promovidos a `MUST`:** B7 (dedup), C5 (streaming), D5 (geração fundamentada). Os três eram
  `SHOULD` nas specs, mas sem eles o produto não cumpre a promessa central ou duplica dados.
- **Cortado do V1:** todo o Épico E (adaptativo/analytics). É o diferencial de longo prazo, mas
  mastery model sem base de uso é modelagem sobre dados inexistentes.

---

## 4) Critérios de aceite

Complementam os UC-01…UC-04 de [`specs/02`](./specs/02-functional-spec.md) cobrindo os casos que
faltavam: fallback, primeiro uso, cota, falha e isolamento.

### AC-01 — Resposta fundamentada ou recusa explícita · *supersede o AC de UC-01*

```gherkin
Dado que existe uma base com documentos indexados
Quando o aluno faz uma pergunta coberta pelo material
Então a resposta deve conter ao menos uma citação com documento, página e trecho
E deve exibir uma banda de confiança "Alta", "Média" ou "Baixa"
E não deve exibir percentual numérico de confiança

Quando o aluno faz uma pergunta não coberta pelo material
Então o sistema deve responder que não encontrou evidência no material
E não deve apresentar conteúdo gerado como se fosse do documento
E deve oferecer a ação de carregar mais material
```

### AC-02 — Citação verificável

```gherkin
Dado que uma resposta exibe citações
Quando o aluno clica em uma citação
Então deve ver o trecho de origem e a página correspondente
E o documento e a página referenciados devem existir de fato na base
```

> Requisito derivado: a citação é resolvida a partir dos chunks recuperados, nunca do texto gerado
> pelo modelo (ver `specs/12` §8.1).

### AC-03 — Primeiro uso (estado vazio)

```gherkin
Dado que um usuário acabou de criar a conta e não tem documentos
Quando abre o tutor
Então deve ver um estado vazio que explica o que fazer e conduz ao upload
E não deve receber respostas do tutor baseadas apenas em conhecimento geral do modelo
```

> Hoje o protótipo apenas exibe um aviso e responde de qualquer forma — comportamento incompatível
> com a proposta de valor.

### AC-04 — Falha de ingestão é visível e recuperável

```gherkin
Dado que o processamento de um documento falhou
Quando o usuário abre a biblioteca
Então deve ver o estado de falha com motivo compreensível
E deve poder reprocessar o documento
E o reprocessamento não deve duplicar conteúdo já indexado
```

### AC-05 — Cota de plano

```gherkin
Dado que o usuário atingiu o limite de perguntas do plano
Quando envia uma nova pergunta
Então deve ver o limite atingido e a data de renovação
E o sistema não deve chamar o provedor de LLM
```

> O bloqueio **antes** da chamada ao provedor é requisito de custo, não de UX.

### AC-06 — Isolamento perceptível ao usuário

```gherkin
Dado dois usuários em tenants diferentes
Quando um deles pesquisa, lista documentos ou consulta o tutor
Então nenhum resultado, citação ou sugestão pode referenciar material do outro
```

### AC-07 — Feedback

```gherkin
Dado que o aluno recebeu uma resposta
Quando classifica com 👍 ou 👎
Então o feedback é persistido com o identificador da resposta e do trace
E respostas com 👎 ficam recuperáveis para análise de qualidade
```

---

## 5) Limites de plano

Planos no V1 são **controle de custo e abuso** (D6), não produto comercial.

| Recurso | Free | Pro | Teams *(V2)* |
|---|---|---|---|
| Bases de conhecimento | 1 | 5 | por tenant |
| Documentos ativos | 3 | 100 | por assento |
| Páginas por documento | 50 | 300 | 300 |
| Tamanho por arquivo | 10 MB | 50 MB | 50 MB |
| Perguntas ao tutor / mês | 30 | 1.000 | agregado no tenant |
| Gerações de exercícios / mês | 3 | 50 | agregado no tenant |
| Histórico de conversas | 30 dias | ilimitado | ilimitado |
| Exportação DOCX | ✅ | ✅ | ✅ |
| Membros | 1 (tenant pessoal) | 1 | vários, com papéis |

### Demo pública anônima

| Recurso | Limite |
|---|---|
| Base | pré-indexada, somente leitura |
| Upload | não permitido |
| Perguntas | 5 por sessão/IP |
| Histórico | não persistido |
| Kill switch | feature flag + teto de gasto diário no provedor |

### Racional dos números

O custo variável tem duas naturezas distintas, e cada limite ataca uma delas:

- **Perguntas → tokens de LLM.** 30 perguntas/mês × ~4k tokens de contexto ≈ 120k tokens/mês por
  usuário free, o que cabe no free tier do provedor com folga para centenas de usuários.
- **Páginas → tempo de CPU do worker.** Embeddings rodam localmente, então ingestão custa *tempo de
  processamento*, não chamada de API. Por isso o limite é por página e por arquivo, não por token.

Os números são **hipóteses de partida** e devem ser recalibrados com custo real por MAU medido a
partir do Marco 3.

---

## 6) Métricas de produto

| Métrica | Definição | Origem | Alvo V1 |
|---|---|---|---|
| **North Star** | Perguntas respondidas **com fonte** e avaliadas como úteis, por semana | `usage_event` + `feedback` | Tendência crescente |
| Ativação | % de usuários com ≥1 documento indexado e ≥3 perguntas em 24 h | `usage_event` | ≥ 40% |
| Taxa de citação | % de respostas factuais com ≥1 citação válida | `message` + `citation` | ≥ 99% |
| **Taxa de fallback** | % de respostas que recusam por falta de evidência | `message.fallback_reason` | **Faixa 10–25%** |
| Utilidade percebida | % de 👍 sobre respostas avaliadas | `feedback` | ≥ 75% |
| Faithfulness | Ragas no dataset dourado v1 congelado | `evals/reports` | ≥ 0,85 |
| Custo por MAU | Custo de LLM + infra ÷ usuários ativos | metering + Langfuse | Dentro do teto definido |

> **Por que a taxa de fallback é uma faixa, e não um mínimo:** fallback **muito baixo** indica que o
> sistema está respondendo sem evidência (alucinando); fallback **muito alto** indica retrieval ruim.
> Otimizar essa métrica em uma única direção é enganoso — ela precisa ser calibrada, e é isso que o
> Marco 3.5 faz.

---

## 7) Não-escopo do V1

| Item | Por que fora | Quando |
|---|---|---|
| Billing / pagamento | Sem receita validada; metering já resolve custo | V2 |
| SSO SAML/OIDC, MFA | Exigência de B2B, que não é a persona-cabeça-de-ponte | V2 |
| Mastery model, analytics de turma | Requer volume de uso inexistente | V2/V3 |
| Ingestão DOCX, PPTX, URL, vídeo | PDF cobre o caso de uso da Ana | V2 |
| Banco de questões reutilizável | Depende de validação do gerador | V2 |
| Exportação PDF | DOCX cobre o fluxo do educador | V2 |
| i18n (EN) | pt-BR valida a hipótese central | V2 |
| App mobile nativo, proctoring, marketplace, geração de vídeo/áudio | Já `WON'T` em `02` | — |
| White-label | Depende de B2B | V3 |

---

## 8) Riscos de produto

Riscos técnicos estão em [`specs/11`](./specs/11-risks-assumptions-adr.md). Estes são de produto.

| ID | Risco | Impacto | Mitigação |
|---|---|---|---|
| RP1 | **Fallback frequente frustra o usuário** — recusar é correto, mas parece "produto quebrado" | Alto | UX de fallback que sugere ação concreta (carregar material, reformular); calibrar faixa no Marco 3.5 |
| RP2 | **Escopo excede a capacidade de entrega** (é o R7 técnico visto do produto) | Alto | Corte mínimo definido em `specs/12` §13.2; Marcos 5 e 6 explicitamente condicionais |
| RP3 | **Qualidade em pt-BR abaixo do esperado** por embedding inadequado | Alto | ADR-018 decide o modelo por benchmark antes do release |
| RP4 | **Ninguém carrega material** — atrito do upload mata a ativação | Alto | Demo com base pré-indexada; onboarding com material de exemplo |
| RP5 | **Educador espera analytics** que estão fora do V1 | Médio | Comunicar escopo; Prof. Carlos é atendido pelo gerador no V1 |
| RP6 | **Custo por usuário acima do previsto** | Médio | Cotas desde o Marco 2; custo por tenant instrumentado no Marco 3 |

---

## 9) Dependências com dono nomeado

Itens que costumam não acontecer por falta de responsável explícito.

| Dependência | Necessária em | Dono |
|---|---|---|
| **Dataset dourado v1** (≥ 60 perguntas, 25% não respondíveis, ≥ 6 PDFs pt-BR licenciados) | Marco 3 | *a definir* |
| Material de exemplo para onboarding e demo | Marco 5 | *a definir* |
| Textos de fallback, erro e estado vazio | Marco 3 | *a definir* |
| Definição do teto de custo mensal | Marco 0 | *a definir* |

> A especificação completa do dataset dourado está em [`specs/12`](./specs/12-execution-plan.md) §7.3.
> É a dependência de maior esforço oculto do projeto: sem ela, nenhuma meta de qualidade do V1 é
> mensurável.

---

## 10) Governança

**Precedência:** em conflito sobre **escopo, prioridade ou critério de aceite do release**, este
documento prevalece. Sobre visão, prevalece `01`. Sobre detalhe funcional, `02`. Sobre arquitetura e
execução, `12`. Sobre decisões técnicas, os ADRs em `11`.

**Regra:** divergência entre documentos **não** é resolvida escrevendo texto novo. É resolvida
registrando um ADR em `11` e marcando o item anterior como `Superseded by ADR-XXX`. Divergência
silenciosa é tratada como defeito de documentação.

As decisões D1–D6 desta versão já estão refletidas na tabela de supersessão de
[`specs/12`](./specs/12-execution-plan.md) §0.1.

---

## 11) Checklist de execução do release (controle de status)

> Controle operacional do V1. Um item só é marcado `[x]` quando seu critério de saída
> (definição em [`specs/12`](./specs/12-execution-plan.md) §12) estiver **evidenciado** —
> comando executado, teste passando ou artefato no repositório. Detalhe técnico de cada marco
> em `specs/12` §12; brief de execução do Marco 0 em
> [`specs/13-marco0-handoff.md`](./specs/13-marco0-handoff.md).

### Marco 0.5 — Higiene do repositório ✅

- [x] `pyproject.toml` + `uv.lock` (lock determinístico) + `.python-version` + `.gitignore`
- [x] `ruff` + `mypy` + `pre-commit` configurados e passando
- [x] `.env.example` corrigido (`QDRANT_URL` era chave, agora é URL)
- [x] Protótipo: coleção isolada `legacy_educacao_rag` + aviso na UI
- [x] Protótipo: retriever reconecta no startup (não responde mais sem grounding)
- [x] Protótipo: `.docx` sanitizado e gerado em memória; variável `exec` renomeada

### Marco 0 — Fundação reproduzível ✅

- [x] Mover `app.py` → `legacy/streamlit/` (sem alterar código) + atualizar README
- [x] Raiz convertida em workspace uv (`legacy/streamlit`, `apps/api`, `apps/worker`)
- [x] `apps/api`: esqueleto FastAPI com config tipada, `/healthz`, `/readyz`, `/api/v1/meta`,
      logs JSON, OpenTelemetry, Alembic, testes mínimos e `import-linter`
- [x] `apps/web`: Next.js App Router com página placeholder consumindo `/api/v1/meta`
- [x] `apps/worker`: esqueleto com entrypoint limpo
- [x] `infra/compose`: Postgres, Redis, Qdrant, MinIO, OTel Collector e stack
      Grafana/Tempo/Loki/Prometheus com healthchecks
- [x] `packages/contracts`: tipos TS gerados do OpenAPI, sem diff no CI
- [x] CI inicial (`.github/workflows/ci.yml`) verde
- [x] Checklist de aceitação do brief §7 cumprido e evidenciado

### Marco 1 — Identidade e isolamento ✅

- [x] Modelos `tenant`, `user`, `membership` + tenant pessoal automático no signup
- [x] Auth por cookie `httpOnly` (ADR-015) + Google OAuth + e-mail/senha
- [x] RBAC pela matriz de `specs/12` §4.2 + RLS no Postgres + audit básico
- [x] Testes negativos cross-tenant passando **antes** de armazenar documentos reais

### Marco 2 — Documentos (walking skeleton) ✅

- [x] Upload seguro (MIME, tamanho, cota) + S3/MinIO + hash SHA-256 + outbox
- [x] Fila Redis Streams (`platform/queue`, ADR-017) com retry, XAUTOCLAIM e DLQ
- [x] Worker de ingestão (Docling, chunking, embeddings, Qdrant ADR-011) idempotente
- [x] UI de biblioteca com status e retry; reenviar o mesmo PDF não duplica vetores

### Marco 3 — Tutor confiável ✅

- [x] Threads persistidas + retrieval tenant-safe + citações resolvidas por chunk ID
- [x] Banda de confiança + fallback (AC-01) + streaming SSE (ADR-016, AC-05)
- [x] Feedback 👍/👎 persistido (AC-07); tracing sem conteúdo bruto segue ADR-014
- [x] Remediação do review P1: OAuth state vinculado ao navegador, cota mensal reservada
      atomicamente e redelivery de ingestão sem reativar estados terminais
- [x] Dataset dourado v1 congelado e hash-locked conforme `specs/12` §7.3 — Marco 3.5

### Marco 3.5 — Calibração baseada em evidência

- [x] Benchmark de embedding (ADR-018) ratificado: E5-small/384 para V1; reindexação não
      destrutiva da versão provisória quando houver corpus ativo
- [x] Benchmark de chunking (ADR-012) ratificado: estrutural 512/64 para V1; SemanticChunker
      256/32 documentado como alternativa de maior custo
- [~] RAG Triad publicada como amostra de 4 casos, explicitamente provisória; não ratifica ADR-009
- [ ] Bandas de confiança/fallback (ADR-009) calibradas no dataset completo; relatório em
      `evals/reports/`

### Marco 4 — Gerador profissional

- [ ] Exercícios estruturados com grounding (D5), gabarito validado e citações
- [ ] Exportação DOCX como job separado; UI e histórico de gerações

---

## 12) Registro de mudanças

| Versão | Data | Mudança |
|--------|------|---------|
| — | 2026-06 | Arquivo continha plano de engenharia; conteúdo movido para `specs/12-execution-plan.md` |
| v1.0 | 2026-08 | PRD real: escopo do V1, decisões D1–D6, critérios de aceite AC-01…AC-07, limites de plano, métricas, não-escopo, riscos de produto e governança |
| v1.1 | 2026-08 | Adicionado §11 Checklist de execução do release (controle de status dos marcos do V1) |
| v1.2 | 2026-08 | Marco 0 evidenciado e concluído: workspace, apps, Compose, contratos e CI |
| v1.3 | 2026-08 | Marco 1 evidenciado e concluído: identidade, sessão em cookies, RBAC, RLS, audit e testes cross-tenant |
| v1.4 | 2026-08 | Marco 2 evidenciado e concluído: documentos, outbox, Redis Streams, worker, Docling, Qdrant e testes de idempotência |
| v1.5 | 2026-08 | Marco 3 concluído: tutor RAG, SSE, citações verificáveis, fallback, confiança e feedback |
| v1.6 | 2026-08 | Marco 3 reaberto após code review e reconcluído com correções P1 de OAuth state, cota mensal do tutor e redelivery idempotente |
| v1.7 | 2026-08-07 | Handoff completo do Marco 3.5: dataset congelado, ADR-018/012 ratificados e RAG Triad provisória publicada; ADR-009 permanece bloqueado por cota de judge |

---

## 13) Handoff técnico — estado atual e continuação obrigatória

> **Objetivo desta seção:** permitir que outra LLM ou engenheiro continue o projeto sem o histórico
> desta conversa. O estado abaixo é válido em **2026-08-07**. Antes de qualquer alteração, leia esta
> seção, `specs/11-risks-assumptions-adr.md`, `specs/12-execution-plan.md` §§7 e 12, e os relatórios
> referenciados em `evals/reports/`.

### 13.1 Estado do Marco 3.5

| Entregável | Estado | Evidência / decisão |
|---|---|---|
| Dataset dourado v1 | **Concluído e congelado** | 120/120 itens aprovados; 72 respondíveis, 30 não respondíveis e 18 ambíguos/parciais; 92 citações auditadas. `evals/datasets/v1/{golden.jsonl,manifest.json,lock.json}` |
| ADR-018 — embedding | **Ratificado** | `intfloat/multilingual-e5-small`, 384 dimensões. Ver `evals/reports/adr-018-embedding-v1.md`. |
| ADR-012 — chunking | **Ratificado** | `structural-v1-t512-o64`; `SemanticChunker` 256/32 permanece alternativa para corpus narrativo. Ver `evals/reports/adr-012-chunking-v1.md`. |
| RAG Triad / Ragas | **Provisório, não ratificante** | Amostra estratificada de 4 respostas cacheadas, judge 8B, publicada no Langfuse. Ver `evals/reports/rag-triad-v1-sample-4.{json,md}`. |
| ADR-009 — confiança/fallback | **Bloqueado** | Requer avaliação Ragas representativa e calibração contra os 30 itens não respondíveis; nenhuma banda/threshold final foi declarada. |
| Status documental final | **Pendente** | README, `specs/12` e o cabeçalho do Marco 3.5 só podem ser marcados concluídos depois de ADR-009. |

### 13.2 Decisões ratificadas que não devem ser reabertas

| Decisão | Valor final | Motivo |
|---|---|---|
| Embedding do V1 | `intfloat/multilingual-e5-small`, 384 dimensões | BGE-M3 venceu qualidade, mas E5-small entrega Recall@10 0,8222, p95 121,1 ms e encoding em 11,05 min CPU; BGE-M3 exigiu 119,11 min e p95 374,1 ms. |
| Chunking do V1 | `structural-v1-t512-o64` | Melhor Recall@10 válido (0,8222), p95 47,81 ms e chunking em 3,15 min CPU. |
| Alternativa de chunking | `semantic-percentile-v1-t256-o32` | MRR/NDCG maiores, mas 41,88 min de chunking e 5.955 vetores; não é o baseline de custo do V1. |
| Limite E5-small | 512 tokens já incluindo `passage: ` | O chunker reserva o prefixo; resultados com truncagem são inválidos. |
| Dados de avaliação | Dataset v1 imutável por hash | Não alterar `golden.jsonl`, `manifest.json` ou `lock.json` para retestar. Uma mudança exige novo dataset `v2` e novo freeze. |

### 13.3 Evidência reproduzível disponível

| Artefato | Conteúdo |
|---|---|
| `evals/reports/adr-018-embedding-v1.md` | Matriz congelada de E5-small, E5-base e BGE-M3; resultados válidos e escolha E5-small. |
| `evals/reports/adr-012-chunking-v1.md` | Matriz válida estrutural vs. SemanticChunker e escolha estrutural 512/64. |
| `evals/reports/rag-triad-v1-sample-4.md` | Amostra **PROVISIONAL** de quatro casos: faithfulness 0,8583; answer relevancy 0,9074; context precision 0,6708; context recall 0,8667. |
| `evals/datasets/v1/lock.json` | Hashes do dataset, manifest e seis PDFs lógicos. |
| `evals/.cache/rag-triad/responses-v1.jsonl` | Cache local ignorado de 52 respostas 70B. Contém conteúdo de respostas; nunca versionar, registrar no Langfuse ou publicar. |

### 13.4 Por que o Marco 3.5 está parado

A Groq gratuita da organização possui limite de **100.000 tokens/dia**. A avaliação completa exige:

1. gerar respostas do tutor para 90 itens respondíveis/parciais;
2. executar múltiplas chamadas de judge Ragas por item para faithfulness, answer relevancy,
   context precision e context recall.

Foram geradas e checkpointadas **52 de 90** respostas do tutor com
`llama-3.3-70b-versatile`. A execução completa atingiu `429` por TPD. Uma amostra de 24 casos
também excedeu a cota porque Ragas abriu 96 avaliações. O runner foi corrigido para batching serial
e checkpoint atômico; mesmo quatro casos com judge 70B ultrapassaram a cota diária restante.

A amostra atual usa:

- respostas cacheadas do tutor `llama-3.3-70b-versatile`;
- judge Ragas `llama-3.1-8b-instant`;
- quatro casos, um por documento disponível no checkpoint;
- `ragas_batch_size=1`;
- Langfuse autenticado, com apenas metadados e métricas agregadas (ADR-014).

Ela é útil como smoke operacional, mas **não** é representativa nem pode ratificar ADR-009.

### 13.5 Retomada obrigatória

**Preflight operacional:** antes de qualquer execução, configurar no `.env` `GROQ_API_KEY`,
`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` e `LANGFUSE_BASE_URL`. Confirmar o pareamento
Langfuse sem expor chaves:

```powershell
uv run python -c "from dotenv import load_dotenv; from langfuse import Langfuse; load_dotenv('.env', override=True); client = Langfuse(); print(client.auth_check()); client.shutdown()"
```

O `auth_check()` deve retornar `True`. Se a Groq ainda usar a cota gratuita de 100.000 TPD, a
estratégia 1 abaixo provavelmente continuará bloqueada; não iniciar novamente o run completo sem
uma decisão explícita sobre capacidade de judge.

Escolha uma estratégia antes de alterar código:

1. **Recomendado para ratificação:** aumentar a cota Groq/Developer Plan e executar a avaliação
   completa. O checkpoint reutiliza as 52 respostas existentes e gera apenas as 38 restantes:

   ```powershell
   $env:PYTHONPATH='apps\worker\src'
   $env:USE_TF='0'
   uv run python -m evals.rag_triad_runner `
     --publish `
     --checkpoint evals\.cache\rag-triad\responses-v1.jsonl `
     --judge-model llama-3.3-70b-versatile `
     --ragas-batch-size 1 `
     --max-rate-limit-wait-seconds 3600 `
     --output evals\reports\rag-triad-v1.json `
     --markdown-output evals\reports\rag-triad-v1.md
   ```

2. **Sem custo por token:** propor em ADR novo um judge local (por exemplo, Ollama/Qwen
   quantizado), declarando hardware, versão e limitação metodológica. Não trocar silenciosamente
   o judge da avaliação ratificante.

3. **Se nenhuma opção for aprovada:** manter RAG Triad e ADR-009 bloqueados. Não usar a amostra
   provisória para alegar que a meta de faithfulness foi atingida.

4. **Estratégia Aprovada (2026-09) — Frota OpenCode Go & OpenRouter :free:**
   Executar a avaliação e o julgamento Ragas utilizando a frota **OpenCode Go** (`DeepSeek V4.1 Flash` para geração do tutor e `DeepSeek V4 Pro` para tarefas complexas) e modelos `:free` do **OpenRouter** (`meta-llama/llama-3.3-70b-instruct:free` ou `qwen/qwen-2.5-coder-32b-instruct:free`) desbloqueados pelo saldo mantido > $10. A tomada de decisão de fallback é calibrada com o decision model **Jev (`typesafe/jev-latest`)** em <30ms com custo de saída $0.00.
   - Especificação dos recursos inovadores da plataforma: [`specs/14-classroom-innovations-v2.md`](./specs/14-classroom-innovations-v2.md).
   - Especificação mestra de produto e engenharia V2: [`specs/15-master-spec-v2.md`](./specs/15-master-spec-v2.md).

### 13.6 Trabalho restante e entrega final do Marco 3.5

Após uma avaliação Ragas completa e publicável:

1. Confirmar `evals/reports/rag-triad-v1.{json,md}` com 90 casos, `PUBLISHABLE`, judge declarado
   e entrega Langfuse bem-sucedida.
2. Implementar/calibrar ADR-009 contra os 30 não respondíveis e os casos respondíveis:
   bandas `high | medium | low`, regra de cobertura de citação e precision/recall do fallback.
   A meta de fallback recall é **≥ 0,90**; a meta de faithfulness é **≥ 0,85** no dataset v1
   congelado. Não derivar threshold apenas de score de similaridade.
3. Escrever relatório de calibração em `evals/reports/` com thresholds, matriz de confusão,
   métricas de fallback, hashes de entrada e limitações.
4. Ratificar ADR-009 em `specs/11-risks-assumptions-adr.md`.
5. Atualizar `README.md`, `specs/12-execution-plan.md`, este PRD e o status do Marco 3.5 somente
   após evidência completa.
6. Executar gates completos: `uv run ruff check .`, `uv run ruff format --check .`,
   `uv run mypy`, `uv run pytest -q` e `uv run pre-commit run --all-files`.

**Definition of Done do Marco 3.5:** dataset v1 congelado; ADR-018, ADR-012 e ADR-009 ratificados
por números reproduzíveis; relatórios versionados em `evals/reports/`; configuração de produção
alinhada a E5-small + estrutural 512/64; e todos os gates acima aprovados.
