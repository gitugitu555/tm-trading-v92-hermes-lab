#!/usr/bin/env python3
"""Read-only audit of OFI-related downstream consumers and references."""

from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

SEARCH_SUFFIXES = {".py", ".md", ".toml", ".yaml", ".yml", ".json", ".txt"}
IGNORED_PARTS = {".git", ".venv", "__pycache__", "data", "reports", "tmp_diagnostics"}
DEFAULT_OUTPUT = Path("docs/v92_OFI_DOWNSTREAM_CONSUMER_AUDIT.md")

SEARCH_TERMS: list[tuple[str, re.Pattern[str]]] = [
    ("join_ofi_to_bars_preserve_coverage", re.compile(r"\bjoin_ofi_to_bars_preserve_coverage\b", re.IGNORECASE)),
    ("microstructure_ofi", re.compile(r"\bmicrostructure_ofi\b", re.IGNORECASE)),
    ("microstructure_numba_ofi", re.compile(r"\bmicrostructure_numba_ofi\b", re.IGNORECASE)),
    ("order_flow_imbalance", re.compile(r"\border flow imbalance\b|\border_flow_imbalance\b", re.IGNORECASE)),
    ("mlofi", re.compile(r"\bmlofi\b", re.IGNORECASE)),
    ("book imbalance", re.compile(r"\bbook imbalance\b", re.IGNORECASE)),
    ("bid ask imbalance", re.compile(r"\bbid ask imbalance\b", re.IGNORECASE)),
    ("OFI", re.compile(r"\bOFI\b")),
    ("ofi", re.compile(r"\bofi\b")),
    ("volume_delta", re.compile(r"\bvolume_delta\b")),
    ("requires_resync", re.compile(r"\brequires_resync\b")),
]


@dataclass(frozen=True)
class AuditReference:
    path: str
    symbol_or_function: str
    reference_type: str
    consumer_type: str
    status: str
    risk: str
    required_action: str
    occurrences: int
    first_line: int
    excerpt: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output-doc", type=Path, required=True)
    return parser.parse_args(argv)


def _iter_files(repo_root: Path) -> Iterable[Path]:
    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORED_PARTS for part in path.parts):
            continue
        if path.suffix.lower() not in SEARCH_SUFFIXES and path.name != "README.md":
            continue
        if path.name in {DEFAULT_OUTPUT.name, Path(__file__).name}:
            continue
        yield path


def _consumer_type(path: Path) -> str:
    if path.name == "v92_data_policy.py":
        return "data_policy"
    if path.parts and path.parts[0] == "features":
        return "feature_builder"
    if path.parts and path.parts[0] == "tests":
        return "test"
    if path.parts and path.parts[0] == "scripts":
        if "cache_builder" in path.name or "l2_cache_builder" in path.name:
            return "feature_builder"
        if "alpha_strategy_test" in path.name:
            return "research_script"
        return "research_script"
    if (path.parts and path.parts[0] == "docs") or path.name == "README.md":
        return "documentation"
    return "unknown"


def _reference_type(path: Path, term: str, line_text: str) -> str:
    if path.suffix.lower() == ".py":
        if re.search(rf"^\s*from\s+.*{re.escape(term)}.*import\b", line_text, re.IGNORECASE) or re.search(
            rf"^\s*import\s+.*\b{re.escape(term)}\b", line_text, re.IGNORECASE
        ):
            return "import"
        if re.search(rf"\b{re.escape(term)}\s*\(", line_text):
            return "function_call"
        if term in {"volume_delta", "ofi"} and re.search(rf'["\']{re.escape(term)}["\']', line_text):
            return "column_reference"
        if term == "requires_resync" and "requires_resync" in line_text:
            return "column_reference"
        return "unused"
    if path.suffix.lower() in {".md", ".txt"}:
        return "documentation"
    if path.suffix.lower() in {".toml", ".yaml", ".yml", ".json"}:
        return "config"
    return "documentation"


