#!/usr/bin/env python3
"""Recompute top_complaints on an existing CSV (no sentiment re-run)."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from telegram_sentiment import build_weekly_keywords


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-i",
        "--input",
        default="output/full_history_v2.csv",
        help="Input CSV from a prior analysis run",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="output/full_history_v4.csv",
        help="Output CSV with refreshed top_complaints",
    )
    parser.add_argument("--lang", default="ko", choices=["ko", "en"])
    args = parser.parse_args()

    inp = Path(args.input)
    if not inp.exists():
        raise SystemExit(f"Input not found: {inp}")

    print(f"Loading {inp} …")
    df = pd.read_csv(inp)
    if "sentiment_label" not in df.columns:
        raise SystemExit("CSV missing sentiment_label column")

    print("Recomputing weekly complaint keywords …")
    weekly = build_weekly_keywords(df, args.lang)
    df = df.copy()
    df["top_complaints"] = df["week_start"].map(
        lambda w: " | ".join(weekly.get(w, []))
    )

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"Saved → {out}  ({len(df):,} rows)")

    weeks = sorted(weekly.keys())[-4:]
    print("\n── Last 4 weeks (sample) ──")
    for w in weeks:
        kws = weekly.get(w, [])
        print(f"  {w}  →  {', '.join(kws) if kws else '(none)'}")


if __name__ == "__main__":
    main()
