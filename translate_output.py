#!/usr/bin/env python3
"""Add text_en column to an analysis CSV using Google Translate (deep-translator)."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd
from deep_translator import GoogleTranslator


def translate_batch(texts: list[str], translator: GoogleTranslator, delay: float) -> list[str]:
    out = []
    for text in texts:
        t = (text or "").strip()
        if not t or len(t) < 2:
            out.append("")
            continue
        try:
            out.append(translator.translate(t[:4500]))
        except Exception:
            out.append("")
        time.sleep(delay)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", default="output/full_history_v3.csv")
    parser.add_argument("-o", "--output", default="output/full_history_v3_en.csv")
    parser.add_argument(
        "--mode",
        choices=["recent", "all"],
        default="recent",
        help="recent = last 2000 rows by date; all = entire file (slow)",
    )
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--delay", type=float, default=0.15, help="Seconds between batches")
    args = parser.parse_args()

    inp = Path(args.input)
    if not inp.exists():
        raise SystemExit(f"Input not found: {inp}")

    df = pd.read_csv(inp)
    if "text" not in df.columns:
        raise SystemExit("CSV missing text column")

    df = df.copy()
    if "text_en" not in df.columns:
        df["text_en"] = ""

    if args.mode == "recent":
        df["_sort_date"] = pd.to_datetime(df["date"], errors="coerce")
        idx = df.sort_values("_sort_date", ascending=False).head(2000).index
        df.drop(columns=["_sort_date"], inplace=True)
    else:
        idx = df.index

    translator = GoogleTranslator(source="ko", target="en")
    indices = list(idx)
    total = len(indices)
    print(f"Translating {total:,} messages ({args.mode} mode) …")

    for start in range(0, total, args.batch_size):
        chunk_idx = indices[start : start + args.batch_size]
        texts = df.loc[chunk_idx, "text"].fillna("").tolist()
        translated = translate_batch(texts, translator, args.delay / max(len(texts), 1))
        df.loc[chunk_idx, "text_en"] = translated
        done = min(start + args.batch_size, total)
        if done % 100 == 0 or done == total:
            print(f"  {done:,}/{total:,}")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"Saved → {out}")


if __name__ == "__main__":
    main()
