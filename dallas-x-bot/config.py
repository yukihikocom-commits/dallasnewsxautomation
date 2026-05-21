import pytz

CLAUDE_MODEL = "claude-sonnet-4-20250514"
CST = pytz.timezone("America/Chicago")

# RSS feed URLs — confirmed via search May 2026.
# If a feed stops working, check the source site's /rss or /feed page.
RSS_FEEDS = [
    {
        "name": "Dallas Morning News",
        # User-confirmed domain; if this 404s try:
        # https://www.dallasnews.com/arc/outboundfeeds/rss/?outputType=xml
        "url": "https://rss.dallasnews.com/",
    },
    {
        "name": "Dallas Business Journal",
        # Confirmed: feeds.bizjournals.com subdomain for Dallas edition
        "url": "https://feeds.bizjournals.com/bizj_dallas",
    },
    {
        "name": "Fort Worth Star-Telegram",
        # WordPress-style feed; if 404s try /news/local/rss2.0.xml
        "url": "https://www.star-telegram.com/feed/",
    },
    {
        "name": "Dallas Observer",
        # Confirmed: note capital R in Rss
        "url": "https://www.dallasobserver.com/dallas/Rss.xml",
    },
    {
        "name": "WFAA",
        # Confirmed from wfaa.com/rss — local news feed
        "url": "https://www.wfaa.com/feeds/syndication/rss/news/local",
    },
    {
        "name": "NBC DFW",
        # Confirmed from nbcdfw.com/rss page
        "url": "https://www.nbcdfw.com/news/feed/",
    },
    {
        "name": "Bisnow Dallas",
        # Bisnow does not publish a confirmed public RSS feed.
        # Remove this entry if it consistently 404s or 403s.
        "url": "https://www.bisnow.com/dallas-ft-worth/feed",
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

# Max age of articles to consider (hours)
MAX_ARTICLE_AGE_HOURS = 24

# Batch size when sending articles to Claude for filtering
FILTER_BATCH_SIZE = 25

# Path for tracking already-posted article URLs across runs
POSTED_URLS_FILE = "logs/posted_urls.json"

# Hashtags appended to every post
FIXED_HASHTAGS = "#ダラス #DFW #テキサス"
