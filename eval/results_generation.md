provider=ollama/qwen2.5:7b top_k=5 min_score=0.5

## In-scope questions

| id | best score | right chunk retrieved | refused | facts in answer | cited source supports | invalid citations |
|---|---:|---|---|---|---|---:|
| fr-1 | 0.799 | yes | no | yes | yes | 0 |
| fr-2 | 0.741 | yes | no | yes | yes | 0 |
| fr-3 | 0.757 | yes | yes | no | no | 0 |
| fr-4 | 0.668 | yes | no | no | no | 0 |
| fr-5 | 0.763 | yes | no | yes | yes | 0 |
| ar-1 | 0.591 | yes | yes | no | no | 0 |
| ar-2 | 0.699 | yes | no | yes | yes | 0 |
| ar-3 | 0.641 | yes | no | no | yes | 0 |
| ar-4 | 0.757 | yes | no | yes | yes | 0 |
| ar-5 | 0.597 | yes | no | yes | yes | 0 |

## Out-of-scope questions (the right behavior is to refuse)

| id | best score | outcome |
|---|---:|---|
| oos-fr-1 | 0.591 | model_declined |
| oos-fr-2 | 0.617 | model_declined |
| oos-fr-3 | 0.546 | model_declined |
| oos-ar-1 | 0.537 | model_declined |
| oos-ar-2 | 0.615 | model_declined |
| oos-ar-3 | 0.485 | below_threshold |

## Summary

- in-scope refused (over-refusal): 2/10
- in-scope answers containing the expected facts: 6/10
- in-scope answers whose cited source supports the facts: 7/10
- answers with no citation at all: 0
- invalid (fake) citations: 0
- out-of-scope refused (correct): 6/6
