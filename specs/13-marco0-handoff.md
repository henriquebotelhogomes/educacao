# Spec 13 — Brief de Handoff do Marco 0 (Fundação reproduzível)

> **Documento:** `specs/13-marco0-handoff.md` · **Status:** RECONSTRUÍDO · **Data:** 2026-08-30
> **Nota de proveniência:** o original **foi perdido** (nunca existiu no histórico git). Reconstruído
> do zero a partir do checklist do Marco 0 no `PRD.md` §11 e da fundação que sobrevive no repositório.
> O Marco 0 está **concluído e evidenciado**; este brief serve para reproduzir e auditar a fundação.

---

## 1) Objetivo do Marco 0

Tornar o repositório um workspace reproduzível onde `apps/api`, `apps/web` e `apps/worker` coexistem
sob um único lock determinístico, com infraestrutura local em Compose, contratos de API gerados e CI
verde — antes de armazenar documentos reais de usuário.

## 2) Entregáveis do Marco 0 (checklist espelhado do `PRD.md` §11)

- [x] Mover `app.py` → `legacy/streamlit/` sem alterar código; atualizar README.
- [x] Converter a raiz em **workspace uv** com membros `legacy/streamlit`, `apps/api`, `apps/worker`
      (`pyproject.toml` `[tool.uv.workspace]`).
- [x] `apps/api`: esqueleto FastAPI com config tipada, `/healthz`, `/readyz`, `/api/v1/meta`,
      logs JSON, OpenTelemetry, Alembic, testes mínimos e `import-linter`.
- [x] `apps/web`: Next.js App Router com página placeholder consumindo `/api/v1/meta`.
- [x] `apps/worker`: esqueleto com entrypoint limpo.
- [x] `infra/compose`: Postgres, Redis, Qdrant, MinIO, OTel Collector e stack
      Grafana/Tempo/Loki/Prometheus com healthchecks.
- [x] `packages/contracts`: tipos TS gerados do OpenAPI, sem diff no CI. ⚠️ **Este diretório não
      existe mais no repositório** — o job `contracts` do CI está quebrado (ver `specs/12` §0).
- [x] CI inicial (`.github/workflows/ci.yml`) verde.

## 3) Como reproduzir a fundação

1. `uv sync --frozen` na raiz (instala os três membros do workspace).
2. `docker compose -f infra/compose/... up` para Postgres/Redis/Qdrant/MinIO/OTel/observabilidade.
3. `alembic upgrade head` em `apps/api`.
4. Gates: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`,
   `uv run pytest -q`, `uv run pre-commit run --all-files`, `lint-imports --package mentora-api`.

> As variáveis necessárias estão em `.env.example` (API 8000, Postgres 5433, Qdrant 6333,
> MinIO 9000, OTel 4318). `.env` é gitignorado.

## 4) Critério de saída

O Marco 0 é considerado concluído quando o checklist de aceitação do seu brief (§7 original) está
**evidenciado** — comando executado, teste passando ou artefato no repositório. Evidência atual:
workspace uv funcional, CI verde e Compose com healthchecks. Pendência aberta: regenerar
`packages/contracts` para destravar o job `contracts`.

## 5) Registro de mudanças

| Versão | Data | Mudança |
|---|---|---|
| reconstruído-v0 | 2026-08-30 | Reconstrução do zero a partir do `PRD.md` §11 e da fundação sobrevivente. Detalhe do brief original (§7) marcado irrecuperável. |
