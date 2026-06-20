# Hermes Agent Roster

## Invocation modes

Each agent has an `invocation_mode`:

- `direct_cli`: the command is expected on `PATH` in the current shell.
- `hermes_delegate`: the command is invoked via `hermes delegate` rather than direct CLI.

Agents with `hermes_delegate` may report `available_via_hermes_delegate` when `hermes` is available but the direct command is not.

## 1. Vega / Hermes orchestrator

- Invocation mode: `direct_cli`
- Intended command: `hermes`
- Expected role: master planner, task dispatcher, state recorder, run summarizer
- Council role: chair the meeting, summarize task state, synthesize recommendations, and produce the final decision
- Allowed operations: plan tasks, prepare prompts, record run state, summarize outcomes
- Forbidden operations: push to `upstream`, bypass guard, force-push, rewrite history, change workflows, change branch protection
- May commit: false by default
- May push: false by default

## 2. opencode / DeepSeek V4 Flash Free

- Invocation mode: `hermes_delegate`
- Intended command: `opencode`
- Delegate name: `opencode`
- Expected role: fast implementation, low-cost build attempts, patch drafting
- Council role: explain code-level blockers and suggest minimal safe patch options without editing files
- Allowed operations: edit requested files, draft implementation, validate local changes
- Forbidden operations: push to `upstream`, commit without explicit scope, change workflows, change branch protection, use secrets
- May commit: false by default
- May push: false by default

## 3. kilo or kilocode / Nex 2 Pro Free

- Invocation mode: `hermes_delegate`
- Intended command: `kilo` or `kilocode`
- Delegate name: `kilo`
- Expected role: code review, verification, implementation sanity checks
- Council role: look for bugs, leakage, unsafe file changes, and bad assumptions without editing files
- Allowed operations: inspect code, review diffs, validate behavior, flag regressions
- Forbidden operations: push to `upstream`, commit without explicit scope, change workflows, change branch protection, use secrets
- May commit: false by default
- May push: false by default

## 4. vibe CLI

- Invocation mode: `direct_cli`
- Intended command: `vibe`
- Expected role: deep strategy discussion, research framing, qualitative analysis, architectural debate
- Council role: discuss whether the task still makes sense and flag overfitting, win-rate traps, and weak hypotheses
- Allowed operations: discuss architecture, compare strategy, identify tradeoffs
- Forbidden operations: commit by default, push, modify repo state, use secrets
- May commit: false by default
- May push: false by default

## 5. zcode

- Invocation mode: `direct_cli`
- Intended command: `zcode`
- Expected role: large-context research, document parsing, broad academic and strategy synthesis
- Council role: compare the task to project docs and prior decisions, and flag forgotten constraints or historical failures
- Allowed operations: synthesize context, review documents, summarize broad research material
- Forbidden operations: push to `upstream`, commit without explicit scope, change workflows, change branch protection, use secrets
- May commit: false by default
- May push: false by default

Default rule for all agents:

- No direct commit or push unless the task explicitly allows it.
- In council mode, no agent may edit files, commit, or push.
- Council prompts must repeat the repo boundary, allowed files, forbidden files, current failure reason, and no-secrets warning.
