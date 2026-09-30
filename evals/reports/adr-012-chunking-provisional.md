# ADR-012 Chunking Benchmark Comparison — INVALIDATED

> **Invalidated on 2026-08-04:** esta matriz herdou chunks E5 truncados e uma formulação de NDCG
> que subavaliava chunks multipágina. O chunker agora reserva o prefixo de embedding, mede o texto
> concatenado exatamente e preserva overlap parcial; o NDCG usa ganho por novas páginas cobertas.
> Estes números não podem selecionar estratégia nem ratificar ADR-012.

| Strategy | Version | Model | Validity | Status | Recall@10 | MRR@10 | NDCG@10 | p95 query ms | Chunking ms | Corpus encode ms | Chunks |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| semantic | semantic-percentile-v1-t1024-o128 | e5-small | INVALID_MODEL_LIMIT | PROVISIONAL | 0.7333 | 0.4784 | 0.5396 | 49.26 | 2.314e+06 | 3.108e+05 | 1477 |
| semantic | semantic-percentile-v1-t256-o32 | e5-small | VALID | PROVISIONAL | 0.7556 | 0.5686 | 0.6145 | 53.22 | 2.349e+06 | 5.785e+05 | 6020 |
| semantic | semantic-percentile-v1-t512-o64 | e5-small | VALID | PROVISIONAL | 0.7889 | 0.5591 | 0.6149 | 65.01 | 2.296e+06 | 6.854e+05 | 3160 |
| structural | structural-v1-t1024-o128 | e5-small | INVALID_MODEL_LIMIT | PROVISIONAL | 0.7778 | 0.5251 | 0.5868 | 68.57 | 1.68e+04 | 3.65e+05 | 1668 |
| structural | structural-v1-t256-o32 | e5-small | VALID | PROVISIONAL | 0.7111 | 0.5259 | 0.5706 | 111.8 | 5.9e+04 | 5.505e+05 | 5773 |
| structural | structural-v1-t512-o64 | e5-small | VALID | PROVISIONAL | 0.7889 | 0.5246 | 0.5878 | 44.34 | 7.77e+04 | 6.191e+05 | 3330 |

**PROVISIONAL:** the dataset is not frozen and approved. Do not use this comparison to ratify ADR-012.

## Controle metodológico

- Mesmo embedding: `intfloat/multilingual-e5-small`.
- Mesmo corpus, dataset, tokenizer canônico e ambiente CPU em todas as variantes.
- Segmentos semânticos são produzidos pelo `SemanticChunker` com breakpoint `percentile`, agregados
  até o alvo token-aware e limitados com overlap.
- Chunks multipágina preservam todas as páginas contribuintes; relevância usa interseção com as
  páginas esperadas.
- Variantes de 1024 tokens são `INVALID_MODEL_LIMIT`: E5-small aceita no máximo 512 tokens e
  truncaria conteúdo silenciosamente. Seus números não participam da seleção.

## Seleção histórica invalidada

Antes da invalidação, `structural-v1-t512-o64` permaneceria como baseline do V1. A variante
semântica 512 obteve o mesmo
Recall@10 (0,7889), com MRR@10 0,5591 contra 0,5246 e NDCG@10 0,6149 contra 0,5878, mas exigiu
2.296 segundos de chunking contra 77,7 segundos — aproximadamente 29,5 vezes mais tempo — sem ganho
de recall.

Nenhuma seleção desta matriz permanece válida. As variantes devem ser reexecutadas após revisão,
aprovação e congelamento do dataset, seguidas da etapa Ragas/RAG Triad.
