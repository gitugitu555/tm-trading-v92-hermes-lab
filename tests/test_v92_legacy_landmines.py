from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_no_legacy_fromtimestamp_open_time_div_1000_in_canonical_scripts():
    canonical_scripts = [
        ROOT / "scripts" / "v92_alpha_strategy_test.py",
        ROOT / "scripts" / "v92_regime_validation.py",
        ROOT / "features" / "regime_classifier.py",
    ]

    for path in canonical_scripts:
        if not path.exists():
            continue
        source = path.read_text()
        assert "datetime.fromtimestamp(open_time / 1000)" not in source


def test_no_unrestricted_drop_nulls_in_alpha_evaluator():
    alpha_script = ROOT / "scripts" / "v92_alpha_strategy_test.py"
    source = alpha_script.read_text()

    assert ".drop_nulls()" not in source
