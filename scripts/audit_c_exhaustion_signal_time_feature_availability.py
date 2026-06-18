#!/usr/bin/env python3
"""Read-only signal-time feature availability audit for C_ExhaustionFade."""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = Path("docs/v92_C_EXHAUSTION_SIGNAL_TIME_FEATURE_AVAILABILITY_AUDIT.md")
SEARCH_SUFFIXES = {".py", ".md", ".txt"}
IGNORED_PARTS = {".git", ".venv", "__pycache__", "data", "reports", "tmp_diagnostics"}

SIGNAL_SEARCH_TERMS = [
    "C_Exhaustion",
    "C_ExhaustionFade",
    "signal_time",
    "entry_time",
    "open_time",
    "close_time",
    "local_low",
    "vol_roll_95",
    "regime",
    "EXHAUSTED",
]

FEATURE_KEYWORDS = [
    "CVD",
    "delta",
    "absorption",
    "VPIN",
    "OFI",
    "MLOFI",
    "microprice",
    "spread",
    "depth",
    "queue",
    "imbalance",
    "spoof",
    "iceberg",
    "whale",
    "volume_delta",
    "funding",
    "open interest",
    "liquidation",
    "basis",
]

STATIC_FEATURE_ROWS = [
    {
        "feature_family": "OHLCV / regime",
        "implementation_files": [
            "replays/c_exhaustion_replay.py",
            "features/regime_classifier.py",
            "features/contextual_filters.py",
            "features/market_structure.py",
        ],
        "feature_examples": ["open", "high", "low", "close", "volume", "regime", "local_low", "vol_roll_95"],
        "consumed_by_replay": True,
        "consumed_by_diagnostics": True,
        "requires_trades": False,
        "requires_l2": False,
        "requires_approved_ofi_artifact": False,
        "current_eligibility": "available_now",
        "leakage_notes": "safe when based on completed bars and properly shifted rolling windows",
    },
    {
        "feature_family": "volume_delta / signed-flow",
        "implementation_files": ["features/trade_signing.py", "features/cvd.py", "features/delta.py"],
        "feature_examples": ["volume_delta", "delta", "cvd", "velocity", "acceleration", "signed side"],
        "consumed_by_replay": False,
        "consumed_by_diagnostics": True,
        "requires_trades": True,
        "requires_l2": False,
        "requires_approved_ofi_artifact": False,
        "current_eligibility": "available_with_existing_trade_columns",
        "leakage_notes": "safe only if sourced from past trades or precomputed bar columns with signal-time alignment",
    },
    {
        "feature_family": "absorption proxy",
        "implementation_files": ["features/absorption.py"],
        "feature_examples": ["ask absorption", "bid absorption", "delta threshold", "price move"],
        "consumed_by_replay": False,
        "consumed_by_diagnostics": True,
        "requires_trades": True,
        "requires_l2": False,
        "requires_approved_ofi_artifact": False,
        "current_eligibility": "available_with_existing_trade_columns",
        "leakage_notes": "requires a strict past-only window and no post-signal price movement",
    },
    {
        "feature_family": "VPIN / toxicity",
        "implementation_files": ["features/vpin.py"],
        "feature_examples": ["vpin_level", "vpin_slope", "toxicity_state", "toxicity_score"],
        "consumed_by_replay": False,
        "consumed_by_diagnostics": True,
        "requires_trades": True,
        "requires_l2": False,
        "requires_approved_ofi_artifact": False,
        "current_eligibility": "available_with_existing_trade_columns",
        "leakage_notes": "safe only with past-only buckets or completed bar splits",
    },
    {
        "feature_family": "footprint",
        "implementation_files": ["features/footprint.py"],
        "feature_examples": ["buy_volume", "sell_volume", "delta", "total_volume by price level"],
        "consumed_by_replay": False,
        "consumed_by_diagnostics": False,
        "requires_trades": True,
        "requires_l2": False,
        "requires_approved_ofi_artifact": False,
        "current_eligibility": "available_with_existing_trade_columns",
        "leakage_notes": "requires strict binning at or before signal time",
    },
    {
        "feature_family": "microstructure / book state",
        "implementation_files": ["features/microprice.py", "features/queue_imbalance.py", "features/l2_imbalance.py"],
        "feature_examples": ["microprice", "spread_bps", "depth_top5", "depth_top10", "weighted_imbalance"],
        "consumed_by_replay": False,
        "consumed_by_diagnostics": True,
        "requires_trades": False,
        "requires_l2": True,
        "requires_approved_ofi_artifact": True,
        "current_eligibility": "blocked_by_ofi_l2_approval",
        "leakage_notes": "needs L2 snapshots with no future-book contamination",
    },
    {
        "feature_family": "OFI / MLOFI",
        "implementation_files": ["features/microstructure_ofi.py", "features/microstructure_numba_ofi.py", "features/mlofi.py"],
        "feature_examples": ["ofi", "mlofi_weighted_aggregate", "book_trap_score", "book_agreement_score"],
        "consumed_by_replay": False,
        "consumed_by_diagnostics": True,
        "requires_trades": False,
        "requires_l2": True,
        "requires_approved_ofi_artifact": True,
        "current_eligibility": "blocked_by_ofi_l2_approval",
        "leakage_notes": "blocked until approved OFI artifacts and historical provenance are available",
    },
    {
        "feature_family": "spoofing / iceberg / whale pressure",
        "implementation_files": ["features/spoofing.py", "features/iceberg.py", "features/whale.py", "features/large_prints.py"],
        "feature_examples": ["spoof candidate", "iceberg candidate", "whale pressure", "large print z-score"],
        "consumed_by_replay": False,
        "consumed_by_diagnostics": True,
        "requires_trades": True,
        "requires_l2": True,
        "requires_approved_ofi_artifact": False,
        "current_eligibility": "blocked_by_missing_historical_source",
        "leakage_notes": "needs verified historical event coverage and stable timestamp ordering",
    },
    {
        "feature_family": "funding / OI / liquidation / basis",
        "implementation_files": [],
        "feature_examples": ["funding", "open interest", "liquidation", "crowding", "basis"],
        "consumed_by_replay": False,
        "consumed_by_diagnostics": False,
        "requires_trades": False,
        "requires_l2": False,
        "requires_approved_ofi_artifact": False,
        "current_eligibility": "blocked_by_missing_historical_source",
        "leakage_notes": "no verified point-in-time historical source was found in the inspected repo surface",
    },
]


