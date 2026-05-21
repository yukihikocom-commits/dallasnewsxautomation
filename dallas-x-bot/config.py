import pytz

CLAUDE_MODEL = "claude-sonnet-4-20250514"
CST = pytz.timezone("America/Chicago")

# RSS feed URLs — verify each one is live before deploying.
# Many news sites rotate or deprecate feed paths; update as needed.
RSS_FEEDS = [
    {
        "name": "Dallas Morning News",
        "url": "https://rss.dallasnews.com/",
    },
    {
        "name": "Dallas Business Journal",
        "url": "https://www.bizjournals.com/dallas/news/rss.xml",
    },
    {
        "name": "Fort Worth Star-Telegram",
        "url": "https://www.star-telegram.com/news/rss2.0.xml",
    },
    {
        "name": "Dallas Observer",
        "url": "https://www.dallasobserver.com/rss.xml",
    },
    {
        "name": "WFAA",
        "url": "https://www.wfaa.com/feeds/syndication/rss/news",
    },
    {
        "name": "NBC DFW",
        "url": "https://www.nbcdfw.com/feed/",
    },
    {
        "name": "Bisnow Dallas",
        "url": "https://www.bisnow.com/dallas/feed",
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

# How many posts to select and publish per day
POSTS_PER_DAY = 5

# Posting window in CST (24-hour)
POSTING_START_HOUR = 7   # 7:00 AM CST
POSTING_END_HOUR = 11    # 11:00 AM CST (last post at or before this)

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
