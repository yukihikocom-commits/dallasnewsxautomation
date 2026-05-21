#!/usr/bin/env python3
"""
Dallas News Bot — fetches DFW news daily and saves Japanese posts to a text file.

Crontab example (run once a day, e.g. 6:00 AM CST):
  0 6 * * * cd /path/to/dallas-x-bot && /path/to/venv/bin/python main.py >> logs/cron.log 2>&1

Output: output/YYYY-MM-DD_posts.txt
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from config import CST, OUTPUT_DIR, POSTS_PER_DAY
from fetcher import fetch_all_articles, save_posted_url
from claude_client import filter_articles, generate_posts, select_top_posts


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging(log_dir: str = "logs") -> None:
    Path(log_dir).mkdir(exist_ok=True)
    today = datetime.now(CST).strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"run_{today}.log")
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


# ---------------------------------------------------------------------------
# Output file writer
# ---------------------------------------------------------------------------

def save_posts_to_file(posts: list[dict], date_str: str) -> str:
    """Write posts to output/YYYY-MM-DD_posts.txt. Returns the file path."""
    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, f"{date_str}_posts.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"Dallas DFW 日本語投稿 — {date_str}\n")
        f.write("=" * 60 + "\n\n")
        for i, post in enumerate(posts, 1):
            f.write(f"【{i}】\n")
            f.write(post["text"] + "\n")
            f.write(f"\n出典: [{post['article']['source']}] {post['article']['title']}\n")
            f.write("-" * 60 + "\n\n")
    return out_path


# ---------------------------------------------------------------------------
# Environment validation
# ---------------------------------------------------------------------------

def check_env() -> bool:
    if not os.getenv("ANTHROPIC_API_KEY"):
        logging.getLogger(__name__).error("Missing required environment variable: ANTHROPIC_API_KEY")
        return False
    return True


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run() -> int:
    logger = logging.getLogger(__name__)
    today = datetime.now(CST).strftime("%Y-%m-%d")

    logger.info("=" * 60)
    logger.info("Dallas News Bot starting — %s CST", datetime.now(CST).strftime("%Y-%m-%d %H:%M"))
    logger.info("=" * 60)

    if not check_env():
        return 1

    # Step 1: Fetch
    logger.info("--- STEP 1: Fetching RSS feeds ---")
    articles = fetch_all_articles()
    if not articles:
        logger.warning("No articles fetched. Exiting.")
        return 0

    # Step 2: Filter
    logger.info("--- STEP 2: Filtering for DFW relevance ---")
    relevant = filter_articles(articles)
    if not relevant:
        logger.warning("No relevant articles found after filtering. Exiting.")
        return 0

    # Step 3: Generate posts
    logger.info("--- STEP 3: Generating Japanese posts ---")
    posts = generate_posts(relevant)
    if not posts:
        logger.warning("No posts generated. Exiting.")
        return 0

    # Step 4: Select top N
    logger.info("--- STEP 4: Selecting top %d posts ---", POSTS_PER_DAY)
    top_posts = select_top_posts(posts, n=POSTS_PER_DAY)

    # Step 5: Save to file
    logger.info("--- STEP 5: Saving to output file ---")
    out_path = save_posts_to_file(top_posts, today)
    logger.info("Saved %d posts to %s", len(top_posts), out_path)

    for i, p in enumerate(top_posts, 1):
        logger.info("  %d. [%s] %s", i, p["article"]["source"], p["text"][:100])

    # Track posted URLs to avoid duplicates in future runs
    for p in top_posts:
        save_posted_url(p["article"]["url"])

    logger.info("=" * 60)
    logger.info("Run complete.")
    logger.info("=" * 60)
    return 0


if __name__ == "__main__":
    setup_logging()
    sys.exit(run())
