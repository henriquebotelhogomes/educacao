# Mentora AI

SaaS educacional em evolução: transforma materiais de estudo em um tutor de IA fundamentado em
fontes. O protótipo Streamlit permanece congelado como referência enquanto o produto migra para
Next.js, FastAPI e serviços locais observáveis.

## Status

| Marco | Status |
|---|---|
| 0.5 — Higiene do repositório | ✅ Concluído |
| 0 — Fundação reproduzível | ✅ Concluído |
| 1 — Identidade e isolamento | ✅ Concluído — OAuth state vinculado ao navegador |
| 2 — Documentos / ingestão | ✅ Concluído — redelivery idempotente |
| 3 — Tutor confiável | ✅ Reconcluído após review — cota mensal atômica |
| 3.5+ — Calibração e gerador | ⬜ Pendente |

As fontes de verdade são o [PRD](./PRD.md), o [plano de execução](./specs/12-execution-plan.md),
o [registro de ADRs](./specs/11-risks-assumptions-adr.md), os [recursos inovadores](./specs/14-classroom-innovations-v2.md)
e a [especificação mestra V2](./specs/15-master-spec-v2.md).

## Onboarding local

**Pré-requisitos:** Docker Desktop, Python 3.12, [uv](https://docs.astral.sh/uv/) e Node.js 24.

Confirme que as ferramentas estão disponíveis:

```powershell
uv --version
node --version
npm --version
docker compose version
```

Crie o arquivo de ambiente apenas na primeira execução:

```powershell
Copy-Item .env.example .env
```

Troque `MENTORA_JWT_SECRET` por um valor aleatório de ao menos 32 bytes antes de compartilhar o
ambiente. Google OAuth permanece desabilitado até preencher as três variáveis
`MENTORA_GOOGLE_OAUTH_*`; o callback local padrão usa o ingress em `localhost:8080`.

Instale dependências determinísticas e suba todo o ambiente:

```powershell
uv sync
npm ci
docker compose -f infra/compose/compose.yaml up -d --build
```

Na primeira subida, o Docker baixa as imagens e constrói API, web e worker; aguarde os
healthchecks terminarem. Consulte o estado antes de abrir as URLs:

```powershell
docker compose -f infra/compose/compose.yaml ps
```

Todos os serviços contínuos devem estar `healthy`; `minio-init` deve aparecer como `Exited (0)`,
pois ele só cria o bucket de desenvolvimento.

O comando final sobe a plataforma local:

| Serviço | URL |
|---|---|
| Produto web via ingress | http://localhost:8080 |
| API / OpenAPI | http://localhost:8000/docs |
| Grafana | http://localhost:3001 (`admin` / `admin_dev_only`) |

### Verificação pós-startup

Execute estes comandos e espere respostas HTTP `200`:

```powershell
curl.exe http://localhost:8000/healthz
curl.exe http://localhost:8000/readyz
curl.exe http://localhost:8000/api/v1/meta
npm run contracts:generate
```

O ingress roteia `/api/*` diretamente ao FastAPI, preservando o caminho de SSE definido no
ADR-016. A página web consulta `GET /api/v1/meta`; o trace correlacionado aparece no datasource
Tempo do Grafana.

## Ingestão de documentos

O endpoint `POST /api/v1/documents` recebe um PDF autenticado e retorna `202 Accepted`. A API
valida magic bytes, tamanho (10 MB no plano Free), cota de documentos, hash SHA-256 e salva o
original no MinIO. A mesma transação grava versão, job e outbox; o worker publica em Redis Streams
e executa:

`scan → Docling → chunking estrutural 512/64 → E5 → Qdrant`

O status pode ser acompanhado em `GET /api/v1/documents/{id}/status`. Estados terminais:
`COMPLETED`, `FAILED` e `QUARANTINED`; o motivo fica disponível em `error_message`. PDFs são
limitados a 50 páginas no plano Free após extração. Reenviar o mesmo conteúdo retorna o documento
existente, sem duplicar job ou vetores. Para reprocessar, use
`POST /api/v1/documents/{id}/reprocess`; a versão anterior só é marcada `SUPERSEDED` após a nova
indexar.

### Comandos cotidianos

```powershell
# Acompanhar inicialização ou falha de um serviço.
docker compose -f infra/compose/compose.yaml logs -f api

# Encerrar mantendo bancos, índices e dashboards locais.
docker compose -f infra/compose/compose.yaml down

# Reinicializar todo o estado local, incluindo Postgres, Qdrant, MinIO e Grafana.
docker compose -f infra/compose/compose.yaml down -v
```

Para encerrar a infraestrutura local:

```powershell
docker compose -f infra/compose/compose.yaml down
```

Use `down -v` apenas quando quiser apagar todos os dados de desenvolvimento.

## Troubleshooting

| Sintoma | Ação |
|---|---|
| Porta `8000`, `8080` ou `3001` já está em uso | Ajuste `MENTORA_API_PORT`, `MENTORA_INGRESS_PORT` ou `MENTORA_GRAFANA_PORT` no `.env` e rode `docker compose -f infra/compose/compose.yaml up -d`. |
| Serviço fica `unhealthy` | Rode `docker compose -f infra/compose/compose.yaml logs <serviço> --tail 100`. Verifique Docker Desktop, memória disponível e aguarde o primeiro download de imagens terminar. |
| Alterou `POSTGRES_*` ou `MINIO_*` depois da primeira subida | Esses valores inicializam volumes apenas uma vez. Em desenvolvimento, execute `docker compose -f infra/compose/compose.yaml down -v` e suba novamente. |
| `uv sync` não consegue limpar `.venv` no Windows | Feche processos Python, Streamlit e terminais que usam o ambiente; execute `uv venv --clear` e depois `uv sync`. |
| A API está saudável, mas a página mostra indisponibilidade | Confirme `docker compose -f infra/compose/compose.yaml ps`, depois veja `logs api` e `logs web`. A web usa `http://api:8000` dentro do Compose. |
| Não há trace no Tempo | Faça uma nova requisição para `http://localhost:8080`, espere alguns segundos e, no Grafana, abra **Explore → Tempo**. Pesquise por `service.name = mentora-web` ou `service.name = mentora-api`. |
| O protótipo Streamlit não conecta ao Qdrant local | Isso é esperado: o protótipo legado permanece separado e usa as variáveis de Qdrant configuradas para ele. Não compartilhe a coleção legado com a plataforma nova. |

## Qualidade

```powershell
uv run ruff check apps/api apps/worker
uv run ruff format --check apps/api apps/worker
uv run mypy --config-file=pyproject.toml
uv run --package mentora-api pytest
uv run --package mentora-api lint-imports
npm run web:lint
npm run web:build
uv run pre-commit run --all-files
```

O GitHub Actions replica os gates de backend, frontend e contrato OpenAPI.

## Protótipo legado

O protótipo original não é o produto atual e não deve receber funcionalidades novas. Execute-o
somente como referência:

```powershell
uv run --package legacy-streamlit streamlit run legacy/streamlit/app.py
```
