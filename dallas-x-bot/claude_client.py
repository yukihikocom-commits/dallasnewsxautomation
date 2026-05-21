"""All Claude API interactions: filtering, post generation, and top-5 selection."""

import json
import logging
import os
import re
import time

import anthropic

from config import (
    CLAUDE_MODEL,
    FILTER_BATCH_SIZE,
    FIXED_HASHTAGS,
    POSTS_PER_DAY,
    RELEVANT_TOPICS,
)

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def _call_claude(prompt: str, max_tokens: int = 2048) -> str:
    client = get_client()
    for attempt in range(3):
        try:
            response = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except anthropic.RateLimitError:
            wait = 2 ** (attempt + 2)
            logger.warning("Rate limit hit, waiting %ds (attempt %d/3)", wait, attempt + 1)
            time.sleep(wait)
        except anthropic.APIError as e:
            logger.error("Claude API error: %s", e)
            if attempt == 2:
                raise
            time.sleep(2)
    return ""


def _extract_json(text: str) -> str:
    """Pull the first JSON array or object from a Claude response."""
    match = re.search(r"(\[[\s\S]*?\]|\{[\s\S]*?\})", text)
    return match.group(1) if match else text.strip()


# ---------------------------------------------------------------------------
# Step 1: Filter articles for DFW relevance
# ---------------------------------------------------------------------------

def _filter_batch(articles: list[dict]) -> list[int]:
    """Return 0-based indices (within this batch) of relevant articles."""
    topics_str = ", ".join(RELEVANT_TOPICS)
    items = "\n".join(
        f'{i}. [{a["source"]}] {a["title"]} — {a["summary"][:200]}'
        for i, a in enumerate(articles)
    )
    prompt = f"""You are a news editor who curates Dallas/DFW-area news for a Japanese-language X (Twitter) account.

Review the following articles and return the indices (0-based integers) of articles that are clearly relevant to the Dallas/DFW metropolitan area AND cover at least one of these topics:
{topics_str}

Rules:
- Include articles that are specifically about Dallas, Fort Worth, Plano, Frisco, McKinney, Allen, Irving, Arlington, Garland, or the broader DFW metro area.
- Exclude national/international news that only mentions Dallas in passing.
- Exclude opinion pieces, listicles, and sponsored content.
- Exclude sports news, entertainment, and celebrity news.

Articles:
{items}

Respond with ONLY a JSON array of the relevant indices. Example: [0, 2, 5]
If none are relevant, respond with: []"""

    raw = _call_claude(prompt, max_tokens=512)
    try:
        indices = json.loads(_extract_json(raw))
        return [int(i) for i in indices if 0 <= int(i) < len(articles)]
    except (json.JSONDecodeError, ValueError):
        logger.warning("Could not parse filter response: %s", raw[:200])
        return []


def filter_articles(articles: list[dict]) -> list[dict]:
    """Filter articles to only DFW-relevant ones using Claude."""
    if not articles:
        return []

    relevant: list[dict] = []
    for batch_start in range(0, len(articles), FILTER_BATCH_SIZE):
        batch = articles[batch_start : batch_start + FILTER_BATCH_SIZE]
        indices = _filter_batch(batch)
        for i in indices:
            relevant.append(batch[i])
        logger.info(
            "Filter batch %d-%d: %d/%d relevant",
            batch_start,
            batch_start + len(batch) - 1,
            len(indices),
            len(batch),
        )

    logger.info("Total relevant articles after filtering: %d", len(relevant))
    return relevant


# ---------------------------------------------------------------------------
# Step 2: Generate a Japanese X post for each article
# ---------------------------------------------------------------------------

_PLANO_RE = re.compile(r"プラノ", re.IGNORECASE)

def _fix_plano(text: str) -> str:
    return _PLANO_RE.sub("プレーノ", text)


def generate_post(article: dict) -> str | None:
    """Generate a Japanese X post for a single article. Returns None on failure."""
    prompt = f"""あなたはダラス/DFWエリアに住む、または移住を検討している日本人向けのX（Twitter）アカウントを運営しています。

以下のニュース記事について、日本語でXの投稿文を1つ作成してください。

【記事情報】
ソース: {article["source"]}
タイトル: {article["title"]}
概要: {article["summary"]}
URL: {article["url"]}

【投稿のルール】
1. 文字数は必ず140文字以内（URLと末尾のハッシュタグを含む）
2. 日本語で書く（ですます調を使用）
3. ダラス/DFWに住む・移住を検討している日本人が「これは知りたい」と思う内容を簡潔に伝える
4. 記事のURLをそのまま含める（短縮しない）
5. 投稿の最後に必ず「{FIXED_HASHTAGS}」を付ける
6. 太字（**text**）は使わない
7. 「〜をご紹介します」「〜についてお知らせします」などのAIっぽい冒頭表現は使わない
8. 地名「Plano」は「プレーノ」と表記する（「プラノ」は不可）
9. URLとハッシュタグは日本語テキストの後に改行して配置する

投稿文のみを出力してください（前置きや説明は不要）。"""

    raw = _call_claude(prompt, max_tokens=300).strip()
    if not raw:
        return None

    raw = _fix_plano(raw)

    # Enforce 140-char limit as a safety net (Claude usually complies)
    if len(raw) > 140:
        logger.warning("Post exceeded 140 chars (%d), article: %s", len(raw), article["title"][:60])

    return raw


def generate_posts(articles: list[dict]) -> list[dict]:
    """Generate posts for all relevant articles. Returns list of post dicts."""
    posts = []
    for article in articles:
        text = generate_post(article)
        if text:
            posts.append({"text": text, "article": article})
            logger.info("  Generated post for: %s", article["title"][:70])
        else:
            logger.warning("  Failed to generate post for: %s", article["title"][:70])
    logger.info("Generated %d posts from %d articles", len(posts), len(articles))
    return posts


# ---------------------------------------------------------------------------
# Step 3: Select the top N most newsworthy posts
# ---------------------------------------------------------------------------

def select_top_posts(posts: list[dict], n: int = POSTS_PER_DAY) -> list[dict]:
    """Use Claude to pick the n most newsworthy posts for the day."""
    if len(posts) <= n:
        return posts

    items = "\n".join(
        f'{i}. {p["text"][:120]}'
        for i, p in enumerate(posts)
    )
    prompt = f"""You are a news editor for a Japanese-language Dallas/DFW news X account.

From the following {len(posts)} draft posts, select the {n} most newsworthy and interesting ones for Japanese readers who live in or are considering moving to the Dallas area.

Prioritize:
- Hard news over soft news
- Topics with direct impact on daily life (economy, real estate, safety, jobs)
- Variety (avoid picking multiple posts on the same story)
- Significant events over routine updates

Draft posts:
{items}

Respond with ONLY a JSON array of the {n} selected indices (0-based). Example: [0, 3, 7, 12, 18]"""

    raw = _call_claude(prompt, max_tokens=128)
    try:
        indices = json.loads(_extract_json(raw))
        selected = [posts[int(i)] for i in indices if 0 <= int(i) < len(posts)]
        if len(selected) != n:
            logger.warning("Selection returned %d posts instead of %d; using first %d", len(selected), n, n)
            selected = (selected + posts)[:n]
        logger.info("Selected top %d posts from %d candidates", len(selected), len(posts))
        return selected
    except (json.JSONDecodeError, ValueError, IndexError) as e:
        logger.warning("Could not parse selection response (%s), falling back to first %d", e, n)
        return posts[:n]
