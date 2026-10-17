"""Announce news that just landed on main (called by land-verified.yml after the push).

Usage: python scripts/announce_news.py <sha-before-landing> <sha-after-landing>

Only news files ADDED to research/news/ between the two commits are sent, so each item is
announced exactly once, and only after it passed verification and the landing gates.
Telegram credentials come from the environment (repository secrets):
  FRDA_TELEGRAM_BOT_TOKEN, FRDA_TELEGRAM_CHAT_ID  (optional FRDA_NEWS_LINK)
Missing credentials or a Telegram error never fail the landing: they are reported as
::warning:: annotations on the workflow run. Delivery is at most once: an item that failed to
send is not retried by a later landing (it was not added by it); re-send it by hand if needed.
The token is never printed, not even inside an exception message.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

from frda.news import DEFAULT_LINK, load, render_telegram, wording_problems


def added_news(before: str, after: str) -> list[Path]:
    out = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=A", before, after, "--", "research/news/"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return [Path(p) for p in out if Path(p).name.startswith("N-") and p.endswith(".md")]


def send(token: str, chat_id: str, text: str) -> bool:
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps(
            {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
        ).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return bool(json.load(resp).get("ok"))
    except Exception as exc:  # the URL holds the token: print the exception type only
        print(f"::warning::Telegram send failed: {type(exc).__name__}")
        return False


def main(before: str, after: str) -> int:
    items = added_news(before, after)
    if not items:
        print("announce: no new news item in this landing")
        return 0
    token = os.environ.get("FRDA_TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("FRDA_TELEGRAM_CHAT_ID")
    link = os.environ.get("FRDA_NEWS_LINK") or DEFAULT_LINK
    for path in items:
        try:
            meta, body = load(path)
            text = render_telegram(meta, body, link)
        except Exception as exc:  # the news gate should have caught it; never block the landing
            print(
                f"::warning::{path.name}: unreadable news item ({type(exc).__name__}), not announced"
            )
            continue
        if wording_problems(meta.title, body):  # second line of defence, after the news gate
            print(f"::warning::{meta.id}: overselling wording, not announced")
            continue
        if not token or not chat:
            print(f"::warning::{meta.id}: Telegram secrets not set, not announced")
            continue
        if send(token, chat, text):
            print(f"announce: {meta.id} -> sent")
        else:
            print(f"::warning::{meta.id}: Telegram send failed, not announced (no retry)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
