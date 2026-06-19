from __future__ import annotations

from pathlib import Path

import pytest

import scripts.hermes_task_runner as runner
from scripts.hermes_invoke_agent import TaskContext


def test_parses_task_001_from_queue():
    task = runner._load_task("TASK-001-nonparametric-diagnostic")
    assert task is not None
    assert task.task_id == "TASK-001-nonparametric-diagnostic"
    assert task.status == "pending"
    assert task.branch_name == "research/nonparametric-failure-attribution-diagnostic-lab"


def test_run_report_path_is_under_reports_hermes_runs(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    runner.RUN_REPORT_DIR = tmp_path / "reports" / "hermes_runs"
    report = runner.RunReport(
        timestamp="2026-06-19T00:00:00+00:00",
        repo_root=str(tmp_path),
        branch="feature/test",
        remotes={"origin": "https://example.com/origin.git", "upstream": "https://example.com/upstream.git"},
        task={
            "task_id": "TASK-001",
            "title": "Title",
            "status": "pending",
            "branch_name": "branch",
            "objective": "Objective",
        },
        failed_attempt_count=0,
        last_failure_reason="",
        council_after_failed_attempts=2,
        council_required=False,
        council_decision_required_before_continue=False,
        assigned_agents=["vega_orchestrator"],
        allowed_files=["a.py"],
        forbidden_files=["b.py"],
        validation_commands=["pytest"],
        guard_result={"ok": True},
        branch_matches_task=False,
        branch_warning="branch mismatch: expected branch, found feature/test",
        dry_run_prompt="prompt",
        next_steps=["next"],
    )
    path = runner._write_report("TASK-001", report)
    assert str(path).startswith(str(tmp_path / "reports" / "hermes_runs"))


def test_dry_run_does_not_commit_or_push(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(runner, "_load_task", lambda task_id: TaskContext(
        task_id="TASK-001",
        title="Title",
        status="pending",
        branch_name="research/nonparametric-failure-attribution-diagnostic-lab",
        objective="Objective",
        context="Context",
        allowed_files=["scripts/example.py"],
        forbidden_files=["upstream/**"],
        validation_commands=["pytest -q"],
    ))
    monkeypatch.setattr(runner, "evaluate_guard", lambda allow_dirty, allow_any_root: {
        "ok": True,
        "repo_root": str(tmp_path),
        "branch": "research/nonparametric-failure-attribution-diagnostic-lab",
        "origin_url": "origin",
        "upstream_url": "upstream",
        "dirty": False,
        "suspicious_files_present": [],
        "failures": [],
    })
    monkeypatch.setattr(runner, "_remote_map", lambda: {"origin": "origin", "upstream": "upstream"})
    commit_push_called = []

    def forbidden(*args, **kwargs):
        commit_push_called.append((args, kwargs))
        raise AssertionError("commit/push should not be called")

    monkeypatch.setattr(runner, "_write_report", lambda task_id, report: tmp_path / "reports" / "hermes_runs" / f"{task_id}.md")
    monkeypatch.setattr(runner, "build_prompt", lambda agent, task: "prompt includes upstream as forbidden only")
    monkeypatch.setattr(runner, "ALLOWED_AGENTS", runner.ALLOWED_AGENTS)
    monkeypatch.setattr(runner, "Path", Path)
    runner.main(["--task-id", "TASK-001", "--json"])
    assert commit_push_called == []
    output = capsys.readouterr().out
    assert '"dry_run": true' in output


def test_failed_attempt_count_below_threshold_continues_normal_dry_run(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(runner, "_load_task", lambda task_id: TaskContext(
        task_id="TASK-001",
        title="Title",
        status="pending",
        branch_name="feature/test",
        objective="Objective",
        context="Context",
        allowed_files=["scripts/example.py"],
        forbidden_files=["upstream/**"],
        validation_commands=["pytest -q"],
        failed_attempt_count=1,
        council_after_failed_attempts=2,
    ))
    monkeypatch.setattr(runner, "evaluate_guard", lambda allow_dirty, allow_any_root: {
        "ok": True,
        "repo_root": str(tmp_path),
        "branch": "feature/test",
        "origin_url": "origin",
        "upstream_url": "upstream",
        "dirty": False,
        "suspicious_files_present": [],
        "failures": [],
    })
    monkeypatch.setattr(runner, "_remote_map", lambda: {"origin": "origin", "upstream": "upstream"})
    monkeypatch.setattr(runner, "_write_report", lambda task_id, report: tmp_path / "reports" / "hermes_runs" / f"{task_id}.md")
    runner.main(["--task-id", "TASK-001", "--json"])
    output = capsys.readouterr().out
    assert '"council_triggered"' not in output
    assert '"dry_run": true' in output


def test_failed_attempt_count_at_threshold_triggers_council(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(runner, "_load_task", lambda task_id: TaskContext(
        task_id="TASK-001",
        title="Title",
        status="pending",
        branch_name="feature/test",
        objective="Objective",
        context="Context",
        allowed_files=[],
        forbidden_files=[],
        validation_commands=[],
        failed_attempt_count=2,
        council_after_failed_attempts=2,
    ))
    monkeypatch.setattr(runner, "run_council", lambda **kwargs: {
        "ok": True,
        "report_path": "reports/hermes_council/TASK-001_council.md",
        "guard_result": {"branch": "feature/test"},
    })
    runner.main(["--task-id", "TASK-001", "--json"])
    assert '"council_triggered": true' in capsys.readouterr().out


def test_force_council_triggers_council(monkeypatch, capsys):
    monkeypatch.setattr(runner, "_load_task", lambda task_id: TaskContext(
        task_id="TASK-001",
        title="Title",
        status="pending",
        branch_name="feature/test",
        objective="Objective",
        context="Context",
        allowed_files=[],
        forbidden_files=[],
        validation_commands=[],
    ))
    monkeypatch.setattr(runner, "run_council", lambda **kwargs: {
        "ok": True,
        "report_path": "reports/hermes_council/TASK-001_council.md",
        "guard_result": {"branch": "feature/test"},
    })
    runner.main(["--task-id", "TASK-001", "--force-council", "--trigger-reason", "human_requested", "--json"])
    output = capsys.readouterr().out
    assert '"council_triggered": true' in output
    assert "reports/hermes_council/TASK-001_council.md" in output


def test_council_required_true_triggers_council(monkeypatch, capsys):
    monkeypatch.setattr(runner, "_load_task", lambda task_id: TaskContext(
        task_id="TASK-001",
        title="Title",
        status="pending",
        branch_name="feature/test",
        objective="Objective",
        context="Context",
        allowed_files=[],
        forbidden_files=[],
        validation_commands=[],
        council_required=True,
    ))
    monkeypatch.setattr(runner, "run_council", lambda **kwargs: {
        "ok": True,
        "report_path": "reports/hermes_council/TASK-001_council.md",
        "guard_result": {"branch": "feature/test"},
    })
    runner.main(["--task-id", "TASK-001", "--json"])
    assert '"council_triggered": true' in capsys.readouterr().out


def test_branch_mismatch_remains_warning_field_in_dry_run(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(runner, "_load_task", lambda task_id: TaskContext(
        task_id="TASK-001",
        title="Title",
        status="pending",
        branch_name="expected/task",
        objective="Objective",
        context="Context",
        allowed_files=[],
        forbidden_files=[],
        validation_commands=[],
    ))
    monkeypatch.setattr(runner, "evaluate_guard", lambda allow_dirty, allow_any_root: {
        "ok": True,
        "repo_root": str(tmp_path),
        "branch": "actual/infra",
        "origin_url": "origin",
        "upstream_url": "upstream",
        "dirty": False,
        "suspicious_files_present": [],
        "failures": [],
    })
    monkeypatch.setattr(runner, "_remote_map", lambda: {"origin": "origin", "upstream": "upstream"})
    monkeypatch.setattr(runner, "_write_report", lambda task_id, report: tmp_path / "report.md")
    runner.main(["--task-id", "TASK-001", "--json"])
    output = capsys.readouterr().out
    assert '"branch_matches_task": false' in output
    assert '"branch_warning": "branch mismatch: expected expected/task, found actual/infra"' in output


def test_generated_prompt_includes_repo_boundary(monkeypatch):
    task = TaskContext(
        task_id="TASK-001",
        title="Title",
        status="pending",
        branch_name="research/nonparametric-failure-attribution-diagnostic-lab",
        objective="Objective",
        context="Context",
        allowed_files=["scripts/example.py"],
        forbidden_files=["upstream/**"],
        validation_commands=["pytest -q"],
    )
    prompt = runner.build_prompt("vega_orchestrator", task)
    assert "/home/tokio/tm-trading-v92-hermes-lab" in prompt
    assert "/home/tokio/tm-trading-v92-core" in prompt


def test_generated_prompt_includes_allowed_and_forbidden_files():
    task = TaskContext(
        task_id="TASK-001",
        title="Title",
        status="pending",
        branch_name="research/nonparametric-failure-attribution-diagnostic-lab",
        objective="Objective",
        context="Context",
        allowed_files=["scripts/example.py"],
        forbidden_files=["upstream/**"],
        validation_commands=["pytest -q"],
    )
    prompt = runner.build_prompt("opencode_deepseek_flash", task)
    assert "Allowed files:" in prompt
    assert "scripts/example.py" in prompt
    assert "Forbidden files:" in prompt
    assert "upstream/**" in prompt


def test_rejects_unknown_agent():
    with pytest.raises(SystemExit):
        runner.main(["--agent", "unknown", "--task-id", "TASK-001"])


def test_never_references_push_to_upstream_as_allowed_action():
    task = TaskContext(
        task_id="TASK-001",
        title="Title",
        status="pending",
        branch_name="research/nonparametric-failure-attribution-diagnostic-lab",
        objective="Objective",
        context="Context",
        allowed_files=["scripts/example.py"],
        forbidden_files=["upstream/**"],
        validation_commands=["pytest -q"],
    )
    prompt = runner.build_prompt("vibe_strategy", task)
    assert "Push remote: origin only" in prompt
    assert "Forbidden remote: upstream" in prompt
    assert "upstream" not in prompt.split("Allowed files:")[0].split("Forbidden remote: upstream")[0]
