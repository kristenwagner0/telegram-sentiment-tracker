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

# (theme_label, weight, message variants)
POS_BY_THEME: list[tuple[str, int, list[str]]] = [
    ("Mainnet upgrades", 22, [
        "헬릭스 메인넷 업그레이드 정말 매끄럽게 진행됐어요!",
        "Mainnet v2 rollout felt stable on my node — impressed.",
        "업그레이드 후 블록 시간이 더 일정해진 것 같아요.",
        "Helix mainnet patch fixed the sync issue I had last week.",
        "메인넷 성능 개선 체감됩니다. 수고 많으셨어요!",
    ]),
    ("Staking rewards", 18, [
        "스테이킹 리워드가 이번 분기 기대 이상이에요 👍",
        "Helix staking rewards look solid this epoch — nice work team.",
        "리워드 계산이 공지랑 일치해서 안심됐어요.",
        "Delegated staking APY improved after the parameter tweak.",
        "스테이킹 대시보드에서 수익 확인하기 쉬워졌네요.",
    ]),
    ("Community support", 16, [
        "커뮤니티 답변 항상 빠르고 도움이 됩니다. 감사합니다!",
        "New member question got three helpful replies in minutes.",
        "모더레이터분들 주말에도 대응해주셔서 감사합니다.",
        "Someone shared a workaround that saved me an hour — great community.",
        "질문 올렸는데 친절하게 설명해주셔서 해결됐어요.",
    ]),
    ("Governance & AMA", 14, [
        "새 거버넌스 제안 내용 좋네요. 찬성합니다.",
        "개발팀 AMA 정말 유익했습니다. 로드맵 기대됩니다.",
        "Governance vote UI is much clearer now, thanks for the update.",
        "HIP-12 discussion was thoughtful — good process.",
        "투표 마감 전에 요약 공지 올려줘서 이해하기 좋았어요.",
    ]),
    ("Testnet stability", 12, [
        "테스트넷 이번 버전 훨씬 안정적입니다. 잘 됐어요.",
        "Testnet faucet worked first try today — rare win!",
        "샌드박스에서 컨트랙트 배포 테스트 성공했습니다.",
        "Public testnet reset was communicated well this time.",
        "테스트넷 익스플로러 속도가 많이 빨라졌네요.",
    ]),
    ("Onboarding & docs", 10, [
        "온보딩 가이드 덕분에 신규 멤버도 금방 적응하네요.",
        "Updated docs for bridge flow finally make sense.",
        "Quick-start tutorial was enough to get my wallet connected.",
        "문서 번역 퀄리티가 올라간 것 같아요.",
        "FAQ에 제가 찾던 내용이 추가됐네요.",
    ]),
    ("Validator operations", 8, [
        "노드 운영자들 대응 속도가 빨라진 것 같아요.",
        "Validator set change went smoothly — no missed slots.",
        "Monitoring alerts were accurate during the upgrade window.",
        "우리 밸리데이터 업타임 99.9% 유지 중입니다.",
    ]),
]

NEG_BY_THEME: list[tuple[str, int, list[str]]] = [
    ("Wallet sync", 25, [
        "지갑 동기화가 계속 실패합니다. 해결 방법 있나요?",
        "Wallet stuck on block 184002 after restart.",
        "모바일 지갑에서 잔액이 안 맞아요.",
    ]),
    ("Gas & fees", 20, [
        "가스비가 예상보다 훨씬 높아서 불편합니다.",
        "Fee spike during peak hours is rough for small txs.",
    ]),
    ("Bridge delays", 20, [
        "브릿지 처리 대기 시간이 너무 길어요.",
        "Bridge queue is frustrating — waited over an hour yesterday.",
    ]),
    ("Staking UI", 18, [
        "스테이킹 UI 설명이 헷갈려요. 문서 업데이트 부탁드립니다.",
        "Unbonding period not obvious in the app.",
    ]),
    ("Testnet faucet", 17, [
        "테스트넷 파셋 신청이 자꾸 오류가 납니다.",
        "Faucet rate limit hit even though I waited 24h.",
    ]),
]

