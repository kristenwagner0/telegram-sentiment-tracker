"""Serve the SentimentTrack dashboard and proxy Google Sheets CSV (avoids browser CORS)."""

from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests
from flask import Flask, Response, jsonify, request, send_from_directory

ROOT = Path(__file__).parent
DASHBOARD = ROOT / "dashboard"

app = Flask(__name__)


def portfolio_mode() -> bool:
    return os.environ.get("PORTFOLIO_MODE", "").lower() in ("1", "true", "yes")



def normalize_sheet_url(url: str) -> str:
    """Convert edit/share links to CSV export URLs."""
    if "/export?" in url or "/pub?" in url or "output=csv" in url:
        return url

    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
    if not m:
        return url

    sheet_id = m.group(1)
    gid = "0"
    parsed = urlparse(url)
    if parsed.fragment and "gid=" in parsed.fragment:
        gid_m = re.search(r"gid=(\d+)", parsed.fragment)
        if gid_m:
            gid = gid_m.group(1)
    elif parsed.query:
        qs = parse_qs(parsed.query)
        if "gid" in qs:
            gid = qs["gid"][0]

    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def fetch_sheet_csv(url: str) -> tuple[bytes | None, str | None]:
    """Fetch CSV bytes from a Google Sheets URL. Returns (content, error)."""
    if not url or "docs.google.com" not in url:
        return None, "Provide a valid Google Sheets URL"
    if not re.match(r"^https://", url):
        return None, "URL must start with https://"

    export_url = normalize_sheet_url(url)
    try:
        resp = requests.get(export_url, timeout=120)
        resp.raise_for_status()
    except requests.RequestException as exc:
        return None, f"Could not fetch sheet: {exc}"

    content = resp.content
    head = content[:500].lower()
    if b"<html" in head or b"<!doctype" in head:
        return None, (
            "URL returned HTML, not CSV. Share the sheet as "
            "'Anyone with the link' or use File → Publish to web → CSV."
        )
    return content, None


@app.route("/")
def index():
    return send_from_directory(DASHBOARD, "index.html")


@app.route("/api/config")
def app_config():
    return jsonify({
        "portfolioMode": portfolio_mode(),
        "repoUrl": os.environ.get("GITHUB_REPO_URL", ""),
        "contactEmail": os.environ.get("CONTACT_EMAIL", ""),
    })


@app.route("/api/demo")
def demo_data():
    url = os.environ.get("DEMO_SHEET_URL", "").strip()
    if not url:
        return jsonify({"error": "DEMO_SHEET_URL is not configured on the server"}), 503

    content, err = fetch_sheet_csv(url)
    if err:
        return jsonify({"error": err}), 502

    return Response(
        content,
        mimetype="text/csv; charset=utf-8",
        headers={"Cache-Control": "public, max-age=300"},
    )


@app.route("/api/sheet")
def sheet_proxy():
    if portfolio_mode():
        return jsonify({"error": "Sheet proxy is disabled in portfolio demo mode"}), 403
    raw_url = request.args.get("url", "").strip()
    content, err = fetch_sheet_csv(raw_url)
    if err:
        code = 400 if "valid Google Sheets" in err or "https://" in err else 502
        return jsonify({"error": err}), code

    return Response(
        content,
        mimetype="text/csv; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )


@app.route("/api/translate", methods=["POST"])
def translate_proxy():
    data = request.get_json(silent=True) or {}
    texts = data.get("texts") or []
    target = data.get("target", "en")
    source = data.get("source", "ko")

    if not texts or not isinstance(texts, list):
        return jsonify({"error": "Provide texts array"}), 400

    try:
        from deep_translator import GoogleTranslator

        translator = GoogleTranslator(source=source, target=target)
        results = []
        for text in texts[:50]:
            t = str(text or "").strip()
            if not t:
                results.append("")
                continue
            try:
                results.append(translator.translate(t[:4500]))
            except Exception:
                results.append("")
        return jsonify({"translations": results})
    except Exception as exc:
        return jsonify({"error": f"Translation failed: {exc}"}), 502


@app.route("/<path:filename>")
def assets(filename):
    return send_from_directory(DASHBOARD, filename)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "127.0.0.1")
    print(f"SentimentTrack dashboard → http://{host}:{port}")
    print("Keep this window open. Press Control+C to stop.")
    app.run(host=host, port=port, debug=False, use_reloader=False)
