# V9.2 OFI Downstream Consumer Audit

## Purpose

Audit every downstream OFI-related reference and classify whether it is safe, research-only, stale, broken, not wired, requires resync-aware handling, or requires provenance validation.

This audit does not approve OFI for production, paper trading, live trading, or alpha use.

## Search Scope

- Repo root: `.`
- File types: `.py`, `.md`, `.toml`, `.yaml`, `.yml`, `.json`, `.txt`
- Ignored directories: `.git/`, `.venv/`, `__pycache__/`, `data/`, `reports/`, `tmp_diagnostics/`

## Method

- Scan the repository for OFI-related symbols and related signed-flow terms.
- Classify each unique file/reference pair by reference type, consumer type, status, risk, and required action.
- Summarize replay / strategy usage, data-policy usage, resync risk, coverage risk, and documentation drift.

## Executive Finding

The repaired OFI engine is present, but no replay or production strategy path is wired to consume it. Current usage is concentrated in feature-builder code, research diagnostics, data-policy helpers, tests, and documentation.

## Reference Inventory

| path | symbol_or_function | reference_type | consumer_type | status | risk | required_action | occurrences | first_line |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| README.md | OFI | documentation | documentation | stale | aspirational language can be read as readiness if not caveated. | Rewrite or annotate as research-only historical context. | 2 | 15 |
| README.md | microstructure_ofi | documentation | documentation | stale | aspirational language can be read as readiness if not caveated. | Rewrite or annotate as research-only historical context. | 1 | 15 |
| README.md | order_flow_imbalance | documentation | documentation | stale | aspirational language can be read as readiness if not caveated. | Rewrite or annotate as research-only historical context. | 1 | 15 |
| docs/V92_FUTURE_ROADMAP_SOURCE_OF_TRUTH.md | OFI | documentation | documentation | research_only | documentation only; not operational wiring. | Keep caveated as research context only. | 1 | 350 |
| docs/roadmaps/TM_Trading_V92_Master_Roadmap.md | OFI | documentation | documentation | research_only | documentation only; not operational wiring. | Keep caveated as research context only. | 6 | 21 |
| docs/v92_750BTC_RAW_REBUILD_PARITY_AUDIT.md | volume_delta | documentation | documentation | research_only | documentation only; not operational wiring. | Keep caveated as research context only. | 2 | 113 |
| docs/v92_ALPHA_REBUILD_BACKLOG.md | OFI | documentation | documentation | research_only | documentation only; not operational wiring. | Keep caveated as research context only. | 5 | 36 |
| docs/v92_C_EXHAUSTION_META_LABEL_BASELINE_PLAN.md | OFI | documentation | documentation | research_only | documentation only; not operational wiring. | Keep caveated as research context only. | 1 | 111 |
| docs/v92_C_EXHAUSTION_RESEARCH_DECISION.md | OFI | documentation | documentation | research_only | documentation only; not operational wiring. | Keep caveated as research context only. | 1 | 48 |
| docs/v92_DATA_FIRST_ALPHA_PLAN.md | OFI | documentation | documentation | research_only | documentation only; not operational wiring. | Keep caveated as research context only. | 3 | 178 |
| docs/v92_DATA_FIRST_ALPHA_PLAN.md | mlofi | documentation | documentation | research_only | documentation only; not operational wiring. | Keep caveated as research context only. | 3 | 15 |
| docs/v92_EXISTING_750BTC_BAR_INTEGRITY_AUDIT.md | volume_delta | documentation | documentation | research_only | documentation only; not operational wiring. | Keep caveated as research context only. | 348 | 15 |
| docs/v92_OFI_ENGINE_REPAIR.md | OFI | documentation | documentation | research_only | documentation only; not operational wiring. | Keep caveated as research context only. | 8 | 1 |
| docs/v92_OFI_ENGINE_REPAIR.md | requires_resync | documentation | documentation | research_only | documentation only; not operational wiring. | Keep caveated as research context only. | 1 | 35 |
| docs/v92_REGIME_CLASSIFIER_SPEC.md | OFI | documentation | documentation | research_only | documentation only; not operational wiring. | Keep caveated as research context only. | 4 | 29 |
| docs/v92_STRATEGY_IDEATION.md | OFI | documentation | documentation | stale | aspirational language can be read as readiness if not caveated. | Rewrite or annotate as research-only historical context. | 2 | 3 |
| docs/v92_STRATEGY_IDEATION.md | order_flow_imbalance | documentation | documentation | stale | aspirational language can be read as readiness if not caveated. | Rewrite or annotate as research-only historical context. | 1 | 3 |
| docs/v92_STRATEGY_IDEATION.md | volume_delta | documentation | documentation | stale | aspirational language can be read as readiness if not caveated. | Rewrite or annotate as research-only historical context. | 3 | 11 |
| docs/v92_STRATEGY_MEMORY_LEDGER.md | OFI | documentation | documentation | stale | aspirational language can be read as readiness if not caveated. | Rewrite or annotate as research-only historical context. | 3 | 82 |
| docs/v92_STRATEGY_MEMORY_LEDGER.md | book imbalance | documentation | documentation | stale | aspirational language can be read as readiness if not caveated. | Rewrite or annotate as research-only historical context. | 1 | 81 |
| docs/v92_STRATEGY_MEMORY_LEDGER.md | mlofi | documentation | documentation | stale | aspirational language can be read as readiness if not caveated. | Rewrite or annotate as research-only historical context. | 3 | 82 |
| docs/v92_TIER2_BAR_DATA_INTEGRITY_REVIEW.md | volume_delta | documentation | documentation | research_only | documentation only; not operational wiring. | Keep caveated as research context only. | 4 | 5 |
| features/__init__.py | mlofi | import | feature_builder | research_only | OFI-related reference is not a production consumer. | Keep it research-only until explicit wiring and provenance validation exist. | 1 | 21 |
| features/l2_imbalance.py | book imbalance | unused | feature_builder | research_only | OFI-related reference is not a production consumer. | Keep it research-only until explicit wiring and provenance validation exist. | 1 | 1 |
| features/microstructure_numba_ofi.py | ofi | unused | feature_builder | research_only | feature builder is not a wired production consumer. | Validate provenance and downstream coverage before any deployment use. | 5 | 26 |
| features/microstructure_ofi.py | OFI | unused | feature_builder | research_only | feature builder is not a wired production consumer. | Validate provenance and downstream coverage before any deployment use. | 8 | 1 |
| features/microstructure_ofi.py | ofi | unused | feature_builder | research_only | feature builder is not a wired production consumer. | Validate provenance and downstream coverage before any deployment use. | 8 | 178 |
| features/microstructure_ofi.py | order_flow_imbalance | unused | feature_builder | research_only | feature builder is not a wired production consumer. | Validate provenance and downstream coverage before any deployment use. | 1 | 3 |
| features/microstructure_ofi.py | requires_resync | column_reference | feature_builder | research_only | feature builder is not a wired production consumer. | Validate provenance and downstream coverage before any deployment use. | 4 | 50 |
| features/mlofi.py | book imbalance | unused | feature_builder | research_only | OFI-related reference is not a production consumer. | Keep it research-only until explicit wiring and provenance validation exist. | 1 | 56 |
| features/mlofi.py | mlofi | unused | feature_builder | research_only | OFI-related reference is not a production consumer. | Keep it research-only until explicit wiring and provenance validation exist. | 4 | 1 |
| features/mlofi.py | order_flow_imbalance | unused | feature_builder | research_only | OFI-related reference is not a production consumer. | Keep it research-only until explicit wiring and provenance validation exist. | 1 | 9 |
| features/regime_classifier.py | volume_delta | function_call | feature_builder | research_only | OFI-related reference is not a production consumer. | Keep it research-only until explicit wiring and provenance validation exist. | 4 | 33 |
| features/v92_data_policy.py | OFI | unused | data_policy | research_only | OFI-related reference is not a production consumer. | Keep it research-only until explicit wiring and provenance validation exist. | 4 | 5 |
| features/v92_data_policy.py | join_ofi_to_bars_preserve_coverage | function_call | data_policy | safe | bar coverage preserved; no rows dropped. | Keep as the canonical join helper. | 1 | 235 |
| features/v92_data_policy.py | ofi | unused | data_policy | research_only | OFI-related reference is not a production consumer. | Keep it research-only until explicit wiring and provenance validation exist. | 9 | 237 |
| scripts/audit_750btc_raw_rebuild_parity.py | volume_delta | column_reference | research_script | research_only | OFI-related reference is not a production consumer. | Keep it research-only until explicit wiring and provenance validation exist. | 37 | 214 |
| scripts/audit_existing_750btc_bar_integrity.py | volume_delta | column_reference | research_script | research_only | OFI-related reference is not a production consumer. | Keep it research-only until explicit wiring and provenance validation exist. | 21 | 25 |
| scripts/diagnose_c_exhaustion_meta_label_baseline_plan.py | OFI | unused | research_script | research_only | OFI-related reference is not a production consumer. | Keep it research-only until explicit wiring and provenance validation exist. | 1 | 227 |
| scripts/v92_alpha_strategy_test.py | OFI | unused | research_script | not_wired | research harness only; not part of replay or production strategy wiring. | Do not treat as an approved trading path. | 9 | 3 |
| scripts/v92_alpha_strategy_test.py | join_ofi_to_bars_preserve_coverage | unused | research_script | not_wired | research harness only; not part of replay or production strategy wiring. | Do not treat as an approved trading path. | 3 | 30 |
| scripts/v92_alpha_strategy_test.py | ofi | unused | research_script | not_wired | research harness only; not part of replay or production strategy wiring. | Do not treat as an approved trading path. | 1 | 169 |
| scripts/v92_alpha_strategy_test.py | volume_delta | column_reference | research_script | not_wired | research harness only; not part of replay or production strategy wiring. | Do not treat as an approved trading path. | 4 | 96 |
| scripts/v92_l2_cache_builder.py | OFI | unused | feature_builder | requires_provenance_validation | OFI extraction cache requires raw-L2 provenance checks. | Validate raw L2 provenance and sequence coverage before trusting derived OFI bars. | 7 | 3 |
| scripts/v92_l2_cache_builder.py | microstructure_numba_ofi | import | feature_builder | requires_provenance_validation | OFI extraction cache requires raw-L2 provenance checks. | Validate raw L2 provenance and sequence coverage before trusting derived OFI bars. | 1 | 23 |
| scripts/v92_l2_cache_builder.py | ofi | unused | feature_builder | requires_provenance_validation | OFI extraction cache requires raw-L2 provenance checks. | Validate raw L2 provenance and sequence coverage before trusting derived OFI bars. | 2 | 26 |
| scripts/v92_l2_cache_builder.py | order_flow_imbalance | unused | feature_builder | requires_provenance_validation | OFI extraction cache requires raw-L2 provenance checks. | Validate raw L2 provenance and sequence coverage before trusting derived OFI bars. | 1 | 6 |
| scripts/v92_ofi_diagnostics.py | OFI | unused | research_script | requires_resync_handling | diagnostic scripts do not surface resync state to downstream callers. | Propagate resync awareness before using against live feeds. | 9 | 3 |
| scripts/v92_ofi_diagnostics.py | microstructure_ofi | import | research_script | requires_resync_handling | diagnostic scripts do not surface resync state to downstream callers. | Propagate resync awareness before using against live feeds. | 1 | 18 |
| scripts/v92_ofi_diagnostics.py | ofi | column_reference | research_script | requires_resync_handling | diagnostic scripts do not surface resync state to downstream callers. | Propagate resync awareness before using against live feeds. | 5 | 55 |
| scripts/v92_ofi_numba_diagnostic.py | OFI | unused | research_script | requires_resync_handling | diagnostic scripts do not surface resync state to downstream callers. | Propagate resync awareness before using against live feeds. | 8 | 3 |
| scripts/v92_ofi_numba_diagnostic.py | microstructure_numba_ofi | import | research_script | requires_resync_handling | diagnostic scripts do not surface resync state to downstream callers. | Propagate resync awareness before using against live feeds. | 1 | 22 |
| scripts/v92_ofi_numba_diagnostic.py | microstructure_ofi | import | research_script | requires_resync_handling | diagnostic scripts do not surface resync state to downstream callers. | Propagate resync awareness before using against live feeds. | 1 | 21 |
| scripts/v92_ofi_numba_diagnostic.py | ofi | column_reference | research_script | requires_resync_handling | diagnostic scripts do not surface resync state to downstream callers. | Propagate resync awareness before using against live feeds. | 2 | 74 |
| scripts/v92_regime_validation.py | volume_delta | column_reference | research_script | research_only | OFI-related reference is not a production consumer. | Keep it research-only until explicit wiring and provenance validation exist. | 4 | 45 |
| scripts/v92_tier2_cache_builder.py | volume_delta | column_reference | feature_builder | research_only | OFI-related reference is not a production consumer. | Keep it research-only until explicit wiring and provenance validation exist. | 1 | 71 |
| tests/test_c_exhaustion_paper_sim.py | volume_delta | column_reference | test | research_only | test-only reference; not runtime wiring. | Keep tests as coverage, not deployment evidence. | 2 | 33 |
| tests/test_c_exhaustion_replay.py | volume_delta | column_reference | test | research_only | test-only reference; not runtime wiring. | Keep tests as coverage, not deployment evidence. | 1 | 36 |
| tests/test_microstructure_ofi.py | microstructure_ofi | import | test | research_only | test-only reference; not runtime wiring. | Keep tests as coverage, not deployment evidence. | 1 | 5 |
| tests/test_microstructure_ofi.py | ofi | unused | test | research_only | test-only reference; not runtime wiring. | Keep tests as coverage, not deployment evidence. | 16 | 20 |
| tests/test_microstructure_ofi.py | requires_resync | column_reference | test | research_only | test-only reference; not runtime wiring. | Keep tests as coverage, not deployment evidence. | 2 | 24 |
| tests/test_ofi_downstream_consumer_audit.py | OFI | unused | test | research_only | test-only reference; not runtime wiring. | Keep tests as coverage, not deployment evidence. | 3 | 20 |
| tests/test_ofi_downstream_consumer_audit.py | join_ofi_to_bars_preserve_coverage | unused | test | research_only | test-only reference; not runtime wiring. | Keep tests as coverage, not deployment evidence. | 6 | 16 |
| tests/test_ofi_downstream_consumer_audit.py | microstructure_ofi | unused | test | research_only | test-only reference; not runtime wiring. | Keep tests as coverage, not deployment evidence. | 3 | 15 |
| tests/test_ofi_downstream_consumer_audit.py | ofi | unused | test | research_only | test-only reference; not runtime wiring. | Keep tests as coverage, not deployment evidence. | 2 | 37 |
| tests/test_ofi_downstream_consumer_audit.py | volume_delta | unused | test | research_only | test-only reference; not runtime wiring. | Keep tests as coverage, not deployment evidence. | 2 | 20 |
| tests/test_regime_classifier_canonical.py | volume_delta | column_reference | test | research_only | test-only reference; not runtime wiring. | Keep tests as coverage, not deployment evidence. | 1 | 37 |
| tests/test_run_c_exhaustion_paper_sim_cli.py | volume_delta | column_reference | test | research_only | test-only reference; not runtime wiring. | Keep tests as coverage, not deployment evidence. | 1 | 43 |
| tests/test_run_c_exhaustion_replay_cli.py | volume_delta | column_reference | test | research_only | test-only reference; not runtime wiring. | Keep tests as coverage, not deployment evidence. | 1 | 41 |
| tests/test_v92_branch_b_scope.py | OFI | unused | test | research_only | test-only reference; not runtime wiring. | Keep tests as coverage, not deployment evidence. | 2 | 13 |
| tests/test_v92_branch_b_scope.py | volume_delta | column_reference | test | research_only | test-only reference; not runtime wiring. | Keep tests as coverage, not deployment evidence. | 8 | 23 |
| tests/test_v92_data_policy.py | join_ofi_to_bars_preserve_coverage | unused | test | research_only | test-only reference; not runtime wiring. | Keep tests as coverage, not deployment evidence. | 3 | 10 |
| tests/test_v92_data_policy.py | ofi | unused | test | research_only | test-only reference; not runtime wiring. | Keep tests as coverage, not deployment evidence. | 3 | 112 |
| tests/test_v92_data_policy.py | volume_delta | column_reference | test | research_only | test-only reference; not runtime wiring. | Keep tests as coverage, not deployment evidence. | 2 | 109 |
| tests/test_v92_tier2_cache_builder.py | volume_delta | column_reference | test | research_only | test-only reference; not runtime wiring. | Keep tests as coverage, not deployment evidence. | 3 | 45 |