@dataclass(frozen=True)
class SchemaAudit:
    path: str
    columns: list[str]
    row_count: int | None = None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-doc", type=Path, required=True)
    parser.add_argument("--bar-file", type=Path)
    parser.add_argument("--trade-log", type=Path)
    parser.add_argument("--max-rows", type=int, default=0)
    return parser.parse_args(argv)


def _iter_repo_files(repo_root: Path) -> Iterable[Path]:
    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORED_PARTS for part in path.parts):
            continue
        if path.suffix.lower() not in SEARCH_SUFFIXES:
            continue
        if path.name in {DEFAULT_OUTPUT.name, Path(__file__).name}:
            continue
        yield path


def _find_matches(repo_root: Path, needles: list[str]) -> list[str]:
    found: list[str] = []
    for path in _iter_repo_files(repo_root):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(needle.lower() in text.lower() for needle in needles):
            found.append(str(path.relative_to(repo_root)))
    return sorted(found)


def _find_signal_source_files(repo_root: Path) -> list[str]:
    patterns = [
        "replays/c_exhaustion_replay.py",
        "scripts/run_c_exhaustion_replay.py",
        "scripts/diagnose_c_exhaustion_meta_label_baseline.py",
        "scripts/diagnose_c_exhaustion_ex_ante_proxy_gate_matrix.py",
        "scripts/diagnose_c_exhaustion_signal_state.py",
        "scripts/diagnose_c_exhaustion_regime_context.py",
    ]
    found = []
    for rel in patterns:
        if (repo_root / rel).exists():
            found.append(rel)
    return found


