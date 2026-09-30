# ADR-018 Embedding Benchmark Comparison

| Model | Input validity | Status | Recall@1 | Recall@3 | Recall@5 | Recall@10 | Precision@10 | MRR@10 | NDCG@10 | p50 query ms | p95 query ms | Corpus encode ms | Chunks | Pages |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bge-m3 | VALID | PUBLISHABLE | 0.6111 | 0.7111 | 0.7889 | 0.8444 | 0.08444 | 0.6756 | 0.7159 | 327.9 | 374.1 | 7.147e+06 | 3329 | 1938 |
| e5-base | VALID | PUBLISHABLE | 0.4778 | 0.6111 | 0.6556 | 0.7444 | 0.07444 | 0.5605 | 0.6045 | 91.92 | 144 | 1.97e+06 | 3329 | 1938 |
| e5-small | VALID | PUBLISHABLE | 0.4111 | 0.6222 | 0.7111 | 0.8222 | 0.08222 | 0.5339 | 0.6029 | 59.07 | 121.1 | 6.632e+05 | 3329 | 1938 |

## Decisão ratificada

**`intfloat/multilingual-e5-small` (384 dimensões)** é o embedding do V1. Embora BGE-M3 lidere
as métricas de retrieval (Recall@10 0,8444, MRR@10 0,6756 e NDCG@10 0,7159), E5-small entrega
Recall@10 de 0,8222 com p95 de consulta de 121,1 ms e encoding do corpus em 11,05 minutos, contra
374,1 ms e 119,11 minutos do BGE-M3 em CPU. A decisão prioriza custo e latência do ambiente
operacional V1 sem abrir mão do desempenho multilíngue necessário para pt-BR.

E5-base não supera E5-small em Recall@10 e é 2,97 vezes mais lento para encoding. MiniLM-L6-v2
está excluído: 2.801 de 3.329 passages excederam seu limite de 256 tokens e o resultado foi
corretamente marcado como não publicável.

Todos os resultados comparados usaram o dataset v1 congelado (120 itens, 1.938 páginas, 3.329
chunks, corpus SHA-256 `7371bb506f81be465c9f8852dfd34d73a0d1d22f38913b036b1d864e4545a638`) e
validação de truncagem do texto preparado. BGE-M3 permanece candidato para uma futura implantação
com GPU e orçamento de armazenamento/latência compatíveis.
