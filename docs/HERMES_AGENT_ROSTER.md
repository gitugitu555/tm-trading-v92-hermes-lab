# Hermes Agent Roster

## 1. Vega / Hermes orchestrator

- Intended command: `hermes`
- Expected role: master planner, task dispatcher, state recorder, run summarizer
- Allowed operations: plan tasks, prepare prompts, record run state, summarize outcomes
- Forbidden operations: push to `upstream`, bypass guard, force-push, rewrite history, change workflows, change branch protection
- May commit: false by default
- May push: false by default

## 2. opencode / DeepSeek V4 Flash Free

- Intended command: `opencode`
- Expected role: fast implementation, low-cost build attempts, patch drafting
- Allowed operations: edit requested files, draft implementation, validate local changes
- Forbidden operations: push to `upstream`, commit without explicit scope, change workflows, change branch protection, use secrets
- May commit: false by default
- May push: false by default

## 3. kilo or kilocode / Nex 2 Pro Free

- Intended command: `kilo` or `kilocode`
- Expected role: code review, verification, implementation sanity checks
- Allowed operations: inspect code, review diffs, validate behavior, flag regressions
- Forbidden operations: push to `upstream`, commit without explicit scope, change workflows, change branch protection, use secrets
- May commit: false by default
- May push: false by default

## 4. vibe CLI

- Intended command: `vibe`
- Expected role: deep strategy discussion, research framing, qualitative analysis, architectural debate
- Allowed operations: discuss architecture, compare strategies, identify tradeoffs
- Forbidden operations: commit by default, push, modify repo state, use secrets
- May commit: false by default
- May push: false by default

## 5. zcode

- Intended command: `zcode`
- Expected role: large-context research, document parsing, broad academic and strategy synthesis
- Allowed operations: synthesize context, review documents, summarize broad research material
- Forbidden operations: push to `upstream`, commit without explicit scope, change workflows, change branch protection, use secrets
- May commit: false by default
- May push: false by default

Default rule for all agents:

- No direct commit or push unless the task explicitly allows it.
