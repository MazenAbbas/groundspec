# Domain guidance: data science and machine learning

Select `--domain data-science-ml` for classification, regression, clustering, recommendation, ranking, anomaly detection, time-series forecasting, computer vision, NLP, retrieval/RAG evaluation, model comparison, dataset preparation, exploratory modeling, or a production-readiness review. Read this pack's actual structure with `groundspec pack inspect data-science-ml` for the exact rule/gate text.

**This pack is deliberately lightweight.** Groundspec must remain usable on an ordinary student laptop with no GPU -- it never imports pandas, NumPy, scikit-learn, PyTorch, TensorFlow, or Jupyter, and never trains, runs, or evaluates a model itself. It validates plans, contracts, evidence, and completion claims; the actual modeling work happens outside Groundspec, in whatever environment the task uses.

## Combine with other packs

`software` when the task also adds a real prediction endpoint to an existing service (see the worked example: "Add a prediction endpoint to an existing Python service" → `software` + `data-science-ml`). `research` when the task is fundamentally an experiment-design question (see: "Design a churn prediction experiment" → `data-science-ml` + `research`). `content` if a launch post or announcement claims something about a model's accuracy (see: "Audit a launch post about model accuracy" → `content` + `data-science-ml`).

## The clarification checklist (see `questions.toml`)

Ask only when material, per this Skill's general clarification policy: the decision/outcome the model supports, the prediction target, the unit of analysis, dataset source, label definition, deployment environment, error-cost asymmetry, latency/cost constraints, regulated-or-sensitive use, evaluation budget, and whether the work is exploratory, benchmark-oriented, or production-facing. The last one is load-bearing: it determines which completion gates below actually apply -- an exploratory notebook is not held to the production-readiness bar.

## Split and leakage discipline

**A single random split must never be accepted automatically for grouped or temporal data.** State the unit of analysis, then pick the split strategy that actually matches it: random (only for genuinely i.i.d. rows), group/entity (when multiple rows share an entity, e.g. multiple sessions per user), time-based (when the deployment use case involves predicting the future from the past), geographical or source-based (when generalization across regions/sources is the actual claim), or user-level (recommendation/personalization tasks, where user-level train/test overlap silently inflates offline metrics). Actively check for target leakage, duplicate-row leakage, entity overlap, temporal look-ahead, preprocessing fitted on the full dataset before splitting, features built from post-outcome information, and hyperparameters tuned against the final test set -- do not just assert their absence.

## Baselines and metrics

**Do not accept "accuracy" automatically for every classification task.** Justify the primary metric against the decision's actual error-cost asymmetry -- a severely imbalanced fraud-detection task where missing fraud is far more costly than a false alarm needs a metric (precision/recall/F1/AUC at an appropriate operating point) that reflects that, not a headline accuracy number that a majority-class baseline could already achieve. State the baseline explicitly; an improvement claim with no comparison and no evaluation protocol is not meaningful.

## Reproducibility, scaled to the claim's weight

Record dataset version/hash, split definition, seed, environment, code revision, config, and the evaluation command -- proportional to how much weight the result carries. A five-minute exploratory sanity check does not need the same rigor as a result meant to justify a build/no-build or production decision. Never claim perfect reproducibility where real nondeterminism remains (GPU non-determinism, an external API that changes over time) -- disclose it instead of asserting a false guarantee.

## Production claims need more than one offline score

An offline evaluation score alone can never establish production readiness. A genuine production-readiness claim needs evidence across held-out evaluation, baseline comparison, latency, resource use, monitoring, data/model drift, rollback, input validation, privacy/security, failure handling, ownership, and a retraining/update policy -- see `evidence-policy.toml`'s `production-readiness-is-multi-dimensional` policy and this pack's `production-claim-single-offline-score` completion gate, which forces `FAIL` when a production claim rests on only one number.

## Evidence labels for data-science claims

This pack reuses the existing schema 0.4.0 evidence taxonomy (`MEASURED`/`PRIMARY_SOURCE_VERIFIED`/`SECONDARY_SOURCE_SUPPORTED`/`USER_CONFIRMED`/`MODEL_EVALUATED`/`ASSUMPTION`/`RESEARCH_NEEDED`) -- see `evidence-policy.toml`'s `evidence-label-mapping` policy for exactly how a "measured experiment result," "reproduced result," "source-backed claim," "user-confirmed constraint," "model-evaluated recommendation," "assumption," "pending experiment," or "unavailable evidence" maps onto those seven labels. No new labels are introduced.

## Error analysis and fairness, scaled to risk

Do not require every fairness check for every harmless toy task -- but do not skip error analysis by default either. Scale failure-category, subgroup, rare-class, calibration, and drift analysis to the task's actual risk and intended use, and state explicitly which analyses were performed and which were judged unnecessary, and why.

## Completion-gate behavior specific to this pack (see `completion-gates.toml`)

Nine gates, fed by `evidence.json` fields an evaluator (human or model) must populate honestly -- the CLI cannot itself detect leakage, judge a metric's fit to a decision, or confirm dataset provenance from contract structure alone:

- `ds_no_baseline_for_performance_claim` -- INCOMPLETE.
- `ds_final_test_set_used_for_tuning` -- FAILs (a methodological violation, not a missing-evidence gap).
- `ds_unresolved_leakage_risk` -- FAILs.
- `ds_dataset_provenance_unknown` -- INCOMPLETE.
- `ds_metric_mismatched_to_objective` -- INCOMPLETE.
- `ds_production_claim_single_offline_score` -- FAILs.
- `ds_insufficient_reproducibility_info` -- INCOMPLETE.
- `ds_high_stakes_missing_domain_review` -- FAILs.
- `ds_exploratory_missing_experiments_disclosed` -- downgrades to PASS_WITH_CAVEATS, not a failure: honestly disclosed exploratory gaps are the correct behavior, not a defect.

Report each triggered gate's `rationale` verbatim in your final report, exactly like a hard-constraint failure.

## What this pack does not do

It does not run, train, or evaluate any model, and it does not itself detect leakage, bias, or a metric/objective mismatch -- it requires that these be actively considered and the result disclosed honestly, exactly like `product-management`'s relationship to user research and legal review. A model comparison or exploratory result that honestly states its remaining gaps can still reach `PASS_WITH_CAVEATS`; only a claim that overstates what the evidence actually shows reaches `FAIL`.
