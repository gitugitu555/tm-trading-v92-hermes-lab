# Hermes Task Template

If any requested action conflicts with `repo_policy`, stop and report.

```text
task_id:
title:
status: pending
created_at:
assigned_agent:
branch_name:
objective:
context:
allowed_files:
forbidden_files:
input_paths:
output_paths:
validation_commands:
failed_attempt_count: 0
last_failure_reason:
council_after_failed_attempts: 2
council_required: false
council_decision_required_before_continue: false
council_triggers:
- repeated_test_failure
- ambiguous_result
- forbidden_file_risk
- strategy_uncertainty
- inconclusive_metrics
- human_requested
commit_allowed: false
push_allowed: false
push_remote: origin
upstream_allowed: false
force_push_allowed: false
workflow_changes_allowed: false
branch_protection_changes_allowed: false
secrets_allowed: false
decision_labels:
stop_conditions:
final_report_required:
```
