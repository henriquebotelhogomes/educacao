# Spec 09 — Frontend & UX

> **Documento:** `specs/09-frontend-ux.md` · **Status:** RASCUNHO RECONSTRUÍDO (esqueleto) · **Data:** 2026-08-30
> **Nota de proveniência:** o original **foi perdido** (nunca existiu no histórico git). Este
> esqueleto foi reconstruído **do zero** a partir apenas de evidência sobrevivente — `PRD.md`
> (v1.7), `specs/12-execution-plan.md`, `specs/02-functional-spec.md` (rascunho) e o código em
> `apps/web`. Design system, wireframes e guias de estilo originais são **IRRECUPERÁVEIS** e não
> foram inventados.

---

## 1) Plataforma e princípios (fundamentado)

- **Web responsiva, mobile-first; sem app nativo** (`PRD` D5).
- **pt-BR apenas** no V1 — UI, mensagens de erro, estados vazios e textos de fallback (`PRD` D4).
- Princípio de UX central: **a interface deve tornar a citação ou a recusa igualmente claras** —
  recusar não pode parecer "produto quebrado" (`PRD` RP1).

## 2) Superfícies implementadas (verdade do repositório)

| Rota | Página | Estado |
|---|---|---|
| `/` | Home/meta | Next.js App Router consumindo `/api/v1/meta` |
| `/documents` | Biblioteca de documentos | status de processamento visível (B5) |
| `/tutor` | Tutor (chat) | SSE; bandas; citações; feedback |

Infra de frontend: `src/lib/api.ts` (cliente), `src/lib/telemetry.ts` + `instrumentation.ts`
(observabilidade). Contratos tipados disponíveis em `packages/contracts/schema.d.ts`
(gerados do OpenAPI; importação pelo web ainda não evidenciada).

## 3) Estados obrigatórios derivados dos critérios de aceite

| Estado | Requisito | Fonte |
|---|---|---|
| **Estado vazio do tutor** | Explicar o que fazer e conduzir ao upload; sem respostas baseadas só em conhecimento geral do modelo | AC-03 |
| **Resposta com citação** | Citação clicável exibindo trecho de origem + página; banda `Alta/Média/Baixa`, **nunca percentual** | AC-01, AC-02, `PRD` D3 |
| **Fallback/recusa** | Mensagem de ausência de evidência + ação concreta (carregar material, reformular) | AC-01, RP1 |
| **Falha de ingestão** | Motivo compreensível + ação de reprocessar | AC-04 |
| **Cota atingida** | Exibir limite atingido + **data de renovação** | AC-05 |
| **Streaming** | Exibição token a token (SSE com eventos `token`, `fallback`, `error`, `citations`, `confidence`, `complete`) | C5; `specs/12` §1.5 |

> Os textos de fallback, erro e estado vazio são dependência com dono *a definir* (`PRD` §9,
> necessária no Marco 3). Conteúdo original: **IRRECUPERÁVEL**.

## 4) Eventos SSE consumidos pela UI (fundamentado em `specs/12` §1.5)

`token` (incremento de resposta), `citations` (lista resolvida por chunk id), `confidence`
(banda), `fallback` (recusa), `error`, `complete`.

## 5) Feedback do usuário

Botões 👍/👎 por resposta; persistência com identificador da resposta e do trace (`PRD` AC-07).

## 6) Design system e componentes

**IRRECUPERÁVEL** — não sobrevive evidência de biblioteca de componentes, tokens, paleta ou
tipografia originais. Reposição deve ser decidida por ADR se/when o web evoluir além do
placeholder atual.

## 7) Lacunas conhecidas deste rascunho

| Item | Estado |
|---|---|
| Wireframes, jornadas visuais e protótipos | **IRRECUPERÁVEL** |
| Design system (tokens, componentes) | **IRRECUPERÁVEL** |
| Textos finais de UX (fallback, erro, vazio) | **IRRECUPERÁVEL** (dependência `PRD` §9) |
| Fluxos de auth em UI (signup/signin/OAuth) | não evidenciados no web atual; **a reconstruir** |

## Registro de mudanças

| Versão | Data | Mudança |
|---|---|---|
| rascunho-v0 | 2026-08-30 | Esqueleto reconstruído do zero a partir de evidência (PRD v1.7, specs 12, `apps/web`). |
