# Hermes Agent Operating Rules

The lab repo is active: `/home/tokio/tm-trading-v92-hermes-lab`.

The core repo is checkpoint-only: `/home/tokio/tm-trading-v92-core`.

Rules:

- Agents may only push to the lab `origin`.
- Agents must never push to `upstream`.
- Do not push to upstream.
- No force-push.
- No history rewrite.
- No branch protection changes.
- No workflow changes.
- No secrets committed.
- No automatic promotion to core.
- Every task starts with `scripts/hermes_lab_guard.py`.
- Every task ends with a run report under `reports/hermes_runs/`.
- Any council-triggered task creates a report under `reports/hermes_council/`.
- Vega can orchestrate but cannot bypass the guard.
- Vega must stop implementation and call council when repeated failures, ambiguity, forbidden-file risk, suspicious files, or unsafe strategy direction appear.
- Worker CLIs are stateless and must receive self-contained prompts.
- All task prompts must include allowed files and forbidden files.
- Any promotion back to core requires explicit human approval and separate review.

Council mode rules:

- Council mode only. Do not edit files. Do not commit. Do not push.
- No alpha approval, paper/live approval, new trading rule approval, or threshold tuning without preregistration.
- Council output is a report only.
- Council prompts must include the repo boundary, allowed files, forbidden files, current failure reason, and a no-secrets warning.

Boundary reminders:

- `origin` must point to `gitugitu555/tm-trading-v92-hermes-lab`.
- `upstream` must point to `gitugitu555/tm-trading-v92-core`.
- `upstream` is read-only for this lab.
