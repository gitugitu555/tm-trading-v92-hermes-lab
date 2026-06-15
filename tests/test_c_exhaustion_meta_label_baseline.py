from __future__ import annotations

import inspect

import numpy as np
import pandas as pd

import scripts.diagnose_c_exhaustion_meta_label_baseline as meta


def _feature_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "pre_signal_return_12_bars_bps": [1.0, 2.0, 3.0],
            "pre_signal_return_24_bars_bps": [10.0, 20.0, 30.0],
            "pre_signal_return_36_bars_bps": [100.0, 200.0, 300.0],
            "realized_vol_12_bars_bps": [0.1, 0.2, 0.3],
            "realized_vol_24_bars_bps": [0.4, 0.5, 0.6],
            "realized_vol_36_bars_bps": [0.7, 0.8, 0.9],
            "range_expansion_ratio_12": [1.0, 1.1, 1.2],
            "range_expansion_ratio_24": [1.3, 1.4, 1.5],
            "range_expansion_ratio_36": [1.6, 1.7, 1.8],
            "body_to_range_ratio": [0.1, 0.2, 0.3],
            "volume_over_vol95_ratio": [1.0, 2.0, 3.0],
            "close_vs_local_low_bps": [4.0, 5.0, 6.0],
            "adr_stretch": [0.7, 0.8, 0.9],
            "rv_1d": [0.11, 0.12, 0.13],
            "rv_15th_pct": [0.14, 0.15, 0.16],
            "bar_range": [7.0, 8.0, 9.0],
            "body_size": [1.0, 1.5, 2.0],
            "volume": [100.0, 200.0, 300.0],
            "vol_roll_95": [400.0, 500.0, 600.0],
        }
    )


def test_dependency_check_path_can_report_unavailable(monkeypatch):
    monkeypatch.setattr(meta.importlib.util, "find_spec", lambda name: None)

    assert meta.check_sklearn_available() is False


def test_allowed_and_forbidden_features_are_leakage_safe():
    allowed = meta.get_allowed_features()
    forbidden = meta.get_forbidden_features()

    assert allowed == meta.ALLOWED_FEATURES
    assert all("post_signal" not in feature for feature in allowed)
    assert all("trend_continuation" not in feature for feature in allowed)
    assert all("failed_reversal" not in feature for feature in allowed)
    assert all(feature not in forbidden for feature in allowed)
    assert "net_return_bps" in forbidden
    assert "gross_return_bps" in forbidden
    assert "exit_time" in forbidden
    assert "exit_price" in forbidden
    assert any(item.startswith("post_signal_return_") for item in forbidden)


def test_walk_forward_splits_are_chronological():
    splits = meta.get_walk_forward_splits()

    assert [split["validate_year"] for split in splits] == [2022, 2023, 2024, 2025]
    assert [split["test_year"] for split in splits] == [2023, 2024, 2025, 2026]
    for split in splits:
        assert max(split["train_years"]) < split["validate_year"] < split["test_year"]


def test_train_only_imputer_and_scaler_fit_on_train_data():
    train = _feature_frame()
    validate = _feature_frame() * 10
    test = _feature_frame() * 100

    imputer, scaler = meta.fit_preprocessors(train, feature_names=meta.ALLOWED_FEATURES, model_family="logistic_regression_l2")

    assert np.allclose(imputer.statistics_, train[meta.ALLOWED_FEATURES].median(axis=0).to_numpy(dtype=float))
    assert scaler is not None
    transformed_train = meta.transform_features(train, feature_names=meta.ALLOWED_FEATURES, imputer=imputer, scaler=scaler)
    transformed_validate = meta.transform_features(validate, feature_names=meta.ALLOWED_FEATURES, imputer=imputer, scaler=scaler)
    transformed_test = meta.transform_features(test, feature_names=meta.ALLOWED_FEATURES, imputer=imputer, scaler=scaler)

    assert transformed_train.shape == (3, len(meta.ALLOWED_FEATURES))
    assert transformed_validate.shape == transformed_train.shape
    assert transformed_test.shape == transformed_train.shape
    assert not np.allclose(transformed_train, transformed_validate)
    assert not np.allclose(transformed_train, transformed_test)


def test_threshold_selection_uses_validation_only():
    assert list(inspect.signature(meta.select_validation_threshold).parameters) == ["validate_df", "validate_scores", "thresholds"]

    validate = pd.DataFrame(
        {
            "label_trade_win": [1, 1, 0, 0, 1, 0],
            "net_return_bps": [50.0, 40.0, -10.0, -20.0, 30.0, -5.0],
        }
    )
    validate_scores = np.array([0.9, 0.85, 0.4, 0.35, 0.8, 0.1], dtype=float)

    result = meta.select_validation_threshold(validate, validate_scores)

    assert "selected_threshold" in result
    assert "threshold_rows" in result
    assert result["selected_threshold"] in {row["threshold"] for row in result["threshold_rows"]}
    assert result["best_available_threshold_diagnostic_only"] == result["selected_threshold"]


def test_threshold_selection_marks_too_small_when_no_validation_threshold_keeps_ten():
    validate = pd.DataFrame(
        {
            "label_trade_win": [1, 0, 1, 0],
            "net_return_bps": [10.0, -10.0, 5.0, -5.0],
        }
    )
    validate_scores = np.array([0.9, 0.8, 0.7, 0.6], dtype=float)

    result = meta.select_validation_threshold(validate, validate_scores, thresholds=np.array([0.5, 0.75, 0.9], dtype=float))

    assert result["validation_sample_too_small"] is True


def test_keep_remove_counts_balance():
    counts = meta.summarize_keep_remove_counts(test_count=17, kept_count=11)

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
    splits = meta.build_purged_walk_forward_splits(frame, purge_bars=1, embargo_bars=1)

    assert len(splits) == 4
    for split in splits:
        assert split["train_count"] >= 0
        assert split["validate_count"] >= 0
        assert split["test_count"] >= 0
        assert split["train_count"] + split["validate_count"] + split["test_count"] <= len(frame)


def test_closing_narrative_matches_evaluated_model_run():
    fold_rows = [
        {
            "model_status": "model_execution_completed",
            "test_year": 2025,
            "test_kept_trade_count": 14,
            "delta_vs_baseline_bps": 6.332226,
            "split": "walk_forward_3",
            "model_family": "decision_tree_depth_2",
            "test_net_expectancy_bps_if_trading_kept_signals": -144.965558,
        },
        {
            "model_status": "model_execution_completed",
            "test_year": 2026,
            "test_kept_trade_count": 7,
            "delta_vs_baseline_bps": 27.899317,
            "split": "walk_forward_4",
            "model_family": "decision_tree_depth_3",
            "test_net_expectancy_bps_if_trading_kept_signals": 9.637375,
        },
    ]

    closing = meta.build_closing_narrative(fold_rows, sklearn_available=True)
    rendered = "\n".join(closing["interpretation"] + closing["what_not_valid"] + closing["decision"])

    assert "blocked environment" not in rendered
    assert "No improvement claim can be made from this blocked environment" not in rendered
    assert "blocked_missing_sklearn" not in rendered
    assert "Partially. The 2025 model folds preserve at least 10 kept trades" in rendered
    assert "Decision label: `meta_labeling_worth_deeper_research`." in rendered
