"""Fetch and deduplicate articles from configured RSS feeds.

Uses only stdlib XML parsing (no feedparser) so there are no build dependencies.
Handles both RSS 2.0 and Atom feed formats.
"""

import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

import requests

from config import (
    MAX_ARTICLE_AGE_HOURS,
    MAX_ARTICLES_PER_FEED,
    POSTED_URLS_FILE,
    RSS_FEEDS,
)

logger = logging.getLogger(__name__)

FETCH_TIMEOUT = 15

# XML namespaces commonly found in feeds
_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "media": "http://search.yahoo.com/mrss/",
}


# ---------------------------------------------------------------------------
# Persistent posted-URL tracking
# ---------------------------------------------------------------------------

def _load_posted_urls() -> set:
    if not os.path.exists(POSTED_URLS_FILE):
        return set()
    try:
        with open(POSTED_URLS_FILE) as f:
            return set(json.load(f).get("urls", []))
    except (json.JSONDecodeError, OSError):
        return set()


def save_posted_url(url: str) -> None:
    os.makedirs(os.path.dirname(POSTED_URLS_FILE), exist_ok=True)
    posted = _load_posted_urls()
    posted.add(url)
    trimmed = list(posted)[-1000:]  # cap at 1000 entries
    with open(POSTED_URLS_FILE, "w") as f:
        json.dump({"urls": trimmed}, f, indent=2)


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

def _parse_date(text: str | None) -> datetime | None:
    if not text:
        return None
    text = text.strip()
    # Try RFC 2822 (RSS pubDate)
    try:
        return parsedate_to_datetime(text).astimezone(timezone.utc).replace(tzinfo=timezone.utc)
    except Exception:
        pass
    # Try ISO 8601 (Atom published/updated)
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(text[:25], fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")

def _strip_html(text: str) -> str:
    text = _HTML_TAG_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def _text(el: ElementTree.Element | None) -> str:
    if el is None:
        return ""
    return (el.text or "").strip()


# ---------------------------------------------------------------------------
# RSS 2.0 parser
# ---------------------------------------------------------------------------

def _parse_rss(root: ElementTree.Element, source_name: str) -> list[dict]:
    articles = []
    channel = root.find("channel")
    if channel is None:
        return articles

    for item in channel.findall("item")[:MAX_ARTICLES_PER_FEED]:
        title = _strip_html(_text(item.find("title")))
        url = _text(item.find("link"))
        if not url:
            # <link> in RSS is sometimes tricky; try guid with isPermaLink
            guid = item.find("guid")
            if guid is not None and guid.get("isPermaLink", "true").lower() != "false":
                url = (guid.text or "").strip()
        if not title or not url:
            continue

        summary = (
            _text(item.find("{%s}encoded" % _NS["content"]))
            or _text(item.find("description"))
            or ""
        )
        summary = _strip_html(summary)[:500]

        pub_date = _parse_date(_text(item.find("pubDate")) or _text(item.find("{%s}date" % _NS["dc"])))

        articles.append({
            "title": title,
            "summary": summary,
            "url": url,
            "source": source_name,
            "pub_date": pub_date,
        })
    return articles


# ---------------------------------------------------------------------------
# Atom parser
# ---------------------------------------------------------------------------

def _parse_atom(root: ElementTree.Element, source_name: str) -> list[dict]:
    articles = []
    ns = _NS["atom"]

    for entry in root.findall(f"{{{ns}}}entry")[:MAX_ARTICLES_PER_FEED]:
        title_el = entry.find(f"{{{ns}}}title")
        title = _strip_html(_text(title_el))
        if not title:
            continue

        # <link rel="alternate" href="..."> preferred
        url = ""
        for link_el in entry.findall(f"{{{ns}}}link"):
            rel = link_el.get("rel", "alternate")
            if rel == "alternate":
                url = link_el.get("href", "").strip()
                break
        if not url:
            # fallback: any link element
            link_el = entry.find(f"{{{ns}}}link")
            if link_el is not None:
                url = link_el.get("href", "").strip()
        if not url:
            continue

        summary = (
            _text(entry.find(f"{{{ns}}}summary"))
            or _text(entry.find(f"{{{ns}}}content"))
            or ""
        )
        summary = _strip_html(summary)[:500]

        pub_date = _parse_date(
            _text(entry.find(f"{{{ns}}}published"))
            or _text(entry.find(f"{{{ns}}}updated"))
        )

        articles.append({
            "title": title,
            "summary": summary,
            "url": url,
            "source": source_name,
            "pub_date": pub_date,
        })
    return articles


# ---------------------------------------------------------------------------
# Feed dispatcher
# ---------------------------------------------------------------------------

def _parse_feed_xml(xml_text: str, source_name: str) -> list[dict]:
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as e:
        logger.warning("  %s: XML parse error — %s", source_name, e)
        return []

    tag = root.tag.lower()
    if "rss" in tag:
        return _parse_rss(root, source_name)
    if "feed" in tag or _NS["atom"] in tag:
        return _parse_atom(root, source_name)
    # RDF/RSS 1.0 — treat items at root level like RSS
    items = root.findall("{http://purl.org/rss/1.0/}item")
    if items:
        return _parse_rss(root, source_name)
    logger.warning("  %s: unknown feed format (root tag: %s)", source_name, root.tag)
    return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _is_recent(article: dict) -> bool:
    if article["pub_date"] is None:
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_ARTICLE_AGE_HOURS)
    return article["pub_date"] >= cutoff


def fetch_feed(feed_config: dict) -> list[dict]:
    name = feed_config["name"]
    url = feed_config["url"]
    try:
        resp = requests.get(
            url,
            timeout=FETCH_TIMEOUT,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        resp.raise_for_status()
        articles = [a for a in _parse_feed_xml(resp.text, name) if _is_recent(a)]
        logger.info("  %s: %d recent articles", name, len(articles))
        return articles
    except requests.RequestException as e:
        logger.warning("  %s: fetch failed — %s", name, e)
        return []
    except Exception as e:
        logger.warning("  %s: unexpected error — %s", name, e)
        return []


def fetch_all_articles() -> list[dict]:
    """Fetch all feeds, deduplicate by URL, exclude already-posted articles."""
    posted_urls = _load_posted_urls()
    seen: set[str] = set()
    all_articles: list[dict] = []

    for feed in RSS_FEEDS:
        for article in fetch_feed(feed):
            url = article["url"]
            if url in seen or url in posted_urls:
                continue
            seen.add(url)
            all_articles.append(article)

    all_articles.sort(
        key=lambda a: a["pub_date"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    logger.info("Total unique new articles: %d", len(all_articles))
    return all_articles
