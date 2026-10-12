## Scores by chunking configuration

| config | language | questions | hit@1 | hit@3 | hit@5 | MRR |
|---|---|---:|---:|---:|---:|---:|
| vector | fr | 5 | 100% | 100% | 100% | 1.00 |
| vector | ar | 5 | 80% | 100% | 100% | 0.90 |
| vector | all | 10 | 90% | 100% | 100% | 0.95 |
| keyword | fr | 5 | 0% | 20% | 20% | 0.10 |
| keyword | ar | 5 | 40% | 80% | 80% | 0.57 |
| keyword | all | 10 | 20% | 50% | 50% | 0.33 |
| hybrid | fr | 5 | 40% | 60% | 100% | 0.58 |
| hybrid | ar | 5 | 100% | 100% | 100% | 1.00 |
| hybrid | all | 10 | 70% | 80% | 100% | 0.79 |

## Rank of the right chunk per question ('-' = not found)

| id | language | vector | keyword | hybrid |
|---|---|---:|---:|---:|
| fr-1 | fr | 1 | - | 2 |
| fr-2 | fr | 1 | - | 1 |
| fr-3 | fr | 1 | 2 | 1 |
| fr-4 | fr | 1 | - | 5 |
| fr-5 | fr | 1 | - | 5 |
| ar-1 | ar | 2 | - | 1 |
| ar-2 | ar | 1 | 3 | 1 |
| ar-3 | ar | 1 | 1 | 1 |
| ar-4 | ar | 1 | 1 | 1 |
| ar-5 | ar | 1 | 2 | 1 |