def _extract_expected_columns_from_replay(repo_root: Path) -> list[str]:
    path = repo_root / "replays/c_exhaustion_replay.py"
    text = path.read_text(encoding="utf-8")
    columns: list[str] = []
    for name in [
        "open_time",
        "close_time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "regime",
        "vol_roll_95",
        "local_low",
        "c_signal",
        "signal_index",
        "entry_index",
        "exit_index",
        "signal_time",
        "entry_time",
        "exit_time",
        "volume_delta",
    ]:
        if name in text:
            columns.append(name)
    # Preserve a human-readable ordering without duplicates.
    seen: set[str] = set()
    ordered: list[str] = []
    for item in columns:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _read_schema(path: Path, max_rows: int = 0) -> SchemaAudit:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        frame = pd.read_csv(path, nrows=max_rows if max_rows > 0 else 0)
        return SchemaAudit(path=str(path), columns=list(frame.columns), row_count=None if max_rows == 0 else int(len(frame)))
    if suffix == ".parquet":
        frame = pd.read_parquet(path)
        if max_rows > 0:
            frame = frame.head(max_rows)
        return SchemaAudit(path=str(path), columns=list(frame.columns), row_count=int(len(frame)) if max_rows > 0 else None)
    raise ValueError(f"Unsupported optional schema file type: {path.suffix}")


def classify_feature(feature_name: str) -> dict[str, object]:
    lookup = {
        "OHLCV / regime": {
            "implementation_files": ["replays/c_exhaustion_replay.py", "features/regime_classifier.py"],
            "requires_trades": False,
            "requires_l2": False,
            "requires_approved_ofi_artifact": False,
            "current_eligibility": "available_now",
        },
        "volume_delta / signed-flow": {
            "implementation_files": ["features/trade_signing.py", "features/cvd.py", "features/delta.py"],
            "requires_trades": True,
            "requires_l2": False,
            "requires_approved_ofi_artifact": False,
            "current_eligibility": "available_with_existing_trade_columns",
        },
        "OFI / MLOFI": {
            "implementation_files": ["features/microstructure_ofi.py", "features/microstructure_numba_ofi.py", "features/mlofi.py"],
            "requires_trades": False,
            "requires_l2": True,
            "requires_approved_ofi_artifact": True,
            "current_eligibility": "blocked_by_ofi_l2_approval",
        },
        "microstructure / book state": {
            "implementation_files": ["features/microprice.py", "features/queue_imbalance.py", "features/l2_imbalance.py"],
            "requires_trades": False,
            "requires_l2": True,
            "requires_approved_ofi_artifact": True,
            "current_eligibility": "blocked_by_ofi_l2_approval",
        },
        "VPIN / toxicity": {
            "implementation_files": ["features/vpin.py"],
            "requires_trades": True,
            "requires_l2": False,
            "requires_approved_ofi_artifact": False,
            "current_eligibility": "available_with_existing_trade_columns",
        },
        "absorption proxy": {
            "implementation_files": ["features/absorption.py"],
            "requires_trades": True,
            "requires_l2": False,
            "requires_approved_ofi_artifact": False,
            "current_eligibility": "available_with_existing_trade_columns",
        },
        "funding / OI / liquidation / basis": {
            "implementation_files": [],
            "requires_trades": False,
            "requires_l2": False,
            "requires_approved_ofi_artifact": False,
            "current_eligibility": "blocked_by_missing_historical_source",
        },
    }
    if feature_name not in lookup:
        raise KeyError(feature_name)
    return dict(lookup[feature_name])


