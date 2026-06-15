from __future__ import annotations

import zipfile
from pathlib import Path

import numpy as np
import polars as pl
import pytest

import scripts.v92_tier2_cache_builder as tier2_builder


def _lazy(rows: list[list[object]]) -> pl.LazyFrame:
    return pl.DataFrame(
        rows,
        schema=[
            "agg_id",
            "price",
            "qty",
            "first_id",
            "last_id",
            "timestamp",
            "is_buyer_maker",
            "is_best_match",
        ],
        orient="row",
    ).lazy()


def _write_zip(path: Path, csv_payloads: dict[str, str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, payload in csv_payloads.items():
            zf.writestr(name, payload)
    return path


def test_true_string_maps_to_negative_signed_qty(tmp_path: Path):
    out = tier2_builder.build_features_lazy(
        _lazy([[1, 100.0, 100.0, 1, 1, 1_700_000_000_000, "true", "true"]]),
        volume_bucket_size=500.0,
    ).collect()

    assert out.height == 1
    assert out["volume_delta"][0] < 0
    assert bool(out["is_complete"][0]) is False


def test_false_string_maps_to_positive_signed_qty(tmp_path: Path):
    out = tier2_builder.build_features_lazy(
        _lazy([[1, 100.0, 100.0, 1, 1, 1_700_000_000_000, "false", "true"]]),
        volume_bucket_size=500.0,
    ).collect()

    assert out.height == 1
    assert out["volume_delta"][0] > 0
    assert bool(out["is_complete"][0]) is False


def test_mixed_true_false_rows_produce_non_degenerate_volume_delta():
    out = tier2_builder.build_features_lazy(
        _lazy(
            [
                [1, 100.0, 100.0, 1, 1, 1_700_000_000_000, "true", "true"],
                [2, 101.0, 100.0, 2, 2, 1_700_000_001_000, "false", "true"],
                [3, 102.0, 100.0, 3, 3, 1_700_000_002_000, "true", "true"],
            ]
        ),
        volume_bucket_size=500.0,
    ).collect()

    assert out.height == 1
    assert out["volume_delta"][0] != 0


def test_is_complete_false_for_final_partial_bar():
    out = tier2_builder.build_features_lazy(
        _lazy(
            [
                [1, 100.0, 150.0, 1, 1, 1_700_000_000_000, "true", "true"],
                [2, 101.0, 150.0, 2, 2, 1_700_000_001_000, "false", "true"],
                [3, 102.0, 150.0, 3, 3, 1_700_000_002_000, "true", "true"],
            ]
        ),
        volume_bucket_size=500.0,
    ).collect()

    assert out.height == 1
    assert out["volume"][0] == pytest.approx(450.0)
    assert bool(out["is_complete"][0]) is False


def test_vwap_is_null_or_finite_for_zero_or_degenerate_volume():
    out = tier2_builder.build_features_lazy(
        _lazy([[1, 100.0, 0.0, 1, 1, 1_700_000_000_000, "true", "true"]]),
        volume_bucket_size=500.0,
    ).collect()

    values = out["vwap"].to_list()
    assert all(v is None or np.isfinite(v) for v in values)


def test_extract_first_csv_raises_for_multiple_csv_payloads(tmp_path: Path):
    archive = _write_zip(
        tmp_path / "BTCUSDT-aggTrades-2024-01.zip",
        {
            "a.csv": "1,2,3\n",
            "b.csv": "4,5,6\n",
        },
    )

    with pytest.raises(ValueError, match="exactly one CSV payload"):
        tier2_builder._extract_first_csv(archive, tmp_path / "tmp")


def test_main_returns_non_zero_when_archive_processing_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    archive = tmp_path / "archives" / "BTCUSDT-aggTrades-2024-01.zip"
    _write_zip(
        archive,
        {
            "payload.csv": "1,100,100,1,1,1700000000000,true,true\n",
        },
    )

    monkeypatch.setattr(tier2_builder, "discover_aggtrade_archives", lambda *args, **kwargs: [archive])
    monkeypatch.setattr(
        tier2_builder,
        "process_archive_lazy",
        lambda *args, **kwargs: "[2024-01] Failed during processing: boom",
    )

    exit_code = tier2_builder.main(
        [
            "--search-dir",
            str(tmp_path / "archives"),
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )

    assert exit_code == 1
