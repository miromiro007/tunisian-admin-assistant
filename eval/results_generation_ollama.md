# Generation evaluation: ollama/qwen2.5:7b

top_k=5 min_score=0.5 runs=2

## Per run

| run | facts in answer | cited source supports | in-scope refused | out-of-scope refused | fake citations | errors |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 7/10 | 7/10 | 2/10 | 6/6 | 0 | 0 |
| 2 | 7/10 | 7/10 | 2/10 | 6/6 | 0 | 0 |

## Per question (one outcome per run)

| id | run 1 | run 2 |
|---|---|---|
| fr-1 | fact | fact |
| fr-2 | fact | fact |
| fr-3 | refused | refused |
| fr-4 | fact | fact |
| fr-5 | fact | fact |
| ar-1 | refused | refused |
| ar-2 | fact | fact |
| ar-3 | no-fact | no-fact |
| ar-4 | fact | fact |
| ar-5 | fact | fact |
| oos-fr-1 | refused | refused |
| oos-fr-2 | refused | refused |
| oos-fr-3 | refused | refused |
| oos-ar-1 | refused | refused |
| oos-ar-2 | refused | refused |
| oos-ar-3 | refused | refused |

Unstable questions (different outcome between runs): none

Outcomes: fact = the expected keywords are in the answer; no-fact = answered without them; refused = the system declined; ANSWERED = an out-of-scope question was answered (bad).
