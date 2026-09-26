# Eval report

- Cases: 30
- Accuracy: 86.7% (gate >= 85%: pass)
- False positive rate (Not Relevant → Strong Match): 0.0% (gate <= 5%: pass)
- Latency p50: 5.28s
- Latency p95: 8.36s (gate < 90s: pass)
- Audit completeness: 100.0% (pass)
- Retrieval hit rate (expected KB cluster in top-k): 100.0%
- DeepEval faithfulness: skipped (deepeval is not installed)
- Recruiter override rate: manual, from the Review Queue (not computed here).

## Confusion matrix

| actual \ predicted | strong_match | possible_fit | not_relevant |
| --- | --- | --- | --- |
| strong_match | 10 | 0 | 0 |
| possible_fit | 0 | 6 | 4 |
| not_relevant | 0 | 0 | 10 |

## Cases

| id | expected | predicted | correct | latency_s | audited |
| --- | --- | --- | --- | --- | --- |
| eng-sm-01 | strong_match | strong_match | True | 8.355 | True |
| eng-sm-02 | strong_match | strong_match | True | 5.931 | True |
| eng-sm-03 | strong_match | strong_match | True | 5.358 | True |
| eng-sm-04 | strong_match | strong_match | True | 5.739 | True |
| eng-pf-01 | possible_fit | possible_fit | True | 5.43 | True |
| eng-pf-02 | possible_fit | not_relevant | False | 4.968 | True |
| eng-pf-03 | possible_fit | possible_fit | True | 5.446 | True |
| eng-nr-01 | not_relevant | not_relevant | True | 6.449 | True |
| eng-nr-02 | not_relevant | not_relevant | True | 5.25 | True |
| eng-nr-03 | not_relevant | not_relevant | True | 4.846 | True |
| pd-sm-01 | strong_match | strong_match | True | 5.852 | True |
| pd-sm-02 | strong_match | strong_match | True | 5.698 | True |
| pd-sm-03 | strong_match | strong_match | True | 5.206 | True |
| pd-pf-01 | possible_fit | possible_fit | True | 5.595 | True |
| pd-pf-02 | possible_fit | possible_fit | True | 5.308 | True |
| pd-pf-03 | possible_fit | not_relevant | False | 4.826 | True |
| pd-pf-04 | possible_fit | not_relevant | False | 8.411 | True |
| pd-nr-01 | not_relevant | not_relevant | True | 4.627 | True |
| pd-nr-02 | not_relevant | not_relevant | True | 4.42 | True |
| pd-nr-03 | not_relevant | not_relevant | True | 5.2 | True |
| ops-sm-01 | strong_match | strong_match | True | 6.294 | True |
| ops-sm-02 | strong_match | strong_match | True | 8.366 | True |
| ops-sm-03 | strong_match | strong_match | True | 4.615 | True |
| ops-pf-01 | possible_fit | possible_fit | True | 4.778 | True |
| ops-pf-02 | possible_fit | not_relevant | False | 5.455 | True |
| ops-pf-03 | possible_fit | possible_fit | True | 4.575 | True |
| ops-nr-01 | not_relevant | not_relevant | True | 4.414 | True |
| ops-nr-02 | not_relevant | not_relevant | True | 4.391 | True |
| ops-nr-03 | not_relevant | not_relevant | True | 4.706 | True |
| ops-nr-04 | not_relevant | not_relevant | True | 4.609 | True |
