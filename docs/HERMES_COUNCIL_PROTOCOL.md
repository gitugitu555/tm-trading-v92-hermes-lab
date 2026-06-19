# Hermes AI Council Meeting Protocol

The AI Council Meeting is a report-only stop condition for ambiguous, repeatedly failing, unsafe, or strategically unclear work.

## What Council Mode Is

Council mode is a structured review meeting where Vega stops implementation, gathers role-specific briefs, and writes a report. It is not a patching workflow.

## Why Vega Calls Council

Vega calls council when continuing with normal implementation is no longer safe or informative. The goal is to avoid blind retries, unsafe scope drift, and false confidence.

## Trigger Conditions

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

## Council Roles

- Vega / Hermes orchestrator: chairs the meeting, summarizes task state, synthesizes recommendations, and produces the final decision.
- `opencode_deepseek_flash`: implementation perspective, code-level blockers, and minimal safe patch options.
- `kilo_nex2_review`: review perspective, bug hunting, unsafe file change detection, and assumption checking.
- `vibe_strategy`: strategy perspective, overfitting detection, win-rate trap detection, and direction checks.
- `zcode_glm52_research`: research perspective, cross-document comparison, and historical constraint checking.

## What Each Role Contributes

- Vega turns the separate briefs into one decision label and a next-action recommendation.
- `opencode_deepseek_flash` explains what can be changed safely, and what should be left alone.
- `kilo_nex2_review` checks for correctness regressions, leakage, and unintended surface area.
- `vibe_strategy` checks whether the task still makes strategic sense or should be reframed.
- `zcode_glm52_research` checks whether prior docs, preregistrations, or earlier decisions already answered the question.

## Distinction Between Work Types

- Implementation task: a normal edit-and-validate task that may continue while safe.
- Review task: a read-only inspection of code, diffs, tests, or reports.
- Strategy discussion: a higher-level discussion about whether the work should proceed, be reframed, or be retired.
- Council meeting: a report-only meeting that collects all relevant viewpoints and stops implementation until a decision is written down.
- Promotion decision: a separate human or orchestrator decision to move a validated result toward a higher-trust branch, repo, or release path.

## Council Hard Rules

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
- Human review is required before any promotion decision.

## Report Format

Council reports must include:

- Meeting metadata
- Task state summary
- Agent briefs
- Disagreement matrix
- Decision options
- Vega final synthesis

## Decision Labels

- `council_continue_current_task`
- `council_retry_with_minimal_patch`
- `council_stop_failed_task`
- `council_rewrite_task_scope`
- `council_create_new_preregistration`
- `council_request_human_decision`
- `council_retire_hypothesis`
- `council_park_until_more_data`

## Human Review Requirement

Council output is not an approval. If the council reaches a conclusion that would change scope, approve a promotion, or change a trading assumption, a human must review the report before the next step.

## Default Usage

```bash
python scripts/hermes_task_runner.py \
  --task-id TASK-001-nonparametric-diagnostic \
  --force-council \
  --trigger-reason human_requested
```
