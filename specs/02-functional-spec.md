# Spec 02 — Especificação Funcional

> **Documento:** `specs/02-functional-spec.md` · **Status:** RASCUNHO RECONSTRUÍDO (esqueleto) · **Data:** 2026-08-30
> **Nota de proveniência:** o original **foi perdido** (nunca existiu no histórico git). Este
> esqueleto foi reconstruído **do zero** a partir apenas de evidência sobrevivente — `PRD.md`
> (v1.7), `specs/12-execution-plan.md` e o código em `apps/`. Trechos originais não recuperados
> estão marcados **IRRECUPERÁVEL** e não foram inventados.
> **Precedência** (`PRD.md` §10): sobre **detalhe funcional**, este documento prevalece; sobre
> escopo/prioridade/aceite do V1, prevalece o `PRD.md`. A decisão **D3** do PRD **supersedou a
> decisão C3 original deste documento** (exibição de confiança).

---

## 1) Personas (fundamentado em `PRD.md` D1; detalhe original IRRECUPERÁVEL)

| Persona | Papel | Situação no V1 |
|---|---|---|
| **Ana** — estudante autodidata | Usuária-cabeça-de-ponte (B2C) | Guia todo o V1 *(PRD D1)* |
| **Prof. Carlos** — educador | Atendido parcialmente | Gerador de exercícios (Épico D) no V1 |
| **Beatriz** — institucional | B2B | Fora do V1; V2 |

> Jornadas detalhadas, dores e critérios de sucesso por persona: **IRRECUPERÁVEL**.

## 2) Épicos (IDs recuperados do mapeamento de escopo do `PRD.md` §3)

| Épico | Tema | Itens conhecidos |
|---|---|---|
| **A** | Identidade, tenants e planos | A1 login e-mail + Google OAuth; A2 tenants/membros/papéis; A3 convites (V2); A4 planos/limites/metering; A5 billing (V2) |
| **B** | Biblioteca de documentos | B1 upload de múltiplos PDFs; B2 processamento assíncrono (Docling); B3 chunking + embeddings + indexação; B4 sem `force_recreate` destrutivo; B5 status visível; B6 listar/remover/reprocessar; B7 deduplicação por hash |
| **C** | Tutor | C1 chat sobre a base do usuário; C2 citação obrigatória; C3 confiança + fallback; C4 histórico persistido; C5 streaming token a token; C6 sugestões (V2); C7 múltiplas threads |
| **D** | Gerador de exercícios | D1–D3 exercícios + gabarito + explicações (múltipla escolha no V1); D4 exportação DOCX; D5 geração fundamentada no material; D6 banco de questões (V2) |
| **E** | Adaptativo e analytics | E1–E4 — cortado do V1 (V2/V3) |
| **F** | Qualidade e feedback | F1 evals automáticos offline; F2 feedback 👍/👎; F3 painel interno (condicional) |

Escopo por item no V1 (✅/⚪/❌) e promoções a `MUST` (B7, C5, D5): tabela authoritative em
`PRD.md` §3.

## 3) Casos de uso

O `PRD.md` §4 referencia **UC-01…UC-04** deste documento como o núcleo já coberto, e adiciona
AC-01…AC-07 para os casos que faltavam (fallback, primeiro uso, cota, falha e isolamento).
Numeração e texto originais dos UCs: **IRRECUPERÁVEL** — a reconstrução abaixo é a leitura mais
conservadora compatível com o PRD e o código:

| UC | Tema (reconstruído) | Evidência |
|---|---|---|
| **UC-01** | Perguntar ao tutor e receber resposta fundamentada (ou recusa explícita) | AC de UC-01 superseded por `PRD` AC-01; implementado em `tutor_ai/ai/tutor.py` + SSE |
| **UC-02** | Carregar e acompanhar documentos na biblioteca | Épicos B; AC-04 (falha visível e recuperável); endpoints `/api/v1/documents*` |
| **UC-03** | Criar conta e operar dentro do próprio tenant | Épicos A; AC-06 (isolamento); RBAC `specs/12` §4.2 |
| **UC-04** | Avaliar respostas com 👍/👎 | Épico F2; AC-07; `POST /api/v1/feedback` |

> Casos de uso do gerador de exercícios (Épico D) possivelmente existiam aqui; **sem evidência**.

## 4) Decisão superseded conhecida

- **C3 original (exibição de confiança):** superseded por `PRD` **D3** — banda
  `Alta / Média / Baixa`, nunca percentual. O texto original de C3 é **IRRECUPERÁVEL**, mas
  continha exibição diferente (percentual), também presente no exemplo original de `03`.

## 5) MoSCoW — `WON'T` recuperados

O `PRD.md` §7 afirma que estes itens **já eram `WON'T` neste documento**: app mobile nativo,
proctoring, marketplace e geração de vídeo/áudio. Classificação `MUST/SHOULD/COULD` original por
item: **IRRECUPERÁVEL** (o PRD registra apenas as promoções posteriores de B7, C5 e D5 de
`SHOULD` para `MUST`).

## 6) Jornadas do usuário

**IRRECUPERÁVEL** — nenhuma jornada sobreviveu. Âncoras conhecidas: primeiro uso com estado vazio
que conduz ao upload (`PRD` AC-03) e demo pública anônima com base pré-indexada (`PRD` §5),
pensadas contra o risco RP4 ("ninguém carrega material").

## 7) Lacunas conhecidas deste rascunho

| Item | Estado |
|---|---|
| Detalhe de personas e jornadas | **IRRECUPERÁVEL** |
| Texto original de UC-01…UC-04 e eventuais UCs adicionais | **IRRECUPERÁVEL** (tabela §3 é reconstrução) |
| Classificação MoSCoW completa | **IRRECUPERÁVEL** |
| Regras de negócio por épico além do PRD §3/§5 | **IRRECUPERÁVEL** |

## Registro de mudanças

| Versão | Data | Mudança |
|---|---|---|
| rascunho-v0 | 2026-08-30 | Esqueleto reconstruído do zero a partir de evidência (PRD v1.7, código). |