## Replay / Strategy Usage

The audit found OFI references in these replay/strategy-adjacent files:
- `scripts/v92_alpha_strategy_test.py`

These references are research-only or not wired, not production-approved replay paths.

## Data Policy Usage

| path | symbol_or_function | reference_type | status | risk | required_action |
| --- | --- | --- | --- | --- | --- |
| features/v92_data_policy.py | OFI | unused | research_only | OFI-related reference is not a production consumer. | Keep it research-only until explicit wiring and provenance validation exist. |
| features/v92_data_policy.py | join_ofi_to_bars_preserve_coverage | function_call | safe | bar coverage preserved; no rows dropped. | Keep as the canonical join helper. |
| features/v92_data_policy.py | ofi | unused | research_only | OFI-related reference is not a production consumer. | Keep it research-only until explicit wiring and provenance validation exist. |

`join_ofi_to_bars_preserve_coverage` is the positive data-policy reference: it preserves bar count and is the canonical OFI join helper.

## Resync Handling Risk

The repaired engine exposes `requires_resync`, but no downstream replay/strategy path was found to consume it directly.
A downstream integration must propagate resync state before live use.

## Null / Coverage Risk

Some research scripts and feature consumers treat OFI as a dense series. That is acceptable for read-only diagnostics, but not proof of production readiness.