NEU_TEMPLATES = [
    "다음 AMA 일정 공지 확인했습니다.",
    "공식 문서 링크 공유드립니다.",
    "네트워크 점검 안내 참고 부탁드립니다.",
    "주간 거버넌스 투표 마감 시간은 UTC 18:00입니다.",
    "Reminder: mainnet maintenance window is Saturday 02:00 UTC.",
    "신규 멤버 환영합니다. 질문 편하게 주세요.",
    "Testnet faucet resets every day at 00:00 UTC.",
    "Office hours moved to Thursday this week.",
]

FIRST_NAMES = ["Orbit", "Nova", "Minji", "Kai", "Yuna", "Dex", "Hana", "Jin", "Ren", "Nari"]
SUFFIXES = ["Trader", "HODL", "Node", "Dev", "Kim", "Validator", "DAO"]
EXTRA_SUFFIXES = ["", " ✅", " 👍", " — thanks!", " (works for me)", ""]


def build_weighted_picker(rng: random.Random, groups: list[tuple[str, int, list[str]]]):
    labels = [g[0] for g in groups]
    weights = [g[1] for g in groups]
    texts_by = {g[0]: g[2] for g in groups}

    def pick() -> tuple[str, str]:
        label = rng.choices(labels, weights=weights, k=1)[0]
        base = rng.choice(texts_by[label])
        return label, base + rng.choice(EXTRA_SUFFIXES)

    return pick


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


def score_for(label: str, rng: random.Random) -> float:
    if label == "pos":
        return round(rng.uniform(0.72, 0.96), 4)
    if label == "neg":
        return round(rng.uniform(0.04, 0.28), 4)
    return round(rng.uniform(0.42, 0.58), 4)


def generate(template: Path, output: Path, seed: int, max_rows: int | None = None) -> dict:
    rng = random.Random(seed)
    week_counts = load_week_counts(template)
    total_weeks = len(week_counts)
    members = build_members(rng)
    pick_pos = build_weighted_picker(rng, POS_BY_THEME)
    pick_neg = build_weighted_picker(rng, NEG_BY_THEME)
    fields = [
        "msg_id", "date", "week_start", "chat_name", "from", "from_id",
        "text", "sentiment_label", "sentiment_score", "is_reply", "top_complaints",
    ]
    msg_id = 1
    stats: Counter = Counter()
    week_neg_themes: dict[str, list[str]] = defaultdict(list)
    pos_theme_counts: Counter = Counter()
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
            if label == "pos":
                theme, text = pick_pos()
                pos_theme_counts[theme] += 1
            elif label == "neg":
                theme, text = pick_neg()
                week_neg_themes[week_start].append(theme)
            else:
                text = rng.choice(NEU_TEMPLATES) + rng.choice(EXTRA_SUFFIXES)
            rows_buffer.append({
                "msg_id": str(msg_id), "date": dt.strftime("%Y-%m-%d %H:%M"),
                "week_start": week_start, "chat_name": CHAT_NAME, "from": name, "from_id": uid,
                "text": text.strip(), "sentiment_label": label, "sentiment_score": str(score_for(label, rng)),
                "is_reply": "TRUE" if rng.random() < 0.22 else "FALSE", "top_complaints": "",
            })
            stats[label] += 1
            msg_id += 1
        if max_rows is not None and msg_id > max_rows:
            break

    for row in rows_buffer:
        themes = week_neg_themes.get(row["week_start"], [])
        if themes:
            top = [t for t, _ in Counter(themes).most_common(5)]
            row["top_complaints"] = "|".join(top)

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
        "pos_themes": pos_theme_counts.most_common(7),
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
    print("Top positive themes:", info["pos_themes"])


if __name__ == "__main__":
    main()
