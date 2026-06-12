"""
Community Sentiment Dashboard
Visual portfolio demo for Telegram chat sentiment analysis.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).parent
OUTPUT_DIR = ROOT / "output"
DEMO_CSV = ROOT / "demo" / "sample_output.csv"

st.set_page_config(
    page_title="Community Sentiment Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

LABEL_COLORS = {"pos": "#22c55e", "neg": "#ef4444", "neu": "#94a3b8"}
LABEL_NAMES = {"pos": "Positive", "neg": "Negative", "neu": "Neutral"}


def load_csv(source: Path | None, uploaded) -> pd.DataFrame | None:
    if uploaded is not None:
        df = pd.read_csv(uploaded)
    elif source and source.exists():
        df = pd.read_csv(source)
    else:
        return None

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    if "sentiment_label" in df.columns:
        df["sentiment_label"] = df["sentiment_label"].str.lower()
    return df


def weekly_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for week, group in df.groupby("week_start"):
        total = len(group)
        counts = group["sentiment_label"].value_counts()
        rows.append(
            {
                "week_start": week,
                "messages": total,
                "pct_pos": counts.get("pos", 0) / total,
                "pct_neg": counts.get("neg", 0) / total,
                "pct_neu": counts.get("neu", 0) / total,
                "avg_score": group["sentiment_score"].mean(),
                "top_complaints": group["top_complaints"].iloc[-1]
                if "top_complaints" in group.columns
                else "",
            }
        )
    return pd.DataFrame(rows).sort_values("week_start")


def repeat_complainers(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    neg = df[df["sentiment_label"] == "neg"]
    if neg.empty:
        return pd.DataFrame(columns=["from", "negative_messages"])
    return (
        neg.groupby("from")
        .size()
        .reset_index(name="negative_messages")
        .sort_values("negative_messages", ascending=False)
        .head(top_n)
    )


def find_latest_csv() -> Path | None:
    if not OUTPUT_DIR.exists():
        return None
    csvs = sorted(OUTPUT_DIR.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    return csvs[0] if csvs else None


def run_analysis(export_path: str, lang: str, batch_size: int) -> tuple[bool, str]:
    cmd = [
        sys.executable,
        str(ROOT / "telegram_sentiment.py"),
        "--input",
        export_path,
        "--lang",
        lang,
        "--batch-size",
        str(batch_size),
    ]
    try:
        result = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=None,
        )
        if result.returncode != 0:
            return False, result.stderr or result.stdout or "Analysis failed."
        return True, result.stdout
    except Exception as e:
        return False, str(e)


# ── Sidebar ──────────────────────────────────────────────────────────
st.sidebar.title("Community Sentiment")
st.sidebar.caption("Telegram chat analysis for community health")

data_choice = st.sidebar.radio(
    "Data source",
    ["Demo data (instant preview)", "Latest saved results", "Upload a CSV"],
    index=0,
)

uploaded = None
source_path = None

if data_choice == "Demo data (instant preview)":
    source_path = DEMO_CSV
elif data_choice == "Latest saved results":
    source_path = find_latest_csv()
    if not source_path:
        st.sidebar.warning("No results yet. Use **Run analysis** below or pick Demo data.")
else:
    uploaded = st.sidebar.file_uploader("Choose a CSV file", type=["csv"])

st.sidebar.divider()
st.sidebar.subheader("Run new analysis")
st.sidebar.caption("Point to your Telegram `result.json` export folder.")

export_path = st.sidebar.text_input(
    "Export path",
    value="/Users/kristenwagner/Downloads/ChatExport_2026-06-09/result.json",
    help="Full path to result.json from Telegram Desktop",
)
lang = st.sidebar.selectbox("Chat language", ["ko", "en"], format_func=lambda x: "Korean" if x == "ko" else "English")
batch_size = st.sidebar.select_slider("Speed vs. memory", options=[8, 16, 32], value=16)

if st.sidebar.button("Start analysis", type="primary", use_container_width=True):
    if not Path(export_path).exists():
        st.sidebar.error("File not found. Check the path to result.json.")
    else:
        with st.sidebar.status("Analyzing messages…", expanded=True) as status:
            st.sidebar.write("Large chats can take hours. Keep this window open.")
            ok, log = run_analysis(export_path, lang, batch_size)
            if ok:
                status.update(label="Analysis complete!", state="complete")
                st.sidebar.success("Done! Switch to **Latest saved results** to view.")
                st.cache_data.clear()
            else:
                status.update(label="Analysis failed", state="error")
                st.sidebar.error(log[:500])

st.sidebar.divider()
with st.sidebar.expander("About this project"):
    st.markdown(
        """
        **What it does**
        - Parses Telegram chat exports
        - Scores sentiment with HuggingFace models (KR-FinBert for Korean)
        - Surfaces weekly complaint themes and repeat negative voices

        **Built with:** Python, Transformers, scikit-learn, Streamlit, Plotly

        **Privacy:** Runs locally on your machine. No data is sent to a server.
        """
    )

# ── Load data ────────────────────────────────────────────────────────
df = load_csv(source_path, uploaded)

st.title("Community Sentiment Intelligence")
st.markdown(
    "Track community mood over time, spot complaint patterns, and quantify "
    "sentiment trends from Telegram chat exports."
)

if df is None or df.empty:
    st.info(
        "👈 Pick **Demo data** in the sidebar for an instant preview, "
        "or run an analysis on your Telegram export."
    )
    st.stop()

chat_name = df["chat_name"].iloc[0] if "chat_name" in df.columns else "Community Chat"
date_min = df["date"].min().strftime("%b %Y")
date_max = df["date"].max().strftime("%b %Y")

# ── Filters ──────────────────────────────────────────────────────────
col_f1, col_f2 = st.columns([2, 1])
with col_f1:
    st.caption(f"**{chat_name}** · {len(df):,} messages · {date_min} – {date_max}")
with col_f2:
    date_range = st.date_input(
        "Filter dates",
        value=(df["date"].min().date(), df["date"].max().date()),
        min_value=df["date"].min().date(),
        max_value=df["date"].max().date(),
    )

if len(date_range) == 2:
    start, end = date_range
    df = df[(df["date"].dt.date >= start) & (df["date"].dt.date <= end)]

weekly = weekly_summary(df)
total = len(df)
counts = df["sentiment_label"].value_counts()

# ── KPI row ──────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Messages", f"{total:,}")
k2.metric("Positive", f"{counts.get('pos', 0) / total * 100:.1f}%")
k3.metric("Negative", f"{counts.get('neg', 0) / total * 100:.1f}%")
k4.metric("Neutral", f"{counts.get('neu', 0) / total * 100:.1f}%")
k5.metric("Weeks tracked", f"{df['week_start'].nunique()}")

st.divider()

# ── Charts ───────────────────────────────────────────────────────────
tab_trends, tab_weekly, tab_people, tab_messages = st.tabs(
    ["Trends", "Weekly complaints", "Voices", "Message log"]
)

with tab_trends:
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Sentiment mix")
        mix = pd.DataFrame(
            {
                "sentiment": [LABEL_NAMES.get(k, k) for k in counts.index],
                "count": counts.values,
                "color": [LABEL_COLORS.get(k, "#888") for k in counts.index],
            }
        )
        fig_mix = px.pie(
            mix,
            values="count",
            names="sentiment",
            color="sentiment",
            color_discrete_map={
                "Positive": LABEL_COLORS["pos"],
                "Negative": LABEL_COLORS["neg"],
                "Neutral": LABEL_COLORS["neu"],
            },
            hole=0.45,
        )
        fig_mix.update_layout(margin=dict(t=20, b=20), showlegend=True, height=360)
        st.plotly_chart(fig_mix, use_container_width=True)

    with c2:
        st.subheader("Negative share over time")
        if not weekly.empty:
            fig_neg = px.area(
                weekly,
                x="week_start",
                y="pct_neg",
                labels={"week_start": "Week", "pct_neg": "Negative %"},
                color_discrete_sequence=["#ef4444"],
            )
            fig_neg.update_layout(
                yaxis_tickformat=".0%",
                margin=dict(t=20, b=20),
                height=360,
            )
            st.plotly_chart(fig_neg, use_container_width=True)

    st.subheader("Average sentiment score by week")
    if not weekly.empty:
        fig_score = go.Figure()
        fig_score.add_trace(
            go.Scatter(
                x=weekly["week_start"],
                y=weekly["avg_score"],
                mode="lines+markers",
                line=dict(color="#6366f1", width=2),
                fill="tozeroy",
                fillcolor="rgba(99,102,241,0.1)",
            )
        )
        fig_score.add_hline(y=0.5, line_dash="dot", line_color="#94a3b8")
        fig_score.update_layout(
            xaxis_title="Week",
            yaxis_title="Avg confidence score",
            margin=dict(t=20, b=20),
            height=380,
        )
        st.plotly_chart(fig_score, use_container_width=True)

with tab_weekly:
    st.subheader("Weekly complaint themes")
    st.caption("Keywords extracted from negative messages each week (TF-IDF).")

    if not weekly.empty:
        display_weekly = weekly[["week_start", "messages", "pct_neg", "top_complaints"]].copy()
        display_weekly["pct_neg"] = display_weekly["pct_neg"].map(lambda x: f"{x:.1%}")
        display_weekly.columns = ["Week", "Messages", "Negative %", "Top complaint themes"]
        st.dataframe(display_weekly, use_container_width=True, hide_index=True)

        st.subheader("Message volume by week")
        fig_vol = px.bar(
            weekly,
            x="week_start",
            y="messages",
            labels={"week_start": "Week", "messages": "Messages"},
            color_discrete_sequence=["#6366f1"],
        )
        fig_vol.update_layout(margin=dict(t=20, b=20), height=320)
        st.plotly_chart(fig_vol, use_container_width=True)

with tab_people:
    st.subheader("Most frequent negative voices")
    st.caption("Members with the highest count of negative-sentiment messages.")

    complainers = repeat_complainers(df)
    if complainers.empty:
        st.write("No negative messages in this date range.")
    else:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.dataframe(complainers, use_container_width=True, hide_index=True)
        with c2:
            fig_people = px.bar(
                complainers,
                x="negative_messages",
                y="from",
                orientation="h",
                labels={"from": "Member", "negative_messages": "Negative messages"},
                color_discrete_sequence=["#ef4444"],
            )
            fig_people.update_layout(
                yaxis=dict(autorange="reversed"),
                margin=dict(t=20, b=20),
                height=max(280, len(complainers) * 36),
            )
            st.plotly_chart(fig_people, use_container_width=True)

with tab_messages:
    st.subheader("Search messages")
    search = st.text_input("Search text", placeholder="e.g. bug, delay, help…")
    sentiment_filter = st.multiselect(
        "Sentiment",
        ["pos", "neg", "neu"],
        default=["pos", "neg", "neu"],
        format_func=lambda x: LABEL_NAMES[x],
    )

    view = df[df["sentiment_label"].isin(sentiment_filter)].copy()
    if search:
        view = view[view["text"].str.contains(search, case=False, na=False)]

    display_cols = [
        c
        for c in [
            "date",
            "from",
            "sentiment_label",
            "sentiment_score",
            "text",
            "week_start",
        ]
        if c in view.columns
    ]
    st.dataframe(
        view[display_cols].sort_values("date", ascending=False).head(500),
        use_container_width=True,
        hide_index=True,
    )
    if len(view) > 500:
        st.caption(f"Showing 500 of {len(view):,} matching messages.")
