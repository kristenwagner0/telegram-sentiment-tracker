"""
Telegram Sentiment Preprocessor
================================
Purpose: Parse Telegram result.json exports, run offline HuggingFace sentiment
         analysis (Korean or English), extract weekly complaint keywords, output CSV.
Deploy:  Local only — ML models run on your machine, not on Render.

Parses a Telegram result.json export, runs offline HuggingFace sentiment
analysis (Korean or English), extracts complaint keywords per week, and
outputs a CSV ready to paste into Google Sheets.

Usage
-----
  python telegram_sentiment.py --input result.json --lang ko
  python telegram_sentiment.py --input result.json --lang en --push-sheets

First run (large historical dump): outputs output/full_history.csv
Weekly runs: outputs output/week_YYYY-MM-DD.csv (single-week exports)

Requirements  (install once)
-----------------------------
  pip install -r requirements.txt

Models downloaded automatically on first run (~250-500 MB, then cached):
  Korean (default): monologg/koelectra-base-finetuned-nsmc  (informal chat)
  Korean (legacy):  snunlp/KR-FinBert-SC  (--model finbert, financial text)
  English:          distilbert-base-uncased-finetuned-sst-2-english
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

# Flush progress lines immediately when stdout is piped (e.g. tee rerun_v2.log)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass

import pandas as pd
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from tqdm import tqdm

BATCH_SIZE = 32

LABEL_MAP = {
    "positive": "pos",
    "negative": "neg",
    "neutral": "neu",
    "POSITIVE": "pos",
    "NEGATIVE": "neg",
    "LABEL_0": "neg",
    "LABEL_1": "pos",
    "LABEL_2": "neu",
}

STOPWORDS_KO = {
    "이", "그", "저", "것", "수", "를", "에", "의", "은", "는", "이다",
    "있", "하", "없", "하다", "합니다", "해요", "이에요", "아", "오", "네",
    "네요", "요", "죠", "좀", "더", "도", "안", "못", "제", "저", "우리",
    "그리고", "하지만", "그런데", "그래서", "또", "잘", "다", "나", "내",
    "ㅋㅋ", "ㅎㅎ", "ㅠㅠ", "ㅜㅜ", "진짜", "그냥", "근데", "이거", "저거",
    "뭐", "왜", "어떻게", "지금", "오늘", "내일", "어제", "여기", "거기",
}

# Tickers / project names — appear in almost every crypto chat message, not complaint themes
DOMAIN_STOP_KO = {
    "stx", "btc", "eth", "sbtc", "strc", "usda", "usdc", "the", "and", "for",
    "스택스", "스택", "스택스는", "비트코인", "비트", "이더", "이더리움",
    "bitcoin", "stacks", "stack", "crypto", "크립토", "코인", "coin",
    "bitflow", "nakamoto", "pox", "sip", "tge", "defi",
}

STOPWORDS_EN = {
    "the", "a", "an", "is", "it", "in", "on", "at", "to", "and", "or",
    "but", "for", "of", "this", "that", "i", "we", "you", "they", "he",
    "she", "my", "our", "your", "its", "be", "was", "are", "were", "has",
    "have", "had", "will", "can", "do", "did", "not", "no", "so", "just",
    "with", "from", "about", "what", "how", "when", "why", "who",
}

OUTPUT_COLUMNS = [
    "msg_id",
    "date",
    "week_start",
    "chat_name",
    "from",
    "from_id",
    "text",
    "sentiment_label",
    "sentiment_score",
    "is_reply",
    "top_complaints",
]

KO_MODELS = {
    "social": {
        "hf_id": "monologg/koelectra-base-finetuned-nsmc",
        "display": "KoELECTRA-NSMC (informal Korean)",
        "binary": True,
    },
    "finbert": {
        "hf_id": "snunlp/KR-FinBert-SC",
        "display": "KR-FinBert-SC (financial Korean)",
        "binary": False,
    },
}

EN_MODEL = {
    "hf_id": "distilbert-base-uncased-finetuned-sst-2-english",
    "display": "DistilBERT SST-2",
    "binary": True,
}

NEUTRAL_MIN_CHARS = 8
NEUTRAL_MAX_CONFIDENCE = 0.55


def resolve_ko_model(model: str) -> str:
    if model not in KO_MODELS:
        sys.exit(f"ERROR: Unknown Korean model '{model}'. Use: social or finbert")
    return model


def model_display_name(lang: str, ko_model: str) -> str:
    if lang == "ko":
        return KO_MODELS[ko_model]["display"]
    return EN_MODEL["display"]


def load_sentiment_pipeline(lang: str, ko_model: str = "social"):
    from transformers import pipeline

    if lang == "ko":
        ko_model = resolve_ko_model(ko_model)
        cfg = KO_MODELS[ko_model]
        model_name = cfg["hf_id"]
        print(f"Loading Korean sentiment model: {model_name}")
        print(f"  ({cfg['display']})")
        print("(Downloads on first run, then cached)")
        return pipeline(
            "text-classification",
            model=model_name,
            tokenizer=model_name,
            max_length=512,
            truncation=True,
        ), ko_model

    model_name = EN_MODEL["hf_id"]
    print(f"Loading English sentiment model: {model_name}")
    print("(Downloads ~250 MB on first run, then cached)")
    return pipeline(
        "text-classification",
        model=model_name,
        truncation=True,
        max_length=512,
    ), "en"


def normalise_label(raw: str) -> str:
    return LABEL_MAP.get(raw, "neu")


def apply_neutral_rules(
    text: str, label: str, score: float, lang: str, ko_model: str
) -> tuple[str, float]:
    """Short or low-confidence messages → neutral (for binary social models)."""
    if len(text.strip()) < NEUTRAL_MIN_CHARS:
        return "neu", score
    if lang == "ko" and ko_model == "social" and score < NEUTRAL_MAX_CONFIDENCE:
        return "neu", score
    if lang == "en" and score < NEUTRAL_MAX_CONFIDENCE:
        return "neu", score
    return label, score


def parse_telegram_json(path: str) -> tuple[pd.DataFrame, str]:
    print(f"Reading {path} ...")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    chat_name = data.get("name", Path(path).parent.name)
    messages = data.get("messages", [])
    if not messages:
        sys.exit(
            "ERROR: No messages found. Make sure you exported with 'result.json' format."
        )

    rows = []
    for msg in messages:
        if msg.get("type") != "message":
            continue

        raw_text = msg.get("text", "")
        if isinstance(raw_text, list):
            text = " ".join(
                part["text"] if isinstance(part, dict) else part for part in raw_text
            )
        else:
            text = raw_text

        text = text.strip()
        if not text:
            continue

        rows.append(
            {
                "msg_id": msg.get("id"),
                "date": msg.get("date", ""),
                "from": msg.get("from", "unknown"),
                "from_id": msg.get("from_id", ""),
                "text": text,
                "reply_to": msg.get("reply_to_message_id"),
                "chat_name": chat_name,
            }
        )

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    print(
        f"  → {len(df):,} messages parsed "
        f"({df['date'].min().date()} to {df['date'].max().date()})"
    )
    return df, chat_name


def add_week_column(df: pd.DataFrame) -> pd.DataFrame:
    """ISO week starting Monday. Column = YYYY-MM-DD of that Monday."""
    df = df.copy()
    df["week_start"] = df["date"].dt.to_period("W-MON").apply(
        lambda p: p.start_time.date().isoformat()
    )
    return df


def flag_replies(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["is_reply"] = df["reply_to"].notna()
    return df


def format_duration(seconds: float) -> str:
    seconds = max(0, seconds)
    if seconds < 90:
        return f"about {int(seconds)} seconds"
    if seconds < 3600:
        mins = max(1, int(round(seconds / 60)))
        return f"about {mins} minute{'s' if mins != 1 else ''}"
    hours = seconds / 3600
    if hours < 48:
        return f"about {hours:.1f} hours"
    return f"about {hours / 24:.1f} days"


def estimate_seconds_per_batch(lang: str, batch_size: int, ko_model: str = "social") -> float:
    """Conservative CPU estimate; refined live as batches complete."""
    if lang == "ko":
        base = 2.8 if ko_model == "social" else 3.5
    else:
        base = 1.8
    return base * (batch_size / 32)


def print_run_estimate(
    n_messages: int, lang: str, batch_size: int, ko_model: str = "social"
) -> int:
    num_batches = (n_messages + batch_size - 1) // batch_size
    est_secs = num_batches * estimate_seconds_per_batch(lang, batch_size, ko_model)
    lang_name = "Korean" if lang == "ko" else "English"
    model = model_display_name(lang, ko_model)

    print("\n── Time estimate ──────────────────────────────")
    print(f"  Messages       : {n_messages:,}")
    print(f"  Batches        : {num_batches:,}  (batch size {batch_size})")
    print(f"  Language/model : {lang_name} · {model}")
    print(f"  Estimated time : {format_duration(est_secs)}")
    print(
        f"  Likely range   : {format_duration(est_secs * 0.7)}"
        f" – {format_duration(est_secs * 1.5)}"
    )
    print("  Updates every 10 batches once processing starts.")
    print("  Keep this window open — Control+C to stop safely.")
    print()
    return num_batches


def run_sentiment(
    df: pd.DataFrame,
    pipe,
    batch_size: int,
    lang: str,
    ko_model: str = "social",
) -> pd.DataFrame:
    texts = df["text"].tolist()
    labels, scores = [], []
    n = len(texts)
    num_batches = (n + batch_size - 1) // batch_size
    batch_durations: list[float] = []
    started = time.time()

    print(f"Running sentiment on {n:,} messages ...")
    print(f"  Model: {model_display_name(lang, ko_model)}")
    print()

    pbar = tqdm(
        range(0, n, batch_size),
        total=num_batches,
        unit="batch",
        bar_format=(
            "{l_bar}{bar}| {n_fmt}/{total_fmt} batches "
            "[{elapsed}<{remaining}, {rate_fmt}]"
        ),
    )

    for batch_idx, i in enumerate(pbar):
        batch_start = time.time()
        batch_texts = [t[:1000] for t in texts[i : i + batch_size]]
        try:
            results = pipe(batch_texts)
        except Exception as e:
            tqdm.write(
                f"  Warning: batch {batch_idx + 1} failed ({e}), defaulting to neutral"
            )
            results = [{"label": "neutral", "score": 0.5}] * len(batch_texts)

        for text, r in zip(batch_texts, results):
            label = normalise_label(r["label"])
            score = round(r["score"], 4)
            label, score = apply_neutral_rules(text, label, score, lang, ko_model)
            labels.append(label)
            scores.append(score)

        batch_durations.append(time.time() - batch_start)
        done = batch_idx + 1

        if done >= 3 and done % 10 == 0:
            avg = sum(batch_durations) / len(batch_durations)
            remaining = (num_batches - done) * avg
            pct = done / num_batches * 100
            msgs_done = min(done * batch_size, n)
            tqdm.write(
                f"  ▸ {pct:.1f}% complete ({msgs_done:,}/{n:,} messages)"
                f" · ~{format_duration(remaining)} remaining"
            )

    elapsed = time.time() - started
    print()
    print(f"── Sentiment pass finished in {format_duration(elapsed)} ──")
    print()

    df = df.copy()
    df["sentiment_label"] = labels
    df["sentiment_score"] = scores
    return df


def _ko_words(text: str) -> list[str]:
    domain = DOMAIN_STOP_KO
    return [
        w for w in re.findall(r"[가-힣]{2,}|[a-zA-Z]{2,}", text.lower())
        if w not in domain
    ]


def _ko_phrase_tokenizer(text: str) -> list[str]:
    words = _ko_words(text)
    phrases = list(words)
    for i in range(len(words) - 1):
        phrases.append(f"{words[i]} {words[i + 1]}")
    return phrases


def _is_valid_keyword(kw: str, lang: str, stop: set[str]) -> bool:
    if not kw or len(kw) < 2:
        return False
    low = kw.lower()
    if low in stop or low in DOMAIN_STOP_KO:
        return False
    if lang == "ko":
        if not re.search(r"[가-힣]", kw):
            return False
        if re.fullmatch(r"[\W\d_.…?!,;:\s\-]+", kw):
            return False
        if len(kw) < 3 and " " not in kw:
            return False
    return True


def extract_keywords(
    texts: list[str],
    lang: str,
    top_n: int = 5,
    contrast_texts: list[str] | None = None,
) -> list[str]:
    if not texts:
        return []

    stop = STOPWORDS_KO if lang == "ko" else STOPWORDS_EN

    try:
        if lang == "ko":
            vec = TfidfVectorizer(
                tokenizer=_ko_phrase_tokenizer,
                preprocessor=lambda x: x,
                token_pattern=None,
                max_features=400,
                min_df=2,
            )
        else:
            vec = TfidfVectorizer(
                analyzer="word",
                ngram_range=(1, 2),
                max_features=200,
                stop_words=None,
                min_df=2,
            )
        x_neg = vec.fit_transform(texts)
        neg_scores = x_neg.sum(axis=0).A1

        if contrast_texts:
            x_all = vec.transform(contrast_texts)
            all_scores = x_all.sum(axis=0).A1
            scores = neg_scores - 0.35 * all_scores
        else:
            scores = neg_scores

        vocab = vec.get_feature_names_out()
        ranked = sorted(zip(vocab, scores), key=lambda item: -item[1])
        out = []
        for kw, sc in ranked:
            if sc <= 0:
                continue
            if not _is_valid_keyword(kw, lang, stop):
                continue
            if " " not in kw and len(kw) < 4:
                continue
            out.append(kw)
            if len(out) >= top_n:
                break
        return out
    except Exception:
        return []


def build_weekly_keywords(df: pd.DataFrame, lang: str) -> dict:
    results = {}
    for week, group in df.groupby("week_start"):
        neg_texts = group[group["sentiment_label"] == "neg"]["text"].tolist()
        all_texts = group["text"].tolist()
        results[week] = extract_keywords(
            neg_texts, lang, top_n=5, contrast_texts=all_texts
        )
    return results


def repeat_complainers(df: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    neg = df[df["sentiment_label"] == "neg"]
    return (
        neg.groupby(["from_id", "from"])
        .agg(neg_msgs=("msg_id", "count"))
        .reset_index()
        .sort_values("neg_msgs", ascending=False)
        .head(top_n)
    )


def build_output(df: pd.DataFrame, weekly_keywords: dict) -> pd.DataFrame:
    df = df.copy()
    df["top_complaints"] = df["week_start"].map(
        lambda w: " | ".join(weekly_keywords.get(w, []))
    )
    out = df[OUTPUT_COLUMNS].copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d %H:%M")
    return out


def print_summary(df: pd.DataFrame, lang: str, weekly_keywords: dict):
    total = len(df)
    counts = df["sentiment_label"].value_counts()
    print("\n── Summary ──────────────────────────────────")
    print(f"  Total messages : {total:,}")
    print(
        f"  Positive       : {counts.get('pos', 0):,} "
        f"({counts.get('pos', 0) / total * 100:.1f}%)"
    )
    print(
        f"  Negative       : {counts.get('neg', 0):,} "
        f"({counts.get('neg', 0) / total * 100:.1f}%)"
    )
    print(
        f"  Neutral        : {counts.get('neu', 0):,} "
        f"({counts.get('neu', 0) / total * 100:.1f}%)"
    )
    print(f"  Weeks covered  : {df['week_start'].nunique()}")
    print(f"  Date range     : {df['date'].min()} → {df['date'].max()}")

    print("\n── Top 5 repeat complainers ─────────────────")
    for _, row in repeat_complainers(df).iterrows():
        print(f"  {row['from']:<20} {row['neg_msgs']} negative messages")

    print("\n── Weekly complaint keywords (last 4 weeks) ─")
    last4 = sorted(df["week_start"].unique())[-4:]
    for w in last4:
        kws = weekly_keywords.get(w, [])
        print(f"  {w}  →  {', '.join(kws) if kws else '(none)'}")
    print()


def print_dry_run_summary(
    df: pd.DataFrame,
    chat_name: str,
    lang: str,
    batch_size: int,
    ko_model: str = "social",
):
    df = add_week_column(df)
    print("\n── Dry run (no sentiment model loaded) ──────")
    print(f"  Chat name      : {chat_name}")
    print(f"  Total messages : {len(df):,}")
    print(f"  Weeks covered  : {df['week_start'].nunique()}")
    print(f"  Date range     : {df['date'].min()} → {df['date'].max()}")
    print_run_estimate(len(df), lang, batch_size, ko_model)


def resolve_output_path(
    df: pd.DataFrame,
    output: str | None,
    output_dir: Path,
) -> Path:
    if output:
        path = Path(output)
        return path if path.is_absolute() else output_dir / path

    n_weeks = df["week_start"].nunique()
    if n_weeks <= 1:
        week = df["week_start"].iloc[0]
        return output_dir / f"week_{week}.csv"
    return output_dir / "full_history.csv"


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Telegram Sentiment Preprocessor")
    parser.add_argument(
        "--input", "-i", required=True, help="Path to Telegram result.json export"
    )
    parser.add_argument(
        "--lang",
        "-l",
        choices=["ko", "en"],
        default="ko",
        help="Language of the chat: ko (Korean) or en (English). Default: ko",
    )
    parser.add_argument(
        "--model",
        "-m",
        choices=["social", "finbert"],
        default="social",
        help=(
            "Korean model: social (KoELECTRA-NSMC, default, best for Telegram chat) "
            "or finbert (KR-FinBert-SC, financial text). Ignored for --lang en."
        ),
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output CSV filename (relative to --output-dir unless absolute)",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory for CSV output. Default: output",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Sentiment batch size. Reduce to 8 if you hit memory errors. Default: 32",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse only; skip model inference and file writes",
    )
    parser.add_argument(
        "--push-sheets",
        action="store_true",
        help="Append results to Google Sheet after CSV write (requires .env setup)",
    )
    parser.add_argument(
        "--sheet-id",
        default=None,
        help="Google Sheet ID (defaults to GOOGLE_SHEET_ID from .env)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df, chat_name = parse_telegram_json(args.input)
    df = add_week_column(df)
    df = flag_replies(df)

    ko_model = resolve_ko_model(args.model) if args.lang == "ko" else "social"

    if args.dry_run:
        print_dry_run_summary(df, chat_name, args.lang, args.batch_size, ko_model)
        return

    print_run_estimate(len(df), args.lang, args.batch_size, ko_model)
    pipe, model_key = load_sentiment_pipeline(args.lang, ko_model)
    df = run_sentiment(df, pipe, args.batch_size, args.lang, model_key)
    weekly_kw = build_weekly_keywords(df, args.lang)
    out = build_output(df, weekly_kw)

    out_path = resolve_output_path(df, args.output, output_dir)
    out.to_csv(out_path, index=False, encoding="utf-8-sig")

    print_summary(df, args.lang, weekly_kw)
    print(f"✅  Saved → {out_path}  ({len(out):,} rows)")
    print()

    if args.push_sheets:
        from sheets_sync import push_to_sheets

        sheet_id = args.sheet_id or os.environ.get("GOOGLE_SHEET_ID", "")
        appended, weekly_touched = push_to_sheets(
            out,
            weekly_kw,
            sheet_id=sheet_id,
        )
        print(
            f"✅  Google Sheets: {appended:,} new message rows appended, "
            f"{weekly_touched:,} weekly summary rows updated"
        )
        print()
    else:
        print("Next steps:")
        print("  1. Open Google Sheets")
        print("  2. File → Import → Upload the CSV")
        print("  3. Or re-run with --push-sheets after setting up .env")
        print()


if __name__ == "__main__":
    main()
