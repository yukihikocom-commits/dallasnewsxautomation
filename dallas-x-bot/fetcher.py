"""Fetch and deduplicate articles from configured RSS feeds."""

import json
import logging
import os
from datetime import datetime, timedelta, timezone

import feedparser
import requests

from config import (
    CST,
    MAX_ARTICLE_AGE_HOURS,
    MAX_ARTICLES_PER_FEED,
    POSTED_URLS_FILE,
    RSS_FEEDS,
)

logger = logging.getLogger(__name__)

FETCH_TIMEOUT = 15  # seconds


def _load_posted_urls() -> set:
    if not os.path.exists(POSTED_URLS_FILE):
        return set()
    try:
        with open(POSTED_URLS_FILE) as f:
            data = json.load(f)
        return set(data.get("urls", []))
    except (json.JSONDecodeError, OSError):
        return set()


def save_posted_url(url: str) -> None:
    os.makedirs(os.path.dirname(POSTED_URLS_FILE), exist_ok=True)
    posted = _load_posted_urls()
    posted.add(url)
    # Keep only the last 1000 URLs to prevent unbounded growth
    trimmed = list(posted)[-1000:]
    with open(POSTED_URLS_FILE, "w") as f:
        json.dump({"urls": trimmed}, f, indent=2)


def _parse_entry(entry: feedparser.FeedParserDict, source_name: str) -> dict | None:
    url = entry.get("link", "").strip()
    title = entry.get("title", "").strip()
    if not url or not title:
        return None

    summary = (
        entry.get("summary", "")
        or entry.get("description", "")
        or ""
    ).strip()
    # Strip HTML tags from summary crudely (feedparser usually does this, but just in case)
    import re
    summary = re.sub(r"<[^>]+>", " ", summary).strip()

    pub_date = None
    if entry.get("published_parsed"):
        pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    elif entry.get("updated_parsed"):
        pub_date = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)

    return {
        "title": title,
        "summary": summary[:500],
        "url": url,
        "source": source_name,
        "pub_date": pub_date,
    }


def _is_recent(article: dict) -> bool:
    if article["pub_date"] is None:
        return True  # keep if date unknown
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_ARTICLE_AGE_HOURS)
    return article["pub_date"] >= cutoff


def fetch_feed(feed_config: dict) -> list[dict]:
    name = feed_config["name"]
    url = feed_config["url"]
    articles = []
    try:
        # feedparser can hang on slow servers; use requests + parse from string
        response = requests.get(url, timeout=FETCH_TIMEOUT, headers={"User-Agent": "DallasXBot/1.0"})
        response.raise_for_status()
        parsed = feedparser.parse(response.text)

        for entry in parsed.entries[:MAX_ARTICLES_PER_FEED]:
            article = _parse_entry(entry, name)
            if article and _is_recent(article):
                articles.append(article)

        logger.info("  %s: fetched %d recent articles", name, len(articles))
    except requests.RequestException as e:
        logger.warning("  %s: fetch failed — %s", name, e)
    except Exception as e:
        logger.warning("  %s: unexpected error — %s", name, e)
    return articles


def fetch_all_articles() -> list[dict]:
    """Fetch from all feeds, deduplicate by URL, exclude already-posted articles."""
    posted_urls = _load_posted_urls()
    seen_urls: set[str] = set()
    all_articles: list[dict] = []

    for feed in RSS_FEEDS:
        for article in fetch_feed(feed):
            url = article["url"]
            if url in seen_urls or url in posted_urls:
                continue
            seen_urls.add(url)
            all_articles.append(article)

    # Sort newest first (None pub_date goes to the end)
    all_articles.sort(
        key=lambda a: a["pub_date"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    logger.info("Total unique unfetched articles: %d", len(all_articles))
    return all_articles