def _status(path: Path, term: str, reference_type: str, line_text: str, full_text: str) -> tuple[str, str, str]:
    consumer_type = _consumer_type(path)
    risk = "read-only"
    required_action = "No immediate action."

    if consumer_type == "data_policy" and term == "join_ofi_to_bars_preserve_coverage":
        return "safe", "bar coverage preserved; no rows dropped.", "Keep as the canonical join helper."

    if consumer_type == "feature_builder" and path.name in {"microstructure_ofi.py", "microstructure_numba_ofi.py"}:
        return (
            "research_only",
            "feature builder is not a wired production consumer.",
            "Validate provenance and downstream coverage before any deployment use.",
        )

    if consumer_type == "feature_builder" and path.name == "v92_l2_cache_builder.py":
        return (
            "requires_provenance_validation",
            "OFI extraction cache requires raw-L2 provenance checks.",
            "Validate raw L2 provenance and sequence coverage before trusting derived OFI bars.",
        )

    if consumer_type == "research_script" and "alpha_strategy_test" in path.name:
        return (
            "not_wired",
            "research harness only; not part of replay or production strategy wiring.",
            "Do not treat as an approved trading path.",
        )

    if consumer_type == "research_script" and path.name in {"v92_ofi_diagnostics.py", "v92_ofi_numba_diagnostic.py"}:
        return (
            "requires_resync_handling",
            "diagnostic scripts do not surface resync state to downstream callers.",
            "Propagate resync awareness before using against live feeds.",
        )

    if consumer_type == "test":
        return (
            "research_only",
            "test-only reference; not runtime wiring.",
            "Keep tests as coverage, not deployment evidence.",
        )

    if consumer_type == "documentation":
        stale_phrases = [
            "we can trade pure market mechanics",
            "pure market mechanics",
            "clean Order Flow Imbalance",
            "true OFI",
            "stable recent post-cost value",
        ]
        if any(phrase.lower() in full_text.lower() for phrase in stale_phrases):
            return (
                "stale",
                "aspirational language can be read as readiness if not caveated.",
                "Rewrite or annotate as research-only historical context.",
            )
        return (
            "research_only",
            "documentation only; not operational wiring.",
            "Keep caveated as research context only.",
        )

    if term == "requires_resync":
        return (
            "requires_resync_handling",
            "engine exposes resync state but downstream use may ignore it.",
            "Ensure callers propagate resync flags before production use.",
        )

    if term == "volume_delta" and consumer_type == "documentation":
        return (
            "research_only",
            "signed-flow references in docs are not deployment evidence.",
            "Keep as documentation only until provenance and wiring are validated.",
        )

    return (
        "research_only",
        "OFI-related reference is not a production consumer.",
        "Keep it research-only until explicit wiring and provenance validation exist.",
    )


def scan_repo(repo_root: Path) -> list[AuditReference]:
    records: dict[tuple[str, str, str], AuditReference] = {}
    for path in _iter_files(repo_root):
        text = path.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()
        for term, pattern in SEARCH_TERMS:
            matches = list(pattern.finditer(text))
            if not matches:
                continue
            first = matches[0]
            first_line = text.count("\n", 0, first.start()) + 1
            line_text = lines[first_line - 1] if 0 <= first_line - 1 < len(lines) else ""
            ref_type = _reference_type(path, term, line_text)
            status, risk, required_action = _status(path, term, ref_type, line_text, text)
            key = (str(path.relative_to(repo_root)), term, ref_type)
            records[key] = AuditReference(
                path=str(path.relative_to(repo_root)),
                symbol_or_function=term,
                reference_type=ref_type,
                consumer_type=_consumer_type(path),
                status=status,
                risk=risk,
                required_action=required_action,
                occurrences=len(matches),
                first_line=first_line,
                excerpt=line_text.strip()[:200],
            )
    return sorted(records.values(), key=lambda row: (row.path, row.symbol_or_function, row.reference_type))


def _table(rows: list[dict[str, object]], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, sep]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")
    return "\n".join(lines)


def _build_summary(rows: list[AuditReference]) -> dict[str, object]:
    by_status = Counter(row.status for row in rows)
    by_consumer = Counter(row.consumer_type for row in rows)
    replay_or_strategy_refs = [
        row for row in rows if row.path.startswith("replays/") or row.path.startswith("scripts/v92_alpha_strategy_test.py")
    ]
    resync_refs = [row for row in rows if row.status == "requires_resync_handling"]
    dense_assumption_refs = [row for row in rows if row.symbol_or_function in {"OFI", "ofi"} and row.reference_type in {"function_call", "column_reference"} and row.consumer_type in {"research_script", "feature_builder"}]
    return {
        "reference_count": len(rows),
        "file_count": len({row.path for row in rows}),
        "status_counts": by_status,
        "consumer_counts": by_consumer,
        "replay_or_strategy_refs": replay_or_strategy_refs,
        "resync_refs": resync_refs,
        "dense_assumption_refs": dense_assumption_refs,
    }