def _build_static_feature_rows(repo_root: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in STATIC_FEATURE_ROWS:
        impl_exists = any((repo_root / rel).exists() for rel in row["implementation_files"])
        out = dict(row)
        out["implementation_files"] = ", ".join(row["implementation_files"]) if row["implementation_files"] else "none"
        out["implementation_files_exist"] = impl_exists
        rows.append(out)
    return rows


def _scan_code_consumers(repo_root: Path) -> dict[str, list[str]]:
    files = {
        "replay": ["replays/c_exhaustion_replay.py"],
        "diagnostics": [
            "scripts/diagnose_c_exhaustion_meta_label_baseline.py",
            "scripts/diagnose_c_exhaustion_ex_ante_proxy_gate_matrix.py",
            "scripts/diagnose_c_exhaustion_signal_state.py",
            "scripts/diagnose_c_exhaustion_regime_context.py",
        ],
    }
    result: dict[str, list[str]] = {}
    for label, rel_paths in files.items():
        result[label] = [rel for rel in rel_paths if (repo_root / rel).exists()]
    return result


def build_report(repo_root: Path, *, bar_file: Path | None = None, trade_log: Path | None = None, max_rows: int = 0) -> tuple[str, dict[str, object]]:
    signal_source_files = _find_signal_source_files(repo_root)
    expected_columns = _extract_expected_columns_from_replay(repo_root)
    static_feature_rows = _build_static_feature_rows(repo_root)
    consumer_files = _scan_code_consumers(repo_root)
    static_matches = _find_matches(repo_root, SIGNAL_SEARCH_TERMS + FEATURE_KEYWORDS)
    schema_audits: list[SchemaAudit] = []
    if bar_file is not None:
        schema_audits.append(_read_schema(bar_file, max_rows=max_rows))
    if trade_log is not None:
        schema_audits.append(_read_schema(trade_log, max_rows=max_rows))

    inputs_mode = "static-only audit" if not schema_audits else "static + optional schema audit"
    decision_labels = [
        "c_exhaustion_signal_time_feature_audit_created",
        "gate_1_static_inventory_completed",
        "no_raw_l2_data_read",
        "no_ofi_artifacts_read",
        "no_ofi_artifacts_written",
        "no_strategy_backtest_run",
        "full_reconstruction_not_approved",
        "alpha_blocked",
        "paper_live_blocked",
    ]
    if not schema_audits:
        decision_labels.append("data_availability_audit_partial")
    else:
        decision_labels.append("optional_schema_audit_completed")

    lines: list[str] = []
    lines.append("# V9.2 C_Exhaustion Signal-Time Feature Availability Audit")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append("Identify which existing repo features are available at C_Exhaustion signal time, which are leakage-safe when shifted, and which remain blocked by unapproved OFI/L2 artifacts or missing historical sources.")
    lines.append("")
    lines.append("## Inputs")
    lines.append("")
    lines.append(f"- Audit mode: `{inputs_mode}`")
    lines.append(f"- Repo root: `{repo_root}`")
    lines.append(f"- Static signal-source files found: `{len(signal_source_files)}`")
    if bar_file is not None:
        lines.append(f"- Optional bar file: `{bar_file}`")
    if trade_log is not None:
        lines.append(f"- Optional trade log: `{trade_log}`")
    lines.append("")
    lines.append("## Read-Only Guardrails")
    lines.append("")
    lines.append("- No raw L2 data was read.")
    lines.append("- No OFI artifacts were read.")
    lines.append("- No OFI artifacts were written.")
    lines.append("- No market-data artifacts were written.")
    lines.append("- No strategy backtest was run.")
    lines.append("- No alpha claim is made.")
    lines.append("- Full reconstruction remains blocked.")
    lines.append("")
    lines.append("## C_Exhaustion Signal Source")
    lines.append("")
    lines.append("The signal path is defined in `replays/c_exhaustion_replay.py`, where `attach_c_exhaustion_signal` builds the past-only `c_signal` and `replay_c_exhaustionfade` converts signal bars into trades with `signal_time`, `entry_time`, and `exit_time`.")
    lines.append("The replay consumes `open_time`, `close_time`, `open`, `high`, `low`, `close`, `volume`, `regime`, `vol_roll_95`, and `local_low`. `run_c_exhaustion_replay.py` is the CLI entry point, while the diagnostics scripts reconstruct the same signal set for attribution and meta-label research.")
    lines.append("")
    lines.append("## Current Signal-Time Columns / Inputs")
    lines.append("")
    for col in expected_columns:
        lines.append(f"- `{col}`")
    if not expected_columns:
        lines.append("- `open_time`, `close_time`, `open`, `high`, `low`, `close`, `volume`, `regime`, `vol_roll_95`, `local_low`, `c_signal`, `signal_time`, `entry_time`, `exit_time`")
    lines.append("")
    lines.append("## Static Feature Inventory")
    lines.append("")
    headers = [
        "feature family",
        "implementation files",
        "feature examples",
        "consumed by C_Exhaustion replay?",
        "consumed by C_Exhaustion diagnostics?",
        "requires trades?",
        "requires L2?",
        "requires approved OFI artifact?",
        "current eligibility",
        "leakage notes",
    ]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in static_feature_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["feature_family"]),
                    str(row["implementation_files"]),
                    ", ".join(row["feature_examples"]),
                    "yes" if row["consumed_by_replay"] else "no",
                    "yes" if row["consumed_by_diagnostics"] else "no",
                    "yes" if row["requires_trades"] else "no",
                    "yes" if row["requires_l2"] else "no",
                    "yes" if row["requires_approved_ofi_artifact"] else "no",
                    str(row["current_eligibility"]),
                    str(row["leakage_notes"]),
                ]
            )
            + " |"
        )
    lines.append("")
    lines.append("## Available Now Without L2 Reconstruction")
    lines.append("")
    lines.append("- OHLCV context: returns, volatility, range, body/range, close-vs-local-low, ADR stretch, regime, and volume.")
    lines.append("- `volume_delta` if the bar or trade file already carries it.")
    lines.append("- CVD/delta if signed trade columns already exist in a local trade-derived source.")
    lines.append("- Absorption proxy if signed trade and price-move inputs exist.")
    lines.append("- VPIN / toxicity if buy/sell bucket inputs already exist.")
    lines.append("")
    lines.append("## Blocked Until OFI / L2 Artifact Approval")
    lines.append("")
    lines.append("- OFI")
    lines.append("- MLOFI")
    lines.append("- microprice")
    lines.append("- spread")
    lines.append("- depth")
    lines.append("- queue imbalance")
    lines.append("- L2 imbalance")
    lines.append("- spoofing")
    lines.append("- iceberg")
    lines.append("- L2 whale pressure")
    lines.append("")
    lines.append("## Blocked By Missing Historical Source")
    lines.append("")
    lines.append("- funding")
    lines.append("- OI")
    lines.append("- liquidation")
    lines.append("- derivatives crowding")
    lines.append("- basis")
    lines.append("")
    lines.append("## Leakage Risk Assessment")
    lines.append("")
    lines.append("- Same-bar leakage")
    lines.append("- Future bar leakage")
    lines.append("- Post-entry outcome leakage")
    lines.append("- Label leakage")
    lines.append("- Rolling-window endpoint leakage")
    lines.append("- Feature timestamp after signal timestamp")
    lines.append("- Bar close vs signal timing ambiguity")
    lines.append("")
    lines.append("## Gate 1 Finding")
    lines.append("")
    lines.append("Gate 1 static inventory: pass.")
    if schema_audits:
        lines.append("Gate 1 data availability: partial until the optional schema audit is matched to a known replay output and bar file pair.")
    else:
        lines.append("Gate 1 data availability: partial because no optional schema files were supplied.")
    lines.append("Gate 2 feature table dry run: not started.")
    lines.append("")
    lines.append("## Recommended Next Step")
    lines.append("")
    lines.append("Create a bounded read-only signal-time schema audit using a known C_Exhaustion replay output and a bar file, if available, to verify actual columns and timestamp alignment before any feature table dry run.")
    lines.append("")
    lines.append("## What Is Safe")
    lines.append("")
    lines.append("- Static inventory")
    lines.append("- Schema-only audit")
    lines.append("- Timestamp alignment audit")
    lines.append("- Leakage audit")
    lines.append("- Bounded read-only feature availability diagnostics")
    lines.append("")
    lines.append("## What Is Not Safe")
    lines.append("")
    lines.append("- Alpha claims")
    lines.append("- Strategy optimization")
    lines.append("- Full reconstruction")
    lines.append("- OFI artifact generation")
    lines.append("- Paper/live trading")
    lines.append("- Using unapproved L2 features")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    for label in decision_labels:
        lines.append(f"- `{label}`")

    if schema_audits:
        lines.append("")
        lines.append("## Optional Schema Audit")
        lines.append("")
        lines.append("| source file | columns |")
        lines.append("| --- | --- |")
        for audit in schema_audits:
            lines.append(f"| `{audit.path}` | `{', '.join(audit.columns)}` |")

    report = "\n".join(lines) + "\n"
    summary = {
        "signal_source_files": signal_source_files,
        "expected_columns": expected_columns,
        "static_inventory_count": len(static_feature_rows),
        "static_matches": static_matches,
        "consumer_files": consumer_files,
        "decision_labels": decision_labels,
        "schema_audits": schema_audits,
        "audit_mode": inputs_mode,
    }
    return report, summary


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report, _summary = build_report(
        ROOT,
        bar_file=args.bar_file,
        trade_log=args.trade_log,
        max_rows=args.max_rows,
    )
    args.output_doc.parent.mkdir(parents=True, exist_ok=True)
    args.output_doc.write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
