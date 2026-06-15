#!/usr/bin/env python3
"""Generate a fully synthetic Telegram sentiment CSV for portfolio demos."""

from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

CHAT_NAME = "Helix Protocol Community"
PROJECT_TAG = "helix"

POS_TEMPLATES = [
    "헬릭스 메인넷 업그레이드 정말 매끄럽게 진행됐어요!",
    "커뮤니티 답변 항상 빠르고 도움이 됩니다. 감사합니다!",
    "스테이킹 리워드가 이번 분기 기대 이상이에요 👍",
    "새 거버넌스 제안 내용 좋네요. 찬성합니다.",
    "테스트넷 이번 버전 훨씬 안정적입니다. 잘 됐어요.",
    "온보딩 가이드 덕분에 신규 멤버도 금방 적응하네요.",
    "개발팀 AMA 정말 유익했습니다. 로드맵 기대됩니다.",
    "Helix staking rewards look solid this epoch — nice work team.",
]
NEG_TEMPLATES = [
    "지갑 동기화가 계속 실패합니다. 해결 방법 있나요?",
    "가스비가 예상보다 훨씬 높아서 불편합니다.",
    "브릿지 처리 대기 시간이 너무 길어요.",
    "스테이킹 UI 설명이 헷갈려요. 문서 업데이트 부탁드립니다.",
    "Bridge queue is frustrating — waited over an hour yesterday.",
]
NEU_TEMPLATES = [
    "다음 AMA 일정 공지 확인했습니다.",
    "공식 문서 링크 공유드립니다.",
    "네트워크 점검 안내 참고 부탁드립니다.",
    "Reminder: mainnet maintenance window is Saturday 02:00 UTC.",
]
NEG_KEYWORDS = ["wallet sync", "gas fees", "bridge delay", "staking UI", "testnet faucet"]
FIRST_NAMES = ["Orbit", "Nova", "Minji", "Kai", "Yuna", "Dex", "Hana", "Jin", "Ren", "Nari"]
SUFFIXES = ["Trader", "HODL", "Node", "Dev", "Kim", "Validator", "DAO"]


def build_members(rng: random.Random, n: int = 220) -> list[tuple[str, str]]:
    members: list[tuple[str, str]] = []
    seen: set[str] = set()
    while len(members) < n:
        name = f"{rng.choice(FIRST_NAMES)}{rng.choice(SUFFIXES)}{rng.randint(1, 999)}"
        if name in seen:
            continue
        seen.add(name)
        members.append((name, f"user_{PROJECT_TAG}_{len(members)+1:04d}"))
    return members


def load_week_counts(template: Path) -> list[tuple[str, int]]:
    counts: dict[str, int] = defaultdict(int)
    with template.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            counts[row["week_start"]] += 1
    return sorted(counts.items())


def sentiment_probs(week_idx: int, total_weeks: int) -> tuple[float, float, float]:
    t = week_idx / max(total_weeks - 1, 1)
    pos = 0.35 + 0.25 * t
    neg = 0.38 - 0.16 * t
    neu = max(0.05, 1.0 - pos - neg)
    total = pos + neg + neu
    return pos / total, neg / total, neu / total


def pick_label(rng: random.Random, pos_p: float, neg_p: float) -> str:
    r = rng.random()
    if r < pos_p:
        return "pos"
    if r < pos_p + neg_p:
        return "neg"
    return "neu"


def pick_text(rng: random.Random, label: str) -> str:
    return rng.choice({"pos": POS_TEMPLATES, "neg": NEG_TEMPLATES, "neu": NEU_TEMPLATES}[label])


def score_for(label: str, rng: random.Random) -> float:
    if label == "pos":
        return round(rng.uniform(0.72, 0.96), 4)
    if label == "neg":
        return round(rng.uniform(0.04, 0.28), 4)
    return round(rng.uniform(0.42, 0.58), 4)


def week_complaint_keywords(neg_texts: list[str], rng: random.Random) -> str:
    if not neg_texts:
        return ""
    themes = Counter(rng.choice(NEG_KEYWORDS) for _ in neg_texts[: min(40, len(neg_texts))])
    return "|".join(k for k, _ in themes.most_common(5))


def generate(template: Path, output: Path, seed: int, max_rows: int | None = None) -> dict:
    rng = random.Random(seed)
    week_counts = load_week_counts(template)
    total_weeks = len(week_counts)
    members = build_members(rng)
    fields = [
        "msg_id", "date", "week_start", "chat_name", "from", "from_id",
        "text", "sentiment_label", "sentiment_score", "is_reply", "top_complaints",
    ]
    msg_id = 1
    stats: Counter = Counter()
    week_neg_texts: dict[str, list[str]] = defaultdict(list)
    rows_buffer: list[dict] = []

    for week_idx, (week_start, count) in enumerate(week_counts):
        pos_p, neg_p, _ = sentiment_probs(week_idx, total_weeks)
        base = datetime.strptime(week_start[:10], "%Y-%m-%d")
        for _ in range(count):
            if max_rows is not None and msg_id > max_rows:
                break
            label = pick_label(rng, pos_p, neg_p)
            name, uid = rng.choice(members)
            dt = base + timedelta(days=rng.randint(0, 6), hours=rng.randint(8, 22), minutes=rng.randint(0, 59))
            text = pick_text(rng, label)
            rows_buffer.append({
                "msg_id": str(msg_id), "date": dt.strftime("%Y-%m-%d %H:%M"),
                "week_start": week_start, "chat_name": CHAT_NAME, "from": name, "from_id": uid,
                "text": text, "sentiment_label": label, "sentiment_score": str(score_for(label, rng)),
                "is_reply": "TRUE" if rng.random() < 0.22 else "FALSE", "top_complaints": "",
            })
            stats[label] += 1
            if label == "neg":
                week_neg_texts[week_start].append(text)
            msg_id += 1
        if max_rows is not None and msg_id > max_rows:
            break

    for row in rows_buffer:
        row["top_complaints"] = week_complaint_keywords(week_neg_texts[row["week_start"]], rng)

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows_buffer)

    total = sum(stats.values())
    return {
        "rows": total,
        "pos_pct": round(100 * stats["pos"] / total, 1),
        "neg_pct": round(100 * stats["neg"] / total, 1),
        "neu_pct": round(100 * stats["neu"] / total, 1),
        "weeks": total_weeks,
        "output": str(output),
        "size_mb": round(output.stat().st_size / 1e6, 1),
    }


def main() -> None:
    root = Path(__file__).parent
    parser = argparse.ArgumentParser(description="Generate synthetic portfolio demo CSV")
    parser.add_argument("-t", "--template", default=str(root / "output" / "full_history_v4.csv"))
    parser.add_argument("-o", "--output", default=str(root / "output" / "synthetic_demo.csv"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-rows", type=int, default=None)
    args = parser.parse_args()
    template = Path(args.template)
    if not template.exists():
        sys.exit(f"ERROR: Template not found: {template}")
    info = generate(template, Path(args.output), args.seed, args.max_rows)
    print(f"Wrote {info['output']} ({info['size_mb']} MB)")
    print(f"Rows: {info['rows']:,} · weeks: {info['weeks']}")
    print(f"Sentiment: {info['pos_pct']}% pos · {info['neg_pct']}% neg · {info['neu_pct']}% neu")


if __name__ == "__main__":
    main()
