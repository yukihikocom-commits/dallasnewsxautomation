#!/usr/bin/env python3
"""
Dallas X Bot — daily DFW news → Japanese X posts.

Crontab example (run at 7:00 AM CST every day):
  0 7 * * * cd /path/to/dallas-x-bot && /path/to/venv/bin/python main.py >> logs/cron.log 2>&1

Flags:
  --dry-run       Fetch, filter, and generate posts but do NOT post to X
  --skip-post     Alias for --dry-run
  --no-schedule   Post immediately without waiting for the posting window
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Load .env before importing modules that read env vars
load_dotenv()

from config import CST, POSTS_PER_DAY
from fetcher import fetch_all_articles, save_posted_url
from claude_client import filter_articles, generate_posts, select_top_posts
from x_poster import schedule_and_post


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging(log_dir: str = "logs") -> None:
    Path(log_dir).mkdir(exist_ok=True)
    today = datetime.now(CST).strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"run_{today}.log")

    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        datefmt=datefmt,
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


# ---------------------------------------------------------------------------
# Environment validation
# ---------------------------------------------------------------------------

REQUIRED_ENV_VARS = [
    "ANTHROPIC_API_KEY",
    "X_API_KEY",
    "X_API_SECRET",
    "X_ACCESS_TOKEN",
    "X_ACCESS_TOKEN_SECRET",
]


def check_env() -> bool:
    missing = [v for v in REQUIRED_ENV_VARS if not os.getenv(v)]
    if missing:
        logging.getLogger(__name__).error(
            "Missing required environment variables: %s", ", ".join(missing)
        )
        return False
    return True


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run(dry_run: bool = False) -> int:
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Dallas X Bot starting — %s CST", datetime.now(CST).strftime("%Y-%m-%d %H:%M"))
    logger.info("Mode: %s", "DRY RUN" if dry_run else "LIVE")
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
    logger.info("--- STEP 3: Generating Japanese X posts ---")
    posts = generate_posts(relevant)
    if not posts:
        logger.warning("No posts generated. Exiting.")
        return 0

    # Step 4: Select top N
    logger.info("--- STEP 4: Selecting top %d posts ---", POSTS_PER_DAY)
    top_posts = select_top_posts(posts, n=POSTS_PER_DAY)

    logger.info("--- Top posts selected ---")
    for i, p in enumerate(top_posts, 1):
        logger.info("  %d. [%s] %s", i, p["article"]["source"], p["text"][:100])

    # Step 5: Schedule and post
    logger.info("--- STEP 5: Posting to X ---")
    published = schedule_and_post(top_posts, dry_run=dry_run)

    # Mark URLs as posted so they are skipped in future runs
    if not dry_run:
        for p in published:
            save_posted_url(p["article"]["url"])

    logger.info("=" * 60)
    logger.info(
        "Run complete. Published %d/%d posts.",
        len(published),
        len(top_posts),
    )
    logger.info("=" * 60)
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dallas X Bot — DFW news to Japanese X posts")
    parser.add_argument(
        "--dry-run", "--skip-post",
        action="store_true",
        dest="dry_run",
        help="Run the full pipeline but do not post to X",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    setup_logging()
    sys.exit(run(dry_run=args.dry_run))
