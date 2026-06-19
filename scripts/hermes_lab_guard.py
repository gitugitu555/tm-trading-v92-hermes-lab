#!/usr/bin/env python3
"""Fail fast when Hermes/Vega code runs in the wrong repo or remote state."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

EXPECTED_REPO_ROOT = Path("/home/tokio/tm-trading-v92-hermes-lab")
EXPECTED_ORIGIN = "https://github.com/gitugitu555/tm-trading-v92-hermes-lab.git"
EXPECTED_UPSTREAM = "https://github.com/gitugitu555/tm-trading-v92-core.git"
SUSPICIOUS_FILES = (
    Path(".github/workflows/manifest-check.yml"),
    Path("scripts/verify_run_manifest.py"),
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--allow-any-root", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def _run_git(args: list[str], cwd: Path) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def _current_branch(cwd: Path) -> str:
    return _run_git(["branch", "--show-current"], cwd)


def _remote_url(cwd: Path, remote: str) -> str:
    return _run_git(["remote", "get-url", remote], cwd)


def _status_porcelain(cwd: Path) -> str:
    return _run_git(["status", "--short"], cwd)


def _repo_root(cwd: Path) -> Path | None:
    resolved = cwd.resolve()
    top_level = _run_git(["rev-parse", "--show-toplevel"], resolved)
    if not top_level:
        return None
    return Path(top_level).resolve()


def _suspicious_files(root: Path) -> list[str]:
    present = []
    for rel_path in SUSPICIOUS_FILES:
        if (root / rel_path).exists():
            present.append(str(rel_path))
    return present


def evaluate_guard(cwd: Path | None = None, allow_dirty: bool = False, allow_any_root: bool = False) -> dict[str, object]:
    cwd = (cwd or Path.cwd()).resolve()
    failures: list[str] = []

    repo_root = _repo_root(cwd)
    if repo_root is None:
        failures.append("not a git repository")
        repo_root_value = str(cwd)
    else:
        repo_root_value = str(repo_root)
        if not allow_any_root and repo_root != EXPECTED_REPO_ROOT:
            failures.append(f"repo root mismatch: expected {EXPECTED_REPO_ROOT}, found {repo_root}")
        if not allow_any_root and cwd != EXPECTED_REPO_ROOT:
            failures.append(f"current working directory mismatch: expected {EXPECTED_REPO_ROOT}, found {cwd}")

    branch = _current_branch(cwd)
    if not branch:
        failures.append("detached HEAD or unable to determine branch")

    origin_url = _remote_url(cwd, "origin")
    if not origin_url:
        failures.append("missing origin remote")
    elif origin_url != EXPECTED_ORIGIN:
        failures.append(f"origin remote mismatch: expected {EXPECTED_ORIGIN}, found {origin_url}")

    upstream_url = _remote_url(cwd, "upstream")
    if not upstream_url:
        failures.append("missing upstream remote")
    elif upstream_url != EXPECTED_UPSTREAM:
        failures.append(f"upstream remote mismatch: expected {EXPECTED_UPSTREAM}, found {upstream_url}")

    dirty = bool(_status_porcelain(cwd))
    if dirty and not allow_dirty:
        failures.append("git status is dirty")

    suspicious_files_present = _suspicious_files(repo_root or cwd)
    if suspicious_files_present:
        failures.append("suspicious files present: " + ", ".join(suspicious_files_present))

    ok = not failures
    return {
        "ok": ok,
        "repo_root": repo_root_value,
        "branch": branch,
        "origin_url": origin_url,
        "upstream_url": upstream_url,
        "dirty": dirty,
        "suspicious_files_present": suspicious_files_present,
        "failures": failures,
    }


def _print_text(result: dict[str, object]) -> None:
    status = "PASS" if result["ok"] else "FAIL"
    print(f"[{status}] hermes_lab_guard")
    print(f"repo_root: {result['repo_root']}")
    print(f"branch: {result['branch'] or 'detached'}")
    print(f"origin: {result['origin_url'] or 'missing'}")
    print(f"upstream: {result['upstream_url'] or 'missing'}")
    print(f"dirty: {str(result['dirty']).lower()}")
    print(f"suspicious_files_present: {', '.join(result['suspicious_files_present']) if result['suspicious_files_present'] else 'none'}")
    if result["failures"]:
        print("failures:")
        for failure in result["failures"]:
            print(f"- {failure}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = evaluate_guard(allow_dirty=args.allow_dirty, allow_any_root=args.allow_any_root)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        _print_text(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
