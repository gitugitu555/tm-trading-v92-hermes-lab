from __future__ import annotations

from pathlib import Path

import scripts.audit_l2_ofi_source_inventory as audit


def test_missing_root_reported_not_fatal(tmp_path):
    missing = tmp_path / "missing-root"
    existing = tmp_path / "tm-trading-v555" / "data" / "raw" / "cryptohftdata" / "orderbook" / "binance_futures" / "BTCUSDT" / "2026-01-01" / "00"
    existing.mkdir(parents=True)
    (existing / "BTCUSDT_orderbook.parquet.zst").write_bytes(b"")

    result = audit.audit_inventory([missing, tmp_path])

    assert any((not row.exists) and row.path == str(missing) for row in result.root_status)
    assert any(row.exists for row in result.root_status)


def test_classify_candidate_path_for_l2_and_tbt_and_trades_and_manifest():
    l2_type, l2_readiness, _, _ = audit.classify_candidate_path(
        Path("/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-01-01/00/BTCUSDT_depthUpdate_2026-01-01.jsonl")
    )
    tbt_type, tbt_readiness, _, _ = audit.classify_candidate_path(
        Path("/mnt/seagate/tm-trading-v555/data/raw/cryptohftdata/orderbook/binance_futures/BTCUSDT/2026-01-01/00/BTCUSDT_full_depth_tbt.parquet")
    )
    trade_type, trade_readiness, _, _ = audit.classify_candidate_path(
        Path("/mnt/seagate/tm-trading-v555/data/raw/binance/spot/aggTrades/BTCUSDT/2026-05-04/BTCUSDT-aggTrades-2026-05-04.zip")
    )
    manifest_type, manifest_readiness, _, _ = audit.classify_candidate_path(Path("/tmp/README.md"))

    assert l2_type == "l2_diff"
    assert l2_readiness == "possibly_ready_needs_schema_check"
    assert tbt_type == "l2_tbt"
    assert tbt_readiness == "ofi_reconstruction_ready"
    assert trade_type == "agg_trades"
    assert trade_readiness == "not_ready_trades_only"
    assert manifest_type == "manifest"
    assert manifest_readiness == "not_ready_manifest_only"


def test_rendered_report_contains_no_approval_statement(tmp_path):
    existing = tmp_path / "tm-trading-v555" / "data" / "raw" / "cryptohftdata" / "orderbook" / "binance_futures" / "BTCUSDT" / "2026-01-01" / "00"
    existing.mkdir(parents=True)
    (existing / "BTCUSDT_orderbook.parquet.zst").write_bytes(b"")

    result = audit.audit_inventory([tmp_path])
    report = audit.render_report(result)

    assert audit.PRODUCTION_APPROVAL_STATEMENT in report
    assert "historical ofi output files were not found" in report.lower()
    assert "no search roots were missing" in report.lower() or "missing_root" in report.lower()