## Documentation Drift

Stale or overly aspirational documentation references were found:
- `README.md` (OFI)
- `README.md` (microstructure_ofi)
- `README.md` (order_flow_imbalance)
- `docs/v92_STRATEGY_IDEATION.md` (OFI)
- `docs/v92_STRATEGY_IDEATION.md` (order_flow_imbalance)
- `docs/v92_STRATEGY_IDEATION.md` (volume_delta)
- `docs/v92_STRATEGY_MEMORY_LEDGER.md` (OFI)
- `docs/v92_STRATEGY_MEMORY_LEDGER.md` (book imbalance)
- `docs/v92_STRATEGY_MEMORY_LEDGER.md` (mlofi)

These docs should be treated as historical or aspirational, not as approval to deploy OFI.

## What Is Safe

- `features/v92_data_policy.py::join_ofi_to_bars_preserve_coverage` preserves bar coverage.
- Test-only and research-only OFI references are acceptable for validation work.
- The repaired engine itself is warmup-safe and bounded.

## What Is Not Safe

- Treating OFI as production-approved.
- Using OFI without downstream provenance and sequence-gap validation.
- Assuming research diagnostics imply live/paper readiness.

## Required Next Step

Run a read-only provenance and coverage audit on the historical OFI/volume-delta sources that feed the research scripts, then validate any actual downstream consumer wiring before considering broader use.

## Audit Notes

- reference_count: `75`
- file_count: `40`
- status_counts: `{'stale': 9, 'research_only': 50, 'safe': 1, 'not_wired': 4, 'requires_provenance_validation': 4, 'requires_resync_handling': 7}`
- consumer_counts: `{'documentation': 22, 'feature_builder': 16, 'data_policy': 3, 'research_script': 15, 'test': 19}`