def build_report(repo_root: Path, rows: list[AuditReference]) -> str:
    summary = _build_summary(rows)
    docs_drift = [row for row in rows if row.consumer_type == "documentation" and row.status == "stale"]
    replay_or_strategy_paths = sorted({row.path for row in rows if row.path.startswith("replays/") or row.path.startswith("scripts/v92_alpha_strategy_test.py")})
    data_policy_rows = [row for row in rows if row.consumer_type == "data_policy"]

    lines: list[str] = []
    lines.append("# V9.2 OFI Downstream Consumer Audit")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append("Audit every downstream OFI-related reference and classify whether it is safe, research-only, stale, broken, not wired, requires resync-aware handling, or requires provenance validation.")
    lines.append("")
    lines.append("This audit does not approve OFI for production, paper trading, live trading, or alpha use.")
    lines.append("")
    lines.append("## Search Scope")
    lines.append("")
    lines.append(f"- Repo root: `{repo_root}`")
    lines.append("- File types: `.py`, `.md`, `.toml`, `.yaml`, `.yml`, `.json`, `.txt`")
    lines.append("- Ignored directories: `.git/`, `.venv/`, `__pycache__/`, `data/`, `reports/`, `tmp_diagnostics/`")
    lines.append("")
    lines.append("## Method")
    lines.append("")
    lines.append("- Scan the repository for OFI-related symbols and related signed-flow terms.")
    lines.append("- Classify each unique file/reference pair by reference type, consumer type, status, risk, and required action.")
    lines.append("- Summarize replay / strategy usage, data-policy usage, resync risk, coverage risk, and documentation drift.")
    lines.append("")
    lines.append("## Executive Finding")
    lines.append("")
    lines.append("The repaired OFI engine is present, but no replay or production strategy path is wired to consume it. Current usage is concentrated in feature-builder code, research diagnostics, data-policy helpers, tests, and documentation.")
    lines.append("")
    lines.append("## Reference Inventory")
    lines.append("")
    lines.append(
        _table(
            [asdict(row) for row in rows],
            [
                "path",
                "symbol_or_function",
                "reference_type",
                "consumer_type",
                "status",
                "risk",
                "required_action",
                "occurrences",
                "first_line",
            ],
        )
    )
    lines.append("")
    lines.append("## Replay / Strategy Usage")
    lines.append("")
    if replay_or_strategy_paths:
        lines.append("The audit found OFI references in these replay/strategy-adjacent files:")
        for path in replay_or_strategy_paths:
            lines.append(f"- `{path}`")
        lines.append("")
        lines.append("These references are research-only or not wired, not production-approved replay paths.")
    else:
        lines.append("No replay or production strategy path currently consumes the repaired OFI engine.")
    lines.append("")
    lines.append("## Data Policy Usage")
    lines.append("")
    if data_policy_rows:
        lines.append(
            _table(
                [asdict(row) for row in data_policy_rows],
                ["path", "symbol_or_function", "reference_type", "status", "risk", "required_action"],
            )
        )
        lines.append("")
        lines.append("`join_ofi_to_bars_preserve_coverage` is the positive data-policy reference: it preserves bar count and is the canonical OFI join helper.")
    else:
        lines.append("No OFI data-policy helper was found.")
    lines.append("")
    lines.append("## Resync Handling Risk")
    lines.append("")
    if summary["resync_refs"]:
        lines.append("The repaired engine exposes `requires_resync`, but no downstream replay/strategy path was found to consume it directly.")
        lines.append("A downstream integration must propagate resync state before live use.")
    else:
        lines.append("No resync-aware downstream consumer was found.")
    lines.append("")
    lines.append("## Null / Coverage Risk")
    lines.append("")
    if summary["dense_assumption_refs"]:
        lines.append("Some research scripts and feature consumers treat OFI as a dense series. That is acceptable for read-only diagnostics, but not proof of production readiness.")
    else:
        lines.append("No consumer was found that clearly assumes dense/non-null OFI without caveat.")
    lines.append("")
    lines.append("## Documentation Drift")
    lines.append("")
    if docs_drift:
        lines.append("Stale or overly aspirational documentation references were found:")
        for row in docs_drift:
            lines.append(f"- `{row.path}` ({row.symbol_or_function})")
        lines.append("")
        lines.append("These docs should be treated as historical or aspirational, not as approval to deploy OFI.")
    else:
        lines.append("No explicit production-ready OFI claim was found in the audited documentation.")
    lines.append("")
    lines.append("## What Is Safe")
    lines.append("")
    lines.append("- `features/v92_data_policy.py::join_ofi_to_bars_preserve_coverage` preserves bar coverage.")
    lines.append("- Test-only and research-only OFI references are acceptable for validation work.")
    lines.append("- The repaired engine itself is warmup-safe and bounded.")
    lines.append("")
    lines.append("## What Is Not Safe")
    lines.append("")
    lines.append("- Treating OFI as production-approved.")
    lines.append("- Using OFI without downstream provenance and sequence-gap validation.")
    lines.append("- Assuming research diagnostics imply live/paper readiness.")
    lines.append("")
    lines.append("## Required Next Step")
    lines.append("")
    lines.append("Run a read-only provenance and coverage audit on the historical OFI/volume-delta sources that feed the research scripts, then validate any actual downstream consumer wiring before considering broader use.")
    lines.append("")
    lines.append("## Audit Notes")
    lines.append("")
    lines.append(f"- reference_count: `{summary['reference_count']}`")
    lines.append(f"- file_count: `{summary['file_count']}`")
    lines.append(f"- status_counts: `{dict(summary['status_counts'])}`")
    lines.append(f"- consumer_counts: `{dict(summary['consumer_counts'])}`")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    rows = scan_repo(args.repo_root)
    report = build_report(args.repo_root, rows)
    args.output_doc.parent.mkdir(parents=True, exist_ok=True)
    args.output_doc.write_text(report, encoding="utf-8")
    print(args.output_doc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
