#!/usr/bin/env python3
"""One-off script: generate today's posts from manually curated articles (RSS feeds unavailable)."""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from datetime import datetime
from config import CST, POSTS_PER_DAY
from claude_client import generate_posts, select_top_posts
from main import setup_logging, save_posts_to_file
from fetcher import save_posted_url

import logging

setup_logging()
logger = logging.getLogger(__name__)

today = datetime.now(CST).strftime("%Y-%m-%d")

articles = [
    {
        "title": "Ken Paxton defeats John Cornyn in Texas U.S. Senate GOP primary runoff",
        "summary": "Attorney General Ken Paxton won the Republican primary runoff for U.S. Senate on May 26 with 64% of the vote, ending Sen. John Cornyn's three-decade electoral dominance. Trump endorsed Paxton seven days before the runoff. Cornyn became the first Republican Senator in Texas history to lose renomination. The general election will be Paxton vs. Democratic state Rep. James Talarico.",
        "url": "https://www.texastribune.org/2026/05/26/texas-john-cornyn-ken-paxton-us-senate-republican-primary-runoff/",
        "source": "Texas Tribune",
        "pub_date": None,
    },
    {
        "title": "Spirit Airlines Shuts Down After 34 Years, Blames Higher Oil Prices",
        "summary": "Spirit Airlines announced it has gone out of business after 34 years. The ultralow cost airline that employed about 17,000 people cited high oil prices driven by the war with Iran. Jet fuel costs climbed to about $4.51 per gallon by the end of April, far exceeding their restructuring plan assumptions. The final Spirit flight landed at Dallas Fort Worth International Airport from Detroit.",
        "url": "https://www.usnews.com/news/business/articles/2026-05-02/spirit-airlines-appears-closer-to-a-shutdown-as-time-dwindles-for-a-government-bailout",
        "source": "US News",
        "pub_date": None,
    },
    {
        "title": "Memorial Day Holiday Travel Boom: 1.6 Million Passengers Expected At DFW Alone",
        "summary": "DFW Airport expects approximately 1.6 million passengers between May 21 and May 26, a 5.8% increase from last year. Officials said the busiest days are Thursday, Friday, and Monday, with heaviest congestion during late-morning hours (9-11 AM) and evenings (6-8 PM). Roadway changes tied to the International Parkway Project add complexity ahead of the holiday rush.",
        "url": "https://dallasexpress.com/metroplex/memorial-day-holiday-travel-boom-1-6-million-passengers-expected-at-dfw-alone/",
        "source": "Dallas Express",
        "pub_date": None,
    },
    {
        "title": "All graduates at Barack Obama Male Leadership Academy earned college scholarships",
        "summary": "Every senior in the Class of 2026 at Barack Obama Male Leadership Academy in Dallas was accepted into college and earned a scholarship. The 54 graduating seniors earned scholarships totaling more than $15 million to institutions including Princeton and the University of Chicago. It is rare for a graduating class to have 100% college acceptance and scholarship offers.",
        "url": "https://www.fox4news.com/news/all-graduates-dallas-isd-school-earned-college-scholarship",
        "source": "FOX 4 DFW",
        "pub_date": None,
    },
    {
        "title": "KFC relocates U.S. headquarters from Kentucky to Plano, Texas",
        "summary": "KFC is moving its U.S. corporate headquarters from Louisville, Kentucky to Plano, Texas. Around 100 U.S. employees will relocate over six months, with another 90 remote workers required to move within 18 months. KFC's national headquarters will share space with the KFC and Pizza Hut Global Headquarters already in Plano.",
        "url": "https://www.fox4news.com/news/kfc-headquarters-plano",
        "source": "FOX 4 DFW",
        "pub_date": None,
    },
    {
        "title": "UTA Expert: DFW Housing Market Hits Turning Point",
        "summary": "After years of rapid growth, the Dallas-Fort Worth housing market is entering a period of transition. High interest rates, affordability pressures and global economic uncertainty are reshaping housing demand. Median home prices are down across much of the metroplex. The income needed to buy at the median is $109,242 compared to a metro median household income of $87,155.",
        "url": "https://www.uta.edu/news/news-releases/2026/03/06/uta-expert-dfw-housing-market-hits-turning-point",
        "source": "UTA News",
        "pub_date": None,
    },
    {
        "title": "DFW Airport Opens $130 Million Emergency Response Facility",
        "summary": "Dallas Fort Worth International Airport opened a new $130 million emergency response facility featuring hybrid aircraft rescue vehicles for faster deployment. The facility uses fluorine-free firefighting foam technology aligned with evolving global aviation safety regulations and newer environmental standards.",
        "url": "https://www.travelandtourworld.com/news/article/dallas-fort-worth-airport-opens-one-hundred-thirty-million-dollar-emergency-response-facility-as-americas-aviation-safety-standards-enter-a-new-era/",
        "source": "Travel And Tour World",
        "pub_date": None,
    },
    {
        "title": "North Texas thunderstorms and flash flood warning disrupt Memorial Day travel",
        "summary": "Thunderstorms and a flash flood warning across the Metroplex prompted ground stops at Dallas airports. A Flash Flood Warning was issued for most of North Texas with heavy rain, strong winds, and quarter-size hail. American Airlines experienced thousands of delays at its DFW hub due to the severe weather.",
        "url": "https://www.wfaa.com/article/news/local/dfw-airport-flight-status-outages/287-face8f8e-1e61-4746-b623-cfffad775c46",
        "source": "WFAA",
        "pub_date": None,
    },
    {
        "title": "North Texas restaurants feeling effects of higher costs from Iran War",
        "summary": "Restaurants in North Texas are struggling with rising costs linked to the Iran War and higher oil prices. Over 75% of restaurant owners in the state report increased costs. The impact is being felt across the DFW dining industry as supply chain costs and food prices continue to climb.",
        "url": "https://www.wfaa.com/",
        "source": "WFAA",
        "pub_date": None,
    },
    {
        "title": "Dallas-Fort Worth keeps title of No. 1 real estate market to watch for second year",
        "summary": "Dallas-Fort Worth has been ranked the No. 1 market to watch for the second consecutive year according to the 2026 Emerging Trends in Real Estate report using survey responses from 1,700 real estate executives. DFW's economy is anchored by financial services, technology, healthcare, logistics, and corporate headquarters with over 120 corporate relocations in the last five years.",
        "url": "https://www.wfaa.com/article/money/dallas-fort-worth-real-estate-1-market-to-watch-new-report/287-f72ea999-e69d-4f74-a331-7d82e37156c9",
        "source": "WFAA",
        "pub_date": None,
    },
]

logger.info("=" * 60)
logger.info("Running with %d manually curated articles for %s", len(articles), today)
logger.info("=" * 60)

logger.info("--- Generating Japanese posts ---")
posts = generate_posts(articles)
if not posts:
    logger.warning("No posts generated. Exiting.")
    sys.exit(1)

logger.info("--- Selecting top %d posts ---", POSTS_PER_DAY)
top_posts = select_top_posts(posts, n=POSTS_PER_DAY)

logger.info("--- Saving to output file ---")
out_path = save_posts_to_file(top_posts, today)
logger.info("Saved %d posts to %s", len(top_posts), out_path)

for i, p in enumerate(top_posts, 1):
    logger.info("  %d. [%s] %s", i, p["article"]["source"], p["text"][:100])

for p in top_posts:
    save_posted_url(p["article"]["url"])

logger.info("Done.")
