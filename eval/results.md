## Scores by chunking configuration

| config | language | questions | hit@1 | hit@3 | hit@5 | MRR |
|---|---|---:|---:|---:|---:|---:|
| article_1500 | fr | 5 | 80% | 80% | 80% | 0.80 |
| article_1500 | ar | 5 | 80% | 100% | 100% | 0.90 |
| article_1500 | all | 10 | 80% | 90% | 90% | 0.85 |
| fixed_500 | fr | 5 | 60% | 60% | 60% | 0.60 |
| fixed_500 | ar | 5 | 20% | 100% | 100% | 0.50 |
| fixed_500 | all | 10 | 40% | 80% | 80% | 0.55 |
| fixed_1000 | fr | 5 | 80% | 80% | 80% | 0.80 |
| fixed_1000 | ar | 5 | 40% | 80% | 80% | 0.60 |
| fixed_1000 | all | 10 | 60% | 80% | 80% | 0.70 |

## Rank of the right chunk per question ('-' = not found)

| id | language | article_1500 | fixed_500 | fixed_1000 |
|---|---|---:|---:|---:|
| fr-1 | fr | 1 | 1 | 1 |
| fr-2 | fr | 1 | 1 | 1 |
| fr-3 | fr | - | - | - |
| fr-4 | fr | 1 | 1 | 1 |
| fr-5 | fr | 1 | - | 1 |
| ar-1 | ar | 2 | 3 | - |
| ar-2 | ar | 1 | 3 | 2 |
| ar-3 | ar | 1 | 3 | 1 |
| ar-4 | ar | 1 | 1 | 1 |
| ar-5 | ar | 1 | 2 | 2 |
