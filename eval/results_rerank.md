## Scores by chunking configuration

| config | language | questions | hit@1 | hit@3 | hit@5 | MRR |
|---|---|---:|---:|---:|---:|---:|
| vector | fr | 5 | 100% | 100% | 100% | 1.00 |
| vector | ar | 5 | 80% | 100% | 100% | 0.90 |
| vector | all | 10 | 90% | 100% | 100% | 0.95 |
| reranked | fr | 5 | 80% | 100% | 100% | 0.90 |
| reranked | ar | 5 | 100% | 100% | 100% | 1.00 |
| reranked | all | 10 | 90% | 100% | 100% | 0.95 |

## Rank of the right chunk per question ('-' = not found)

| id | language | vector | reranked |
|---|---|---:|---:|
| fr-1 | fr | 1 | 1 |
| fr-2 | fr | 1 | 1 |
| fr-3 | fr | 1 | 2 |
| fr-4 | fr | 1 | 1 |
| fr-5 | fr | 1 | 1 |
| ar-1 | ar | 2 | 1 |
| ar-2 | ar | 1 | 1 |
| ar-3 | ar | 1 | 1 |
| ar-4 | ar | 1 | 1 |
| ar-5 | ar | 1 | 1 |
