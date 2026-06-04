import urllib.parse

import pytz

CLAUDE_MODEL = "claude-sonnet-4-6"
CST = pytz.timezone("America/Chicago")


# ---------------------------------------------------------------------------
# News source: Google News RSS search
# ---------------------------------------------------------------------------
# Direct local-news RSS feeds (dallasnews.com, wfaa.com, nbcdfw.com, etc.)
# block automated requests with HTTP 403 / dead DNS, so we pull from Google
# News RSS instead. Google News aggregates those same outlets, returns clean
# RSS 2.0, includes a per-article <source> publisher, and rarely bot-blocks.
#
# The `when:Nd` operator limits results to the last N days, so every run
# returns *fresh* articles for that day rather than a static list.

def _gnews_url(query: str) -> str:
    """Build a Google News RSS search URL for the given query."""
    params = urllib.parse.urlencode(
        {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}
    )
    return f"https://news.google.com/rss/search?{params}"


# Each "feed" is a targeted Google News query. Multiple queries widen topic
# coverage; the fetcher deduplicates by URL and Claude filters for relevance.
RSS_FEEDS = [
    {
        "name": "Google News: DFW general",
        "url": _gnews_url('("Dallas" OR "Fort Worth" OR "DFW" OR "North Texas") when:2d'),
    },
    {
        "name": "Google News: DFW economy & business",
        "url": _gnews_url('("Dallas" OR "Fort Worth" OR "DFW") (economy OR business OR jobs OR headquarters OR relocation) when:2d'),
    },
    {
        "name": "Google News: DFW real estate",
        "url": _gnews_url('("Dallas" OR "Fort Worth" OR "DFW") ("real estate" OR housing OR "office market") when:2d'),
    },
    {
        "name": "Google News: DFW weather & transit",
        "url": _gnews_url('("Dallas" OR "Fort Worth" OR "DFW") (weather OR storm OR airport OR DART OR transportation OR infrastructure) when:2d'),
    },
]

# Topics used to filter for relevant articles
RELEVANT_TOPICS = [
    "economy",
    "population",
    "DFW cities",
    "office market",
    "commercial real estate",
    "corporate relocations",
    "headquarters moves",
    "employment",
    "unemployment",
    "wages",
    "labor market",
    "statistics",
    "real estate",
    "housing market",
    "weather",
    "natural events",
    "law",
    "regulations",
    "public safety",
    "technology",
    "innovation",
    "startups",
    "infrastructure",
    "transportation",
    "demographics",
]

# How many posts to select per day
POSTS_PER_DAY = 5

# Output directory for daily post files
OUTPUT_DIR = "output"

# Max articles to fetch per feed per run
MAX_ARTICLES_PER_FEED = 30

# Max age of articles to consider (hours) — aligned with the `when:2d`
# freshness operator in the Google News queries above.
MAX_ARTICLE_AGE_HOURS = 48

# Batch size when sending articles to Claude for filtering
FILTER_BATCH_SIZE = 25

# Path for tracking already-posted article URLs across runs
POSTED_URLS_FILE = "logs/posted_urls.json"

# Hashtags appended to every post
FIXED_HASHTAGS = "#ダラス #DFW #テキサス"
