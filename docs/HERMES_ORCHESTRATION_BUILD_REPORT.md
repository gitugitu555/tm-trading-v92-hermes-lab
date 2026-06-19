# Hermes Orchestration Build Report

Build decision label: `hermes_orchestration_scaffold_lab_only`

## Files Added

- `docs/HERMES_AGENT_OPERATING_RULES.md`
- `docs/HERMES_AGENT_ROSTER.md`
- `docs/HERMES_TASK_TEMPLATE.md`
- `docs/HERMES_TASK_QUEUE.md`
- `docs/HERMES_ORCHESTRATION_BUILD_REPORT.md`
- `config/hermes_agents.example.yaml`
- `scripts/hermes_lab_guard.py`
- `scripts/hermes_agent_check.py`
- `scripts/hermes_task_runner.py`
- `scripts/hermes_invoke_agent.py`
- `tests/test_hermes_lab_guard.py`
- `tests/test_hermes_agent_check.py`
- `tests/test_hermes_task_runner.py`
- `reports/hermes_runs/.gitkeep`
- `reports/hermes_runs/TASK-001-nonparametric-diagnostic.md`

## Command Inventory

Observed from `scripts/hermes_agent_check.py`:

| command | available | path | version |
| --- | --- | --- | --- |
| hermes | true | `/home/tokio/.local/bin/hermes` | `Hermes Agent v0.16.0 (2026.6.5) · upstream 28d887ca` |
| opencode | false |  |  |
| kilo | false |  |  |
| kilocode | false |  |  |
| vibe | true | `/home/tokio/.local/bin/vibe` | `vibe 2.16.1` |
| zcode | true | `/usr/bin/zcode` |  |
| gh | true | `/usr/bin/gh` | `gh version 2.46.0 (2025-01-13 Debian 2.46.0-3)` |
| git | true | `/usr/bin/git` | `git version 2.47.3` |
| python3 | true | `/usr/bin/python3` | `Python 3.13.5` |
| uv | true | `/home/tokio/.local/bin/uv` | `uv 0.11.16 (x86_64-unknown-linux-gnu)` |

Unavailable commands:

- `opencode`
- `kilo`
- `kilocode`

## Guard Behavior

- `scripts/hermes_lab_guard.py` validates the repo root, remotes, branch state, dirty status, and suspicious files.
- In the current workspace, the default guard reports dirty status because the scaffold files are uncommitted.
- `scripts/hermes_lab_guard.py --allow-dirty` passes with the expected lab remotes and no suspicious files.
- Suspicious Gemini files remain absent.

## Task Runner Behavior

- `scripts/hermes_task_runner.py` reads `docs/HERMES_TASK_QUEUE.md`, selects the first pending task, runs the guard, and writes a run report under `reports/hermes_runs/`.
- The runner is conservative by default and does not commit or push.
- In this workspace, the task branch differs from the current branch, so the run report records `branch_matches_task: false` instead of forcing a branch switch.
- Dry-run output includes the repo boundary, allowed files, forbidden files, validation commands, and a self-contained worker prompt.

## AI Council Meeting Protocol

The AI Council Meeting Protocol exists so Vega does not blindly continue through repeated failures, ambiguous metrics, forbidden-file risk, or unclear strategy direction. In council mode, agents provide report-only briefs and may not edit files, commit, or push.

Trigger rules include:

- `failed_attempt_count >= council_after_failed_attempts`
- Same test fails twice after attempted fixes.
- Full pytest fails after a task claimed success.
- Task becomes ambiguous.
- Requested change would touch forbidden files.
- Output metrics are inconclusive.
- Win rate improves while expectancy or payoff worsens.
- Threshold tuning is proposed without preregistration.
- Strategy, replay, OFI, or workflow scope drift is proposed.
- User explicitly requests council, review, or meeting.
- Vega cannot choose a safe next action.

Files created for council support:

- `docs/HERMES_COUNCIL_PROTOCOL.md`
- `scripts/hermes_council_meeting.py`
- `tests/test_hermes_council_meeting.py`
- `reports/hermes_council/.gitkeep`

Dry-run council test result:

- `python scripts/hermes_task_runner.py --task-id TASK-001-nonparametric-diagnostic --force-council --trigger-reason human_requested_test_council` creates a report under `reports/hermes_council/`.
- Validation produced `reports/hermes_council/TASK-001-nonparametric-diagnostic_20260619T165129Z_council.md`.

Council safety confirmations:

- No files are edited by agents during council mode.
- No commit happens during council mode.
- No push happens during council mode.

Next usage command:

```bash
python scripts/hermes_task_runner.py \
  --task-id TASK-001-nonparametric-diagnostic \
  --force-council \
  --trigger-reason human_requested
```

## How Vega Should Use It

- Start every orchestration cycle with `scripts/hermes_lab_guard.py`.
- Use `scripts/hermes_task_runner.py` to select the next pending task and write the run report.
- Use `scripts/hermes_invoke_agent.py` to generate a self-contained prompt for a worker CLI before any execution attempt.
- Keep `origin` as the only push target.
- Treat `upstream` as read-only checkpoint state.

## How Worker CLIs Should Be Called

- `opencode`: call through a self-contained prompt for implementation work only.
- `kilo` or `kilocode`: call through a self-contained prompt for review and verification.
- `vibe`: call through a self-contained prompt for strategy discussion and qualitative analysis.
- `zcode`: call through a self-contained prompt for broad research and document synthesis.
- `hermes`: use for orchestration, state recording, and run summaries.

## Boundary and Policy Confirmation

- No changes were made to `/home/tokio/tm-trading-v92-core`.
- No workflows were created.
- No branch protection settings were changed.
- No secrets were committed.
- No force-push was used.
- No history rewrite was used.
- No pushes were made to `upstream`.
- Only lab-origin scoped orchestration files were added.

## Next Recommended Task

- Run `TASK-001-nonparametric-diagnostic` as a dry-run through `scripts/hermes_task_runner.py` after explicit human approval for any execution beyond the prompt/report phase.
