#!/usr/bin/env python3
"""Research-only CLI for the V9.2 C_ExhaustionFade replay."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import polars as pl

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from replays.c_exhaustion_replay import (  # noqa: E402
    add_v92_regime_labels,
    normalize_v92_bar_timestamps,
    replay_c_exhaustionfade,
)

_PRODUCTION_OUTPUT_BLOCKLIST = (
    "data/hft/tier2",
    "data/hft",
    "data/raw",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bar-dir", type=Path, required=True)
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--bar-size", type=int, default=750)
    parser.add_argument("--horizon", type=int, default=36)
    parser.add_argument("--cost-bps", type=float, default=12.0)
    parser.add_argument("--output-dir", type=Path, default=Path("reports/c_exhaustion_replay"))
    parser.add_argument("--exposure", type=float, default=1.0)
    parser.add_argument("--starting-equity", type=float, default=100000.0)
    parser.add_argument("--write-json", action="store_true")
    parser.add_argument("--write-csv", action="store_true")
    parser.add_argument("--write-summary", action="store_true")
    return parser.parse_args(argv)


def _load_bar_dir(bar_dir: Path) -> pl.DataFrame:
    files = sorted(bar_dir.glob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"No parquet files found in {bar_dir}")
    return pl.concat([pl.scan_parquet(path) for path in files]).collect().sort("open_time")


def _is_under(candidate: Path, parent: Path) -> bool:
    candidate = candidate.resolve()
    parent = parent.resolve()
    return candidate == parent or candidate.is_relative_to(parent)


def _refuse_production_output(output_dir: Path) -> str | None:
    resolved_output = output_dir.expanduser().resolve()
    repo_root = ROOT.resolve()
    for relative in _PRODUCTION_OUTPUT_BLOCKLIST:
        blocked_root = (repo_root / relative).resolve()
        if _is_under(resolved_output, blocked_root):
            return f"Refused production/cache output path: {resolved_output}"
    return None


def build_calendar_daily_equity(
    trades: pd.DataFrame,
    *,
    exposure: float,
    starting_equity: float,
) -> pd.DataFrame:
    """Return calendar-daily equity after realized trade exits.

    Columns:
      date
      equity
      daily_return_pct

    Equity steps on exit_time because trade PnL is realized at exit.
    Forward-fill between realized exits.
    """
    if trades.empty or "exit_time" not in trades.columns:
        return pd.DataFrame(columns=["date", "equity", "daily_return_pct"])

    net_bps = trades["net_return_bps"].astype(float) * exposure
    equity_values = starting_equity + starting_equity * net_bps.cumsum() / 10_000.0
    exit_dates = pd.to_datetime(trades["exit_time"]).dt.normalize()

    daily_by_exit = pd.Series(equity_values.values, index=exit_dates)

    full_calendar = pd.date_range(
        start=exit_dates.min(),
        end=exit_dates.max(),
        freq="D",
    )

    daily_equity = (
        daily_by_exit.groupby(daily_by_exit.index)
        .last()
        .reindex(full_calendar)
        .ffill()
        .fillna(starting_equity)
    )

    daily_returns = daily_equity.pct_change() * 100.0

    return pd.DataFrame(
        {
            "date": full_calendar,
            "equity": daily_equity.values,
            "daily_return_pct": daily_returns.values,
        }
    )


def _compute_equity_metrics(
    trades: pd.DataFrame,
    yearly: pd.DataFrame,
    *,
    exposure: float,
    starting_equity: float,
) -> dict[str, float | int | str | bool]:
    if trades.empty:
        return {
            "calendar_daily_sharpe_365": 0.0,
            "business_day_sharpe_252": 0.0,
            "max_drawdown_pct": 0.0,
            "positive_year_count": 0,
            "worst_year": "n/a",
        }

    daily_df = build_calendar_daily_equity(
        trades,
        exposure=exposure,
        starting_equity=starting_equity,
    )

    daily_returns = daily_df["daily_return_pct"].dropna() / 100.0

    if len(daily_returns) > 1 and daily_returns.std(ddof=1) > 0:
        mean_dr = float(daily_returns.mean())
        std_dr = float(daily_returns.std(ddof=1))
        calendar_daily_sharpe_365 = mean_dr / std_dr * (365 ** 0.5)
        business_day_sharpe_252 = mean_dr / std_dr * (252 ** 0.5)
    else:
        calendar_daily_sharpe_365 = 0.0
        business_day_sharpe_252 = 0.0

    equity = daily_df["equity"].astype(float)
    running_max = equity.cummax()
    drawdown_pct = ((equity - running_max) / running_max) * 100.0
    max_drawdown_pct = float(abs(drawdown_pct.min())) if not drawdown_pct.empty else 0.0

    positive_year_count = int((yearly["net_expectancy_bps"] > 0).sum()) if not yearly.empty else 0
    if yearly.empty:
        worst_year = "n/a"
    else:
        worst_row = yearly.sort_values(["net_expectancy_bps", "year"]).iloc[0]
        worst_year = int(worst_row["year"])

    return {
        "calendar_daily_sharpe_365": calendar_daily_sharpe_365,
        "business_day_sharpe_252": business_day_sharpe_252,
        "max_drawdown_pct": max_drawdown_pct,
        "positive_year_count": positive_year_count,
        "worst_year": worst_year,
    }


def _build_report(
    *,
    symbol: str,
    bar_size: int,
    horizon: int,
    cost_bps: float,
    exposure: float,
    starting_equity: float,
    result,
) -> dict:
    yearly_records = result.yearly.to_dict(orient="records")
    metrics = _compute_equity_metrics(
        result.trades,
        result.yearly,
        exposure=exposure,
        starting_equity=starting_equity,
    )
    return {
        "metadata": {
            "branch": "C_ExhaustionFade",
            "side": "long_only",
            "symbol": symbol,
            "bar_size": bar_size,
            "horizon": horizon,
            "cost_bps": cost_bps,
            "exposure": exposure,
            "starting_equity": starting_equity,
            "production_path_touched": False,
        },
        "summary": {
            "trade_count": int(result.summary["trade_count"]),
            "net_expectancy_bps": float(result.summary["net_expectancy_bps"]),
            "win_rate": float(result.summary["win_rate"]),
            "profit_factor": float(result.summary["profit_factor"]),
            "calendar_daily_sharpe_365": float(metrics["calendar_daily_sharpe_365"]),
            "business_day_sharpe_252": float(metrics["business_day_sharpe_252"]),
            "max_drawdown_pct": float(metrics["max_drawdown_pct"]),
            "positive_year_count": int(metrics["positive_year_count"]),
            "worst_year": metrics["worst_year"],
            "production_path_touched": False,
        },
        "yearly": yearly_records,
        "trades": result.trades.to_dict(orient="records"),
    }


def _write_outputs(report: dict, output_dir: Path, args: argparse.Namespace, result) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    if args.write_json:
        json_path = output_dir / "c_exhaustion_replay_report.json"
        json_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        written.append(json_path)

    if args.write_csv:
        trades_path = output_dir / "trade_log.csv"
        result.trades.to_csv(trades_path, index=False)
        written.append(trades_path)

        # Backward compatibility for the current CLI regression test.
        legacy_trades_path = output_dir / "c_exhaustion_replay_trades.csv"
        result.trades.to_csv(legacy_trades_path, index=False)
        written.append(legacy_trades_path)

        net_bps = result.trades["net_return_bps"].astype(float) * args.exposure
        equity_by_trade = args.starting_equity + args.starting_equity * net_bps.cumsum() / 10_000.0

        equity_trade_df = result.trades[["entry_time", "exit_time"]].copy()
        equity_trade_df["equity"] = equity_by_trade.values
        equity_trade_df.to_csv(output_dir / "equity_curve_by_trade.csv", index=False)

        daily_df = build_calendar_daily_equity(
            result.trades,
            exposure=args.exposure,
            starting_equity=args.starting_equity,
        )

        daily_df[["date", "equity"]].to_csv(
            output_dir / "calendar_daily_equity.csv",
            index=False,
        )

        daily_df[["date", "daily_return_pct"]].to_csv(
            output_dir / "daily_returns.csv",
            index=False,
        )

        written.extend(
            [
                output_dir / "equity_curve_by_trade.csv",
                output_dir / "calendar_daily_equity.csv",
                output_dir / "daily_returns.csv",
            ]
        )

    if args.write_summary:
        summary_path = output_dir / "c_exhaustion_replay_summary.txt"
        lines = [
            "branch=C_ExhaustionFade",
            "side=long_only",
            f"symbol={args.symbol}",
            f"bar_size={args.bar_size}",
            f"horizon={args.horizon}",
            f"cost_bps={args.cost_bps}",
            f"trade_count={report['summary']['trade_count']}",
            f"net_expectancy_bps={report['summary']['net_expectancy_bps']:.6f}",
            f"win_rate={report['summary']['win_rate']:.6f}",
            f"profit_factor={report['summary']['profit_factor']:.6f}",
            f"calendar_daily_sharpe_365={report['summary']['calendar_daily_sharpe_365']:.6f}",
            f"business_day_sharpe_252={report['summary']['business_day_sharpe_252']:.6f}",
            f"max_drawdown_pct={report['summary']['max_drawdown_pct']:.6f}",
            f"positive_year_count={report['summary']['positive_year_count']}",
            f"worst_year={report['summary']['worst_year']}",
            "production_path_touched=false",
        ]
        summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        written.append(summary_path)

    return written


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    refused = _refuse_production_output(args.output_dir)
    if refused is not None:
        print(refused, file=sys.stderr)
        return 2

    try:
        bars = _load_bar_dir(args.bar_dir)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    bars = normalize_v92_bar_timestamps(bars)
    bars = add_v92_regime_labels(bars)

    result = replay_c_exhaustionfade(
        bars,
        horizon_bars=args.horizon,
        round_trip_cost_bps=args.cost_bps,
        bar_size=args.bar_size,
    )

    report = _build_report(
        symbol=args.symbol,
        bar_size=args.bar_size,
        horizon=args.horizon,
        cost_bps=args.cost_bps,
        exposure=args.exposure,
        starting_equity=args.starting_equity,
        result=result,
    )
    _write_outputs(report, args.output_dir, args, result)

    summary = report["summary"]
    print(
        "branch=C_ExhaustionFade "
        f"side=long_only "
        f"bar_size={args.bar_size} "
        f"horizon={args.horizon} "
        f"cost_bps={args.cost_bps} "
        f"trade_count={summary['trade_count']} "
        f"net_expectancy_bps={summary['net_expectancy_bps']:.6f} "
        f"win_rate={summary['win_rate']:.6f} "
        f"profit_factor={summary['profit_factor']:.6f} "
        f"calendar_daily_sharpe_365={summary['calendar_daily_sharpe_365']:.6f} "
        f"business_day_sharpe_252={summary['business_day_sharpe_252']:.6f} "
        f"max_drawdown_pct={summary['max_drawdown_pct']:.6f} "
        f"positive_year_count={summary['positive_year_count']} "
        f"worst_year={summary['worst_year']} "
        "production_path_touched=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
