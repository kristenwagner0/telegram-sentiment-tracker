"""Google Sheets sync: append messages with dedup and upsert weekly summaries."""

from __future__ import annotations

import os
from pathlib import Path

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
MESSAGES_SHEET = "Messages"
WEEKLY_SHEET = "WeeklySummary"

MESSAGES_HEADERS = [
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

WEEKLY_HEADERS = [
    "week_start",
    "chat_name",
    "message_count",
    "pct_pos",
    "pct_neg",
    "pct_neu",
    "avg_sentiment_score",
    "top_complaints",
]


def _expand_path(path: str) -> str:
    return str(Path(path).expanduser())


def get_client(credentials_path: str) -> gspread.Client:
    creds = Credentials.from_service_account_file(
        _expand_path(credentials_path),
        scopes=SCOPES,
    )
    return gspread.authorize(creds)


def _ensure_worksheet(
    spreadsheet: gspread.Spreadsheet,
    title: str,
    headers: list[str],
) -> gspread.Worksheet:
    try:
        ws = spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=title, rows=1000, cols=len(headers))
        ws.append_row(headers)
        return ws

    existing = ws.row_values(1)
    if not existing:
        ws.append_row(headers)
    elif existing != headers:
        ws.update("A1", [headers])
    return ws


def _existing_msg_ids(ws: gspread.Worksheet) -> set[str]:
    records = ws.get_all_records()
    if not records:
        return set()
    return {str(row["msg_id"]) for row in records if row.get("msg_id") != ""}


def build_weekly_summary(df: pd.DataFrame, weekly_keywords: dict) -> pd.DataFrame:
    rows = []
    for (week_start, chat_name), group in df.groupby(["week_start", "chat_name"]):
        total = len(group)
        if total == 0:
            continue
        counts = group["sentiment_label"].value_counts()
        key = (week_start, chat_name)
        complaints = weekly_keywords.get(week_start, [])
        rows.append(
            {
                "week_start": week_start,
                "chat_name": chat_name,
                "message_count": total,
                "pct_pos": round(counts.get("pos", 0) / total, 4),
                "pct_neg": round(counts.get("neg", 0) / total, 4),
                "pct_neu": round(counts.get("neu", 0) / total, 4),
                "avg_sentiment_score": round(group["sentiment_score"].mean(), 4),
                "top_complaints": " | ".join(complaints),
            }
        )
    return pd.DataFrame(rows)


def _upsert_weekly_rows(ws: gspread.Worksheet, summary: pd.DataFrame) -> int:
    if summary.empty:
        return 0

    records = ws.get_all_records()
    index: dict[tuple[str, str], int] = {}
    for i, row in enumerate(records, start=2):
        key = (str(row.get("week_start", "")), str(row.get("chat_name", "")))
        index[key] = i

    updated = 0
    to_append: list[list] = []

    for _, row in summary.iterrows():
        key = (str(row["week_start"]), str(row["chat_name"]))
        values = [row[h] for h in WEEKLY_HEADERS]
        if key in index:
            ws.update(f"A{index[key]}", [values])
            updated += 1
        else:
            to_append.append(values)

    if to_append:
        ws.append_rows(to_append, value_input_option="USER_ENTERED")

    return updated + len(to_append)


def push_to_sheets(
    df: pd.DataFrame,
    weekly_keywords: dict,
    sheet_id: str,
    credentials_path: str | None = None,
) -> tuple[int, int]:
    """
    Append new message rows (deduped by msg_id) and upsert WeeklySummary.
    Returns (messages_appended, weekly_rows_touched).
    """
    creds_path = credentials_path or os.environ.get("GOOGLE_CREDENTIALS_PATH", "")
    if not creds_path:
        raise ValueError(
            "Set GOOGLE_CREDENTIALS_PATH in .env or pass credentials_path"
        )
    if not sheet_id:
        raise ValueError("Set GOOGLE_SHEET_ID in .env or pass --sheet-id")

    client = get_client(creds_path)
    spreadsheet = client.open_by_key(sheet_id)

    messages_ws = _ensure_worksheet(spreadsheet, MESSAGES_SHEET, MESSAGES_HEADERS)
    weekly_ws = _ensure_worksheet(spreadsheet, WEEKLY_SHEET, WEEKLY_HEADERS)

    seen = _existing_msg_ids(messages_ws)
    new_rows = df[~df["msg_id"].astype(str).isin(seen)].copy()

    appended = 0
    if not new_rows.empty:
        out = new_rows[MESSAGES_HEADERS].copy()
        out["msg_id"] = out["msg_id"].astype(str)
        out["is_reply"] = out["is_reply"].map({True: "TRUE", False: "FALSE"})
        messages_ws.append_rows(
            out.values.tolist(),
            value_input_option="USER_ENTERED",
        )
        appended = len(new_rows)

    summary = build_weekly_summary(df, weekly_keywords)
    weekly_touched = _upsert_weekly_rows(weekly_ws, summary)

    return appended, weekly_touched
