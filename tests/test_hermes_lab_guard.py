from __future__ import annotations

from pathlib import Path

import scripts.hermes_lab_guard as guard


def _mock_guard(monkeypatch, tmp_path, origin: str, upstream: str, status: str = "", branch: str = "feature/test", suspicious: bool = False):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(guard, "_repo_root", lambda cwd: tmp_path)
    monkeypatch.setattr(guard, "_current_branch", lambda cwd: branch)
    monkeypatch.setattr(guard, "_remote_url", lambda cwd, remote: origin if remote == "origin" else upstream)
    monkeypatch.setattr(guard, "_status_porcelain", lambda cwd: status)
    monkeypatch.setattr(guard, "_suspicious_files", lambda root: ["scripts/verify_run_manifest.py"] if suspicious else [])


def test_guard_passes_with_correct_mocked_remotes(monkeypatch, tmp_path):
    _mock_guard(
        monkeypatch,
        tmp_path,
        guard.EXPECTED_ORIGIN,
        guard.EXPECTED_UPSTREAM,
        status="",
    )
    result = guard.evaluate_guard(cwd=tmp_path, allow_dirty=False, allow_any_root=True)
    assert result["ok"] is True
    assert result["failures"] == []


def test_guard_fails_if_origin_points_to_core(monkeypatch, tmp_path):
    _mock_guard(
        monkeypatch,
        tmp_path,
        guard.EXPECTED_UPSTREAM,
        guard.EXPECTED_UPSTREAM,
    )
    result = guard.evaluate_guard(cwd=tmp_path, allow_dirty=False, allow_any_root=True)
    assert result["ok"] is False
    assert any("origin remote mismatch" in item for item in result["failures"])


def test_guard_fails_if_upstream_missing(monkeypatch, tmp_path):
    _mock_guard(
        monkeypatch,
        tmp_path,
        guard.EXPECTED_ORIGIN,
        "",
    )
    result = guard.evaluate_guard(cwd=tmp_path, allow_dirty=False, allow_any_root=True)
    assert result["ok"] is False
    assert any("missing upstream remote" in item for item in result["failures"])


def test_guard_fails_if_suspicious_files_present(monkeypatch, tmp_path):
    _mock_guard(
        monkeypatch,
        tmp_path,
        guard.EXPECTED_ORIGIN,
        guard.EXPECTED_UPSTREAM,
        suspicious=True,
    )
    result = guard.evaluate_guard(cwd=tmp_path, allow_dirty=False, allow_any_root=True)
    assert result["ok"] is False
    assert result["suspicious_files_present"] == ["scripts/verify_run_manifest.py"]


def test_guard_fails_if_dirty_and_allow_dirty_false(monkeypatch, tmp_path):
    _mock_guard(
        monkeypatch,
        tmp_path,
        guard.EXPECTED_ORIGIN,
        guard.EXPECTED_UPSTREAM,
        status=" M docs/example.md",
    )
    result = guard.evaluate_guard(cwd=tmp_path, allow_dirty=False, allow_any_root=True)
    assert result["ok"] is False
    assert any("git status is dirty" in item for item in result["failures"])


def test_guard_passes_dirty_only_when_allow_dirty_true(monkeypatch, tmp_path):
    _mock_guard(
        monkeypatch,
        tmp_path,
        guard.EXPECTED_ORIGIN,
        guard.EXPECTED_UPSTREAM,
        status=" M docs/example.md",
    )
    result = guard.evaluate_guard(cwd=tmp_path, allow_dirty=True, allow_any_root=True)
    assert result["ok"] is True


def test_guard_json_output_contains_expected_keys(monkeypatch, tmp_path, capsys):
    _mock_guard(
        monkeypatch,
        tmp_path,
        guard.EXPECTED_ORIGIN,
        guard.EXPECTED_UPSTREAM,
    )
    exit_code = guard.main(["--allow-any-root", "--json"])
    assert exit_code == 0
    payload = capsys.readouterr().out
    assert '"ok": true' in payload
    for key in ["repo_root", "branch", "origin_url", "upstream_url", "dirty", "suspicious_files_present", "failures"]:
        assert f'"{key}"' in payload
