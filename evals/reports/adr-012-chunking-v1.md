# ADR-012 Chunking Benchmark Comparison

| Strategy | Version | Model | Validity | Status | Recall@10 | MRR@10 | NDCG@10 | p95 query ms | Chunking ms | Corpus encode ms | Chunks |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| semantic | semantic-percentile-v1-t256-o32 | e5-small | VALID | PUBLISHABLE | 0.8 | 0.6199 | 0.6636 | 68.52 | 2.513e+06 | 5.39e+05 | 5955 |
| semantic | semantic-percentile-v1-t512-o64 | e5-small | VALID | PUBLISHABLE | 0.7556 | 0.5575 | 0.6053 | 82.73 | 2.505e+06 | 7.326e+05 | 3286 |
| structural | structural-v1-t256-o32 | e5-small | VALID | PUBLISHABLE | 0.7889 | 0.5804 | 0.6296 | 111.1 | 1.564e+05 | 5.425e+05 | 5480 |
| structural | structural-v1-t512-o64 | e5-small | VALID | PUBLISHABLE | 0.8222 | 0.5339 | 0.6029 | 47.81 | 1.887e+05 | 6.403e+05 | 3329 |

## Decisão ratificada

**`structural-v1-t512-o64`** é o baseline do V1. Ele obteve o maior Recall@10 (0,8222) entre as
configurações válidas, p95 de consulta de 47,81 ms e chunking em 3,15 min CPU. A alternativa
`semantic-percentile-v1-t256-o32` obteve MRR@10/NDCG@10 superiores (0,6199/0,6636 contra
0,5339/0,6029), mas exigiu 41,88 min de chunking e 5.955 vetores, versus 3.329 para o baseline.

O V1 prioriza ingestão assíncrona rápida e custo previsível. SemanticChunker 256/32 permanece
configuração candidata para corpus narrativo quando houver orçamento de ingestão compatível.
As variantes 1024/128 foram excluídas: excedem o limite de 512 tokens do E5-small e foram
marcadas como não publicáveis pelo gate de truncagem.

Todos os resultados deste relatório são publicáveis e usam o dataset v1 congelado, corpus SHA-256
`7371bb506f81be465c9f8852dfd34d73a0d1d22f38913b036b1d864e4545a638` e E5-small ratificado.
