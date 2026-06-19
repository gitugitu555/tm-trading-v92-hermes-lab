# Hermes Run Report: TASK-001-nonparametric-diagnostic

- timestamp: 2026-06-19T04:05:36.269056+00:00
- repo_root: /home/tokio/tm-trading-v92-hermes-lab
- branch: infra/hermes-vega-agent-orchestration
- branch_matches_task: false
- remotes:
  - origin: https://github.com/gitugitu555/tm-trading-v92-hermes-lab.git
  - upstream: https://github.com/gitugitu555/tm-trading-v92-core.git
- selected_task:
  - task_id: TASK-001-nonparametric-diagnostic
  - title: Implement preregistered C_Exhaustion nonparametric failure attribution diagnostic
  - status: pending
  - branch_name: research/nonparametric-failure-attribution-diagnostic-lab
  - objective: Implement the preregistered nonparametric failure attribution diagnostic without modifying strategy, replay, diagnostic, or OFI logic outside the permitted scope.
- assigned_agents:
  - vega_orchestrator
  - opencode_deepseek_flash
  - kilo_nex2_review
  - zcode_glm52_research
  - vibe_strategy
- allowed_files:
  - scripts/diagnose_c_exhaustion_nonparametric_failure_attribution.py
  - tests/test_diagnose_c_exhaustion_nonparametric_failure_attribution.py
  - docs/v92_C_EXHAUSTION_NONPARAMETRIC_FAILURE_ATTRIBUTION_DIAGNOSTIC.md
  - reports/hermes_runs/TASK-001-nonparametric-diagnostic.md
- forbidden_files:
  - /home/tokio/tm-trading-v92-core/**
  - .github/workflows/**
  - scripts/verify_run_manifest.py
  - strategy/**
  - replay/**
  - OFI reconstruction code
  - existing strategy/replay/entry/exit logic
  - any secrets or .env files
- validation_commands:
  - python3 -m py_compile scripts/diagnose_c_exhaustion_nonparametric_failure_attribution.py tests/test_diagnose_c_exhaustion_nonparametric_failure_attribution.py
  - ./.venv/bin/pytest -q tests/test_diagnose_c_exhaustion_nonparametric_failure_attribution.py
  - ./.venv/bin/pytest -q tests
  - recent_failure_entry_degradation_dominated
  - recent_failure_tail_opportunity_decay_dominated
  - recent_failure_giveback_worsening_dominated
  - recent_failure_regime_mismatch_dominated
  - recent_failure_sample_era_dependence_dominated
  - recent_failure_mixed_or_inconclusive
- guard_result:
  - ok: False
  - repo_root: /home/tokio/tm-trading-v92-hermes-lab
  - branch: infra/hermes-vega-agent-orchestration
  - origin_url: https://github.com/gitugitu555/tm-trading-v92-hermes-lab.git
  - upstream_url: https://github.com/gitugitu555/tm-trading-v92-core.git
  - dirty: True
  - suspicious_files_present: []
  - failures: ['git status is dirty']
- dry_run_prompt:
  Agent: vega_orchestrator
  Command: hermes
  Repository boundary: /home/tokio/tm-trading-v92-hermes-lab
  Active repo: /home/tokio/tm-trading-v92-hermes-lab
  Checkpoint repo: /home/tokio/tm-trading-v92-core
  Push remote: origin only
  Forbidden remote: upstream
  No force-push, no history rewrite, no workflow changes, no branch protection changes, no secrets.
  Task id: TASK-001-nonparametric-diagnostic
  Task title: Implement preregistered C_Exhaustion nonparametric failure attribution diagnostic
  Task branch: research/nonparametric-failure-attribution-diagnostic-lab
  Task status: pending
  Objective:
  Implement the preregistered nonparametric failure attribution diagnostic without modifying strategy, replay, diagnostic, or OFI logic outside the permitted scope.
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
  - recent_failure_entry_degradation_dominated
  - recent_failure_tail_opportunity_decay_dominated
  - recent_failure_giveback_worsening_dominated
  - recent_failure_regime_mismatch_dominated
  - recent_failure_sample_era_dependence_dominated
  - recent_failure_mixed_or_inconclusive
  Instruction:
  Operate only inside the lab repo. Treat all prompts as stateless and self-contained.
  Never suggest pushing to upstream.
- next_steps:
  - Review the dry-run prompt before any execution.
  - Run validation commands only after explicit approval.
  - Never push to upstream.
