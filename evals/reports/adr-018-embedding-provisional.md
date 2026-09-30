# ADR-018 Embedding Benchmark Comparison — INVALIDATED

> **Invalidated on 2026-08-04:** prepared-passage validation found that 1,309 of 3,330
> E5 chunks exceeded the 512-token model limit after adding `passage: `. MiniLM also used
> a 512-token chunk target despite its 256-token limit. These numbers must not be used for
> model selection or ADR ratification. The corrected harness reserves the prefix, validates every
> prepared passage and records `embedding_inputs`; a full rerun awaits the approved frozen dataset.

| Model | Status | Recall@1 | Recall@3 | Recall@5 | Recall@10 | Precision@10 | MRR@10 | NDCG@10 | p50 query ms | p95 query ms | Corpus encode ms | Chunks | Pages |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bge-m3 | PROVISIONAL | 0.5444 | 0.6889 | 0.7778 | 0.8444 | 0.08444 | 0.6356 | 0.6858 | 308.9 | 369.8 | 8.548e+06 | 3330 | 1938 |
| e5-base | PROVISIONAL | 0.4778 | 0.6333 | 0.7 | 0.7778 | 0.07778 | 0.5731 | 0.6221 | 97.55 | 145.6 | 1.853e+06 | 3330 | 1938 |
| e5-small | PROVISIONAL | 0.4111 | 0.5889 | 0.6778 | 0.7889 | 0.07889 | 0.5246 | 0.5878 | 48.65 | 115.2 | 5.172e+05 | 3330 | 1938 |
| minilm-l6-v2 | PROVISIONAL | 0.1222 | 0.2222 | 0.2667 | 0.3222 | 0.03222 | 0.1842 | 0.2175 | 27 | 36.74 | 1.847e+05 | 3330 | 1938 |

**PROVISIONAL:** at least one result is based on a draft or otherwise non-publishable dataset. Do not cite these numbers as ADR ratification.

## Controle metodológico

- Mesmo corpus: 1.938 páginas e 3.330 chunks para todos os candidatos.
- Tokenizer de chunking fixo: `intfloat/multilingual-e5-small`, 512 tokens e overlap 64.
- Hash do corpus: `7371bb506f81be465c9f8852dfd34d73a0d1d22f38913b036b1d864e4545a638`.
- Dataset: 120 itens draft; 90 respondíveis/parciais nas métricas de retrieval e 30 não respondíveis para calibração.
- Execução local em CPU; tempos não devem ser extrapolados para GPU sem nova medição.

## Seleção histórica invalidada

Antes da descoberta da truncagem, `intfloat/multilingual-e5-small` seria usado no benchmark de
chunking do V1. O BGE-M3 obteve
as melhores métricas de qualidade, mas seu encoding foi 16,5 vezes mais lento, sua dimensão é
2,67 vezes maior e sua consulta p95 foi 3,2 vezes mais lenta que E5-small neste ambiente. E5-small
preservou o segundo melhor Recall@10 (0,7889) com encoding de 8,6 minutos.

Esta seleção foi invalidada. Após revisão, aprovação e congelamento do dataset, a matriz deve ser
repetida com o gate de truncagem ativo.
