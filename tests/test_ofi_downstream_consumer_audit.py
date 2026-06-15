from __future__ import annotations

from pathlib import Path

import scripts.audit_ofi_downstream_consumers as audit


def test_scanner_finds_python_and_markdown_refs_and_ignores_reports_and_data(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "reports").mkdir()
    (tmp_path / "data").mkdir()

    (tmp_path / "src" / "consumer.py").write_text(
        "from features.microstructure_ofi import OFIEngine\n"
        "from features.v92_data_policy import join_ofi_to_bars_preserve_coverage\n"
        "print(OFIEngine, join_ofi_to_bars_preserve_coverage)\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "note.md").write_text("This note mentions OFI and volume_delta.", encoding="utf-8")
    (tmp_path / "reports" / "skip.md").write_text("OFI should not be scanned here.", encoding="utf-8")
    (tmp_path / "data" / "skip.txt").write_text("volume_delta should not be scanned here.", encoding="utf-8")

    rows = audit.scan_repo(tmp_path)

    paths = {row.path for row in rows}
    assert "src/consumer.py" in paths
    assert "docs/note.md" in paths
    assert "reports/skip.md" not in paths
    assert "data/skip.txt" not in paths


def test_classifier_marks_import_references_and_data_policy(tmp_path: Path):
    (tmp_path / "features").mkdir()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "features" / "v92_data_policy.py").write_text(
        "def join_ofi_to_bars_preserve_coverage(bars, ofi):\n    return bars\n",
        encoding="utf-8",
    )
    (tmp_path / "scripts" / "use_ofi.py").write_text(
        "from features.microstructure_ofi import OFIEngine\n",
        encoding="utf-8",
    )

    rows = audit.scan_repo(tmp_path)
    by_path_symbol = {(row.path, row.symbol_or_function): row for row in rows}

    assert by_path_symbol[("scripts/use_ofi.py", "microstructure_ofi")].reference_type == "import"
    assert by_path_symbol[("features/v92_data_policy.py", "join_ofi_to_bars_preserve_coverage")].consumer_type == "data_policy"
    assert by_path_symbol[("features/v92_data_policy.py", "join_ofi_to_bars_preserve_coverage")].status == "safe"


def test_report_includes_no_production_approval_statement(tmp_path: Path):
    (tmp_path / "features").mkdir()
    (tmp_path / "features" / "v92_data_policy.py").write_text(
        "def join_ofi_to_bars_preserve_coverage(bars, ofi):\n    return bars\n",
        encoding="utf-8",
    )

    rows = audit.scan_repo(tmp_path)
    report = audit.build_report(tmp_path, rows)

    assert "This audit does not approve OFI for production, paper trading, live trading, or alpha use." in report
