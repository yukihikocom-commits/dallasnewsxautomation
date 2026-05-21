"""Post tweets to X API v2, spread across the configured posting window."""

import logging
import os
import time
from datetime import datetime

import tweepy

from config import CST, POSTING_END_HOUR, POSTING_START_HOUR, POSTS_PER_DAY

logger = logging.getLogger(__name__)


def _get_client() -> tweepy.Client:
    return tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
        wait_on_rate_limit=True,
    )


def _posting_times_today(count: int) -> list[datetime]:
    """
    Calculate evenly-spaced posting times within the window for today in CST.
    If there is only one post, schedule it at the start of the window.
    """
    now = datetime.now(CST)
    start = now.replace(hour=POSTING_START_HOUR, minute=0, second=0, microsecond=0)
    end = now.replace(hour=POSTING_END_HOUR, minute=0, second=0, microsecond=0)

    if count == 1:
        return [start]

    total_seconds = (end - start).total_seconds()
    interval = total_seconds / (count - 1)
    return [start.replace(second=0, microsecond=0).__class__.fromtimestamp(
        start.timestamp() + i * interval, tz=CST
    ) for i in range(count)]


def _wait_until(target: datetime) -> None:
    now = datetime.now(CST)
    delta = (target - now).total_seconds()
    if delta > 0:
        logger.info("  Waiting %.1f minutes until %s CST...", delta / 60, target.strftime("%H:%M"))
        time.sleep(delta)


def post_tweet(client: tweepy.Client, text: str, dry_run: bool = False) -> bool:
    if dry_run:
        logger.info("  [DRY RUN] Would post: %s", text[:80])
        return True
    try:
        response = client.create_tweet(text=text)
        tweet_id = response.data["id"]
        logger.info("  Posted tweet ID %s: %s", tweet_id, text[:80])
        return True
    except tweepy.TweepyException as e:
        logger.error("  Failed to post tweet: %s", e)
        return False


def schedule_and_post(posts: list[dict], dry_run: bool = False) -> list[dict]:
    """
    Post each item at its scheduled time. Returns list of posts that were
    successfully published, each with 'scheduled_time' added.
    """
    if not posts:
        logger.warning("No posts to schedule.")
        return []

    client = _get_client()
    times = _posting_times_today(len(posts))
    results = []

    now = datetime.now(CST)
    logger.info(
        "Scheduling %d posts between %s and %s CST (now: %s)",
        len(posts),
        times[0].strftime("%H:%M"),
        times[-1].strftime("%H:%M"),
        now.strftime("%H:%M"),
    )

    for post, scheduled_time in zip(posts, times):
        _wait_until(scheduled_time)
        success = post_tweet(client, post["text"], dry_run=dry_run)
        if success:
            post["scheduled_time"] = scheduled_time.isoformat()
            results.append(post)

    return results
