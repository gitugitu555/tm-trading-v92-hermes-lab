# Hermes AI Council Meeting Protocol

The AI Council Meeting is a report-only stop condition for ambiguous, repeatedly failing, or unsafe tasks.

Vega must create a council report when any of these occur:

- `failed_attempt_count >= council_after_failed_attempts`
- The same test fails twice after attempted fixes.
- Full pytest fails after a task claimed success.
- A task becomes ambiguous.
- A requested change would touch forbidden files.
- Output metrics are inconclusive.
- A result improves win rate but worsens expectancy or payoff.
- An agent proposes threshold tuning without preregistration.
- An agent proposes strategy, replay, or OFI changes outside allowed files.
- An agent tries to push to upstream.
- Git status includes unexpected files.
- Suspicious Gemini files appear.
- The user explicitly requests council, review, or meeting.
- Vega cannot choose a safe next action.

Council mode hard rules:

- Council mode only. Do not edit files. Do not commit. Do not push.
- No branch protection changes.
- No workflow changes.
- No force-push.
- No history rewrite.
- No upstream or core writes.
- No alpha approval.
- No paper or live approval.
- No new trading rule approval.
- No threshold tuning unless explicitly preregistered.
- Council output is a report only.

Council roles:

- Vega / Hermes orchestrator chairs the meeting, summarizes task state, synthesizes recommendations, and produces the final decision.
- `opencode_deepseek_flash` gives the implementation perspective and suggests minimal safe patch options.
- `kilo_nex2_review` gives the review perspective and challenges bugs, leakage, unsafe file changes, and bad assumptions.
- `vibe_strategy` gives the strategy perspective and flags overfitting, win-rate traps, weak hypotheses, and unclear direction.
- `zcode_glm52_research` gives the research perspective and compares the task to prior docs and decisions.

Decision labels:

- `council_continue_current_task`
- `council_retry_with_minimal_patch`
- `council_stop_failed_task`
- `council_rewrite_task_scope`
- `council_create_new_preregistration`
- `council_request_human_decision`
- `council_retire_hypothesis`
- `council_park_until_more_data`

Default usage:

```bash
python scripts/hermes_task_runner.py \
  --task-id TASK-001-nonparametric-diagnostic \
  --force-council \
  --trigger-reason human_requested
```
