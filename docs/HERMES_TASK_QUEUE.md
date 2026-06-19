# Hermes Task Queue

## TASK-001-nonparametric-diagnostic

Title: Implement preregistered C_Exhaustion nonparametric failure attribution diagnostic

Status: pending

Branch: research/nonparametric-failure-attribution-diagnostic-lab

Assigned agent:

- opencode_deepseek_flash for implementation
- kilo_nex2_review for review
- zcode_glm52_research for research/context if needed
- vibe_strategy for strategy interpretation if needed
- vega_orchestrator for run control

Objective: Implement the preregistered nonparametric failure attribution diagnostic without modifying strategy, replay, diagnostic, or OFI logic outside the permitted scope.

Context:

This task is intentionally narrow. It is a lab-only diagnostic effort that must respect the repo boundary and cannot touch the checkpoint repo or any forbidden files.

Allowed files:

- scripts/diagnose_c_exhaustion_nonparametric_failure_attribution.py
- tests/test_diagnose_c_exhaustion_nonparametric_failure_attribution.py
- docs/v92_C_EXHAUSTION_NONPARAMETRIC_FAILURE_ATTRIBUTION_DIAGNOSTIC.md
- reports/hermes_runs/TASK-001-nonparametric-diagnostic.md

Forbidden files:

- /home/tokio/tm-trading-v92-core/**
- .github/workflows/**
- scripts/verify_run_manifest.py
- strategy/**
- replay/**
- OFI reconstruction code
- existing strategy/replay/entry/exit logic
- any secrets or .env files

Validation commands:

- python3 -m py_compile scripts/diagnose_c_exhaustion_nonparametric_failure_attribution.py tests/test_diagnose_c_exhaustion_nonparametric_failure_attribution.py
- ./.venv/bin/pytest -q tests/test_diagnose_c_exhaustion_nonparametric_failure_attribution.py
- ./.venv/bin/pytest -q tests

Decision labels:

- recent_failure_entry_degradation_dominated
- recent_failure_tail_opportunity_decay_dominated
- recent_failure_giveback_worsening_dominated
- recent_failure_regime_mismatch_dominated
- recent_failure_sample_era_dependence_dominated
- recent_failure_mixed_or_inconclusive

Final report required: true
