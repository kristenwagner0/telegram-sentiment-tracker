#!/usr/bin/env python3
"""Redact usernames and PII from sentiment CSV before publishing a portfolio demo."""

from __future__ import annotations

import argparse
import hashlib
import random
import re
import sys
from pathlib import Path

import pandas as pd

MENTION_RE = re.compile(r"@\w{2,32}")
TME_LINK_RE = re.compile(r"https?://t\.me/\S+", re.I)
PHONE_RE = re.compile(r"(\+?\d[\d\s\-().]{7,}\d)")


def pseudonym_for(key: str, mapping: dict[str, str]) -> str:
    if not key or key == "unknown":
        return "Member 000"
    if key not in mapping:
        mapping[key] = f"Member {len(mapping) + 1:03d}"
    return mapping[key]


def hash_id(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def scrub_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    out = MENTION_RE.sub("[user]", text)
    out = TME_LINK_RE.sub("[link]", out)
    out = PHONE_RE.sub("[phone]", out)
    return out


def redact_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    name_map: dict[str, str] = {}

    if "from_id" in out.columns:
        for idx, row in out.iterrows():
            fid = str(row.get("from_id") or row.get("from") or "unknown")
            pseudo = pseudonym_for(fid, name_map)
            if "from" in out.columns:
                out.at[idx, "from"] = pseudo
            out.at[idx, "from_id"] = hash_id(fid) if fid else ""

    if "text" in out.columns:
        out["text"] = out["text"].astype(str).map(scrub_text)

    if "text_en" in out.columns:
        out["text_en"] = out["text_en"].astype(str).map(scrub_text)

    return out


def sample_report(df: pd.DataFrame, n: int = 20) -> str:
    neg = df[df.get("sentiment_label", pd.Series(dtype=str)).astype(str).str.lower() == "neg"]
    sample = neg.sample(min(n, len(neg)), random_state=42) if len(neg) else df.head(n)
    lines = ["\n── Spot-check sample (negative messages) ──"]
    for _, row in sample.iterrows():
        text = str(row.get("text", ""))[:120].replace("\n", " ")
        lines.append(f"  [{row.get('from', '?')}] {text}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Redact usernames for public portfolio demo CSV")
    parser.add_argument("-i", "--input", required=True, help="Input CSV (e.g. output/full_history_v4.csv)")
    parser.add_argument("-o", "--output", default="output/demo_public.csv", help="Output redacted CSV")
    parser.add_argument("--dry-run", action="store_true", help="Print sample quotes only, do not write")
    args = parser.parse_args()

    src = Path(args.input)
    if not src.exists():
        sys.exit(f"ERROR: Input not found: {src}")

    df = pd.read_csv(src, dtype=str, keep_default_na=False)
    redacted = redact_dataframe(df)

    unique_members = redacted["from"].nunique() if "from" in redacted.columns else 0
    print(f"Rows: {len(redacted):,} · unique pseudonyms: {unique_members:,}")
    print(sample_report(redacted))

    if args.dry_run:
        print("\n(dry-run — no file written)")
        return

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    redacted.to_csv(out, index=False)
    print(f"\nWrote {out} ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
