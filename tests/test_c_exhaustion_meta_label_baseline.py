from __future__ import annotations

import inspect

import pandas as pd

from scripts.diagnose_c_exhaustion_meta_label_baseline import (
    ALLOWED_FEATURES,
    FORBIDDEN_FEATURES,
    build_purged_walk_forward_splits,
    get_allowed_features,
    get_forbidden_features,
    get_walk_forward_splits,
    select_validation_threshold,
    summarize_keep_remove_counts,
)


def test_forbidden_features_exclude_post_signal_and_outcome_fields():
    forbidden = get_forbidden_features()

    assert "net_return_bps" in forbidden
    assert "gross_return_bps" in forbidden
    assert "exit_time" in forbidden
    assert "exit_price" in forbidden
    assert any(item.startswith("post_signal_return_") for item in forbidden)
    assert any(item.startswith("trend_continuation_flag_") for item in forbidden)
    assert any(item.startswith("failed_reversal_flag_") for item in forbidden)
    assert any(item.startswith("bad_context_label_") for item in forbidden)


def test_allowed_features_are_strictly_ex_ante():
    allowed = get_allowed_features()

    assert allowed == ALLOWED_FEATURES
    assert all("post_signal" not in feature for feature in allowed)
    assert all("trend_continuation" not in feature for feature in allowed)
    assert all("failed_reversal" not in feature for feature in allowed)
    assert all(feature not in FORBIDDEN_FEATURES for feature in allowed)


def test_walk_forward_splits_are_chronological():
    splits = get_walk_forward_splits()

    assert [split["validate_year"] for split in splits] == [2022, 2023, 2024, 2025]
    assert [split["test_year"] for split in splits] == [2023, 2024, 2025, 2026]
    for split in splits:
        assert max(split["train_years"]) < split["validate_year"] < split["test_year"]


def test_threshold_selection_signature_excludes_test_labels():
    params = list(inspect.signature(select_validation_threshold).parameters)

    assert params == ["y_true", "y_score"]


def test_keep_remove_counts_balance():
    counts = summarize_keep_remove_counts(test_count=17, kept_count=11)

    assert counts["test_count"] == 17
    assert counts["test_kept_trade_count"] == 11
    assert counts["test_removed_trade_count"] == 6
    assert counts["test_kept_rate"] == 11 / 17


def test_purged_split_counts_are_conservative():
    frame = pd.DataFrame(
        {
            "signal_time": pd.date_range("2020-01-01", periods=7, freq="YS"),
            "year": [2020, 2021, 2022, 2023, 2024, 2025, 2026],
            "signal_index": [0, 1, 2, 3, 4, 5, 6],
            "exit_index": [1, 2, 3, 4, 5, 6, 6],
        }
    )
    splits = build_purged_walk_forward_splits(frame, purge_bars=1, embargo_bars=1)

    assert len(splits) == 4
    for split in splits:
        assert split["train_count"] >= 0
        assert split["validate_count"] >= 0
        assert split["test_count"] >= 0
        assert split["train_count"] + split["validate_count"] + split["test_count"] <= len(frame)
