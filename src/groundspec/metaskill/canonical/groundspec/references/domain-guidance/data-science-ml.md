# Domain guidance: data science and machine learning

Select `--domain data-science-ml` for classification, regression, clustering, recommendation, ranking, anomaly detection, time-series forecasting, computer vision, NLP, retrieval/RAG evaluation, model comparison, dataset preparation, exploratory modeling, or a production-readiness review. Read the pack's actual rules/gates/questions with `groundspec pack inspect data-science-ml` (or the guidance file bundled inside the pack itself) for full detail.

**This pack is deliberately lightweight** -- it never requires pandas, NumPy, scikit-learn, PyTorch, TensorFlow, or Jupyter, and it never trains, runs, or evaluates a model itself. It validates plans, contracts, evidence, and completion claims; the actual modeling happens outside Groundspec.

## Combine with other packs

`software` when the task also adds a real prediction endpoint to an existing service. `research` when the task is fundamentally an experiment-design question. `content` if a launch post or announcement claims something about a model's accuracy.

## The clarification checklist

Ask only when material: the decision/outcome the model supports, the prediction target, the unit of analysis, dataset source, label definition, deployment environment, error-cost asymmetry, latency/cost constraints, regulated-or-sensitive use, evaluation budget, and whether the work is exploratory, benchmark-oriented, or production-facing. The last one determines which completion gates below actually apply -- an exploratory notebook is not held to the production-readiness bar.

## Split, leakage, and metric discipline

A single random split must never be accepted automatically for grouped or temporal data -- state the unit of analysis, then pick the split strategy that matches it (random/group/time/geography/source/user-level), and actively check for target leakage, duplicate leakage, entity overlap, temporal look-ahead, preprocessing fit on the full dataset, and test-set tuning. Do not accept "accuracy" automatically for every classification task -- justify the primary metric against the decision's actual error-cost asymmetry, and always state a baseline.

## Completion gates this pack contributes

Nine gates, fed by `evidence.json` fields you (or a human reviewer) must populate honestly:

| `evidence.json` field | Effect when `true` |
|---|---|
| `ds_no_baseline_for_performance_claim` | INCOMPLETE |
| `ds_final_test_set_used_for_tuning` | FAIL |
| `ds_unresolved_leakage_risk` | FAIL |
| `ds_dataset_provenance_unknown` | INCOMPLETE |
| `ds_metric_mismatched_to_objective` | INCOMPLETE |
| `ds_production_claim_single_offline_score` | FAIL |
| `ds_insufficient_reproducibility_info` | INCOMPLETE |
| `ds_high_stakes_missing_domain_review` | FAIL |
| `ds_exploratory_missing_experiments_disclosed` | PASS_WITH_CAVEATS |

An offline score alone never establishes production readiness -- a production claim needs evidence across evaluation, baseline, latency, resource use, monitoring, drift, rollback, input validation, privacy/security, failure handling, ownership, and a retraining policy. Exploratory work that honestly discloses its own gaps earns `PASS_WITH_CAVEATS`, not a failure.
