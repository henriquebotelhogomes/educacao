# Spec 01 — Visão de Produto

> **Documento:** `specs/01-product-vision.md` · **Status:** RASCUNHO RECONSTRUÍDO (esqueleto) · **Data:** 2026-08-30
> **Nota de proveniência:** o original **foi perdido** (nunca existiu no histórico git). Este
> esqueleto foi reconstruído **do zero** a partir apenas de evidência sobrevivente — `PRD.md`
> (v1.7), `specs/12-execution-plan.md`, `specs/11-risks-assumptions-adr.md` e o código em `apps/`.
> Seções cujo conteúdo original era narrativa de visão/posicionamento/negócio estão marcadas
> **IRRECUPERÁVEL** e não foram inventadas.
> **Precedência** (`PRD.md` §10): sobre **visão**, este documento prevalece. Sobre escopo,
> prioridade e aceite do release V1, prevalece o `PRD.md`.

---

## 1) Por que o produto existe (fundamentado)

Estudantes têm material de estudo, mas não têm quem responda dúvidas **no contexto do próprio
material**. Ferramentas genéricas de IA respondem — e **inventam**, sem citar fonte. Em contexto
educacional, uma resposta errada com aparência de certeza é pior do que nenhuma resposta.
*(PRD §1)*

**Proposta de valor:** recusar em vez de alucinar. Toda resposta do tutor ou **cita o trecho de
origem** (documento, página e trecho) ou **admite explicitamente não ter encontrado evidência**.
Não existe terceira opção. Todo o resto do V1 existe para sustentar esse comportamento.
*(PRD §1)*

## 2) Produto e codinome (fundamentado)

- **Codinome:** Mentora AI — *Adaptive Learning & AI Tutoring Platform*. *(PRD cabeçalho)*
- **Idioma do V1:** pt-BR apenas (UI, prompts, material). i18n/EN no V2. *(PRD D4)*
- **Plataforma do V1:** web responsiva, mobile-first; sem app nativo. *(PRD D5)*

## 3) Persona-cabeça-de-ponte (fundamentado)

**Ana — estudante autodidata (B2C)** guia o V1: ciclo de feedback mais curto e sem dependência de
venda institucional. Prof. Carlos (educador) é atendido parcialmente pelo gerador de exercícios;
Beatriz (B2B/institucional) fica para o V2. *(PRD D1)* As personas detalhadas vivem em
[`02-functional-spec.md`](./02-functional-spec.md).

## 4) Modelo de negócio no V1 (fundamentado)

**Sem pagamento no V1.** Planos (Free/Pro) existem como **limites técnicos de custo e abuso**,
não como produto comercial; metering e cotas são requisito de custo, não de receita. Stripe
somente com demanda validada. *(PRD D6 e §5)* Limites concretos em `PRD.md` §5.

## 5) Posicionamento e diferenciação

**IRRECUPERÁVEL** — o texto original de posicionamento, mercado e análise competitiva não
sobreviveu. A única evidência de diferenciação é a proposta de valor do §1 (citação obrigatória
ou recusa explícita) e o diferencial de longo prazo: adaptativo/analytics (Épico E), cortado do
V1 por exigir volume de uso inexistente *(PRD §3)*.

## 6) Métricas que expressam a visão (fundamentado)

A visão é mensurada pelas métricas de produto do `PRD.md` §6, destacando-se:

- **North Star:** perguntas respondidas **com fonte** e avaliadas como úteis, por semana.
- **Taxa de citação ≥ 99%** e **taxa de fallback na faixa 10–25%** — fallback fora da faixa
  indica alucinação (baixo demais) ou retrieval ruim (alto demais).
- **Faithfulness ≥ 0,85** no dataset dourado v1 congelado.

## 7) Hipóteses e apostas de negócio

**IRRECUPERÁVEL** — elenco original de hipóteses não sobreviveu. Evidência parcial: os números de
plano são hipóteses de partida a recalibrar com custo real por MAU após o Marco 3 *(PRD §5)*, e
os riscos de produto RP1–RP6 *(PRD §8)* são as apostas de risco conhecidas.

## 8) Lacunas conhecidas deste rascunho

| Item | Estado |
|---|---|
| Posicionamento, mercado e concorrência | **IRRECUPERÁVEL** |
| Hipóteses de negócio originais | **IRRECUPERÁVEL** |
| Jornada/narrativa de marca | **IRRECUPERÁVEL** |

## Registro de mudanças

| Versão | Data | Mudança |
|---|---|---|
| rascunho-v0 | 2026-08-30 | Esqueleto reconstruído do zero a partir de evidência (PRD v1.7, specs 11/12). |
