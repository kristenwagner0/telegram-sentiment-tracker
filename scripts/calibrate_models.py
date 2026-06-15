"""
Compare FinBert vs KoELECTRA-NSMC on a sample of messages before a full re-run.

Purpose: Pick the best Korean sentiment model for your chat style (informal vs financial).
Deploy:  Local only. Downloads both models — run once before large analysis jobs.

Usage:
  python scripts/calibrate_models.py -i /path/to/result.json
  python scripts/calibrate_models.py -i /path/to/result.json --samples 200
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from telegram_sentiment import (
    apply_neutral_rules,
    load_sentiment_pipeline,
    normalise_label,
    parse_telegram_json,
)


def score_batch(pipe, texts: list[str]) -> list[tuple[str, float]]:
    batch = [t[:1000] for t in texts]
    results = pipe(batch)
    out = []
    for text, r in zip(texts, results):
        label = normalise_label(r["label"])
        score = round(r["score"], 4)
        out.append((label, score))
    return out


def main():
    parser = argparse.ArgumentParser(description="Compare Korean sentiment models")
    parser.add_argument("--input", "-i", required=True, help="Path to result.json")
    parser.add_argument(
        "--samples", "-n", type=int, default=200, help="Number of messages to sample"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    df, chat_name = parse_telegram_json(args.input)
    n = min(args.samples, len(df))
    sample = df.sample(n=n, random_state=args.seed)

    print(f"\nChat: {chat_name}")
    print(f"Comparing {n} random messages (seed={args.seed})\n")
    print("Loading models (first run downloads weights)...\n")

    finbert_pipe, _ = load_sentiment_pipeline("ko", "finbert")
    social_pipe, _ = load_sentiment_pipeline("ko", "social")

    texts = sample["text"].tolist()
    batch_size = 32

    fin_labels: list[tuple[str, float]] = []
    social_labels: list[tuple[str, float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        fin_labels.extend(score_batch(finbert_pipe, batch))
        raw_social = score_batch(social_pipe, batch)
        for text, (label, score) in zip(batch, raw_social):
            social_labels.append(
                apply_neutral_rules(text, label, score, "ko", "social")
            )

    fin_counts = {"pos": 0, "neg": 0, "neu": 0}
    social_counts = {"pos": 0, "neg": 0, "neu": 0}
    changed = 0

    print("=" * 100)
    print(f"{'TEXT':<50} {'FINBERT':>12} {'NSMC':>12}")
    print("=" * 100)

    for text, (fl, fs), (sl, ss) in zip(texts, fin_labels, social_labels):
        fin_counts[fl] += 1
        social_counts[sl] += 1
        if fl != sl:
            changed += 1
        preview = text.replace("\n", " ")[:48]
        print(f"{preview:<50} {fl:>5}({fs:.2f}) {sl:>5}({ss:.2f})")

    print("=" * 100)
    print("\n── Label distribution on sample ───────────────")
    for name, counts in [("FinBert (old)", fin_counts), ("NSMC (new)", social_counts)]:
        total = sum(counts.values())
        print(
            f"  {name}: pos {counts['pos']/total*100:.1f}%  "
            f"neg {counts['neg']/total*100:.1f}%  "
            f"neu {counts['neu']/total*100:.1f}%"
        )
    print(f"\n  Labels differ on {changed}/{n} messages ({changed/n*100:.1f}%)")
    print("\nIf NSMC looks more realistic, run the full analysis:")
    print(
        '  python telegram_sentiment.py -i "YOUR/result.json" --lang ko '
        "-o full_history_v2.csv"
    )
    print()


if __name__ == "__main__":
    main()
