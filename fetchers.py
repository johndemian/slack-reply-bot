"""
Content fetchers for X.com and Reddit posts.
Extracts post text, author info, and thread context.
"""

import re
import requests
from dataclasses import dataclass


@dataclass
class PostContent:
    platform: str          # "x" or "reddit"
    url: str
    author: str
    author_bio: str        # X bio or Reddit flair - empty string if unavailable
    content: str           # the main post text
    thread_context: str    # replies, comments, or parent chain
    subreddit: str         # only for Reddit - empty string for X
    engagement: str        # likes, retweets, upvotes - rough signal of reach


# ---------------------------------------------------------------------------
# URL detection
# ---------------------------------------------------------------------------

URL_PATTERN = re.compile(
    r"https?://(?:www\.)?"
    r"(?:twitter\.com|x\.com|reddit\.com|old\.reddit\.com)"
    r"/\S+"
)


def extract_url(text: str) -> str | None:
    """Pull the first X or Reddit URL from a block of text."""
    match = URL_PATTERN.search(text)
    return match.group(0) if match else None


def detect_platform(url: str) -> str | None:
    """Return 'x', 'reddit', or None."""
    if "twitter.com" in url or "x.com" in url:
        return "x"
    if "reddit.com" in url:
        return "reddit"
    return None


# ---------------------------------------------------------------------------
# X / Twitter fetcher (via FxTwitter - free, no auth)
# ---------------------------------------------------------------------------

def _extract_tweet_id(url: str) -> str | None:
    """Extract the tweet/post ID from an X.com URL."""
    match = re.search(r"/status/(\d+)", url)
    return match.group(1) if match else None


def _extract_username(url: str) -> str | None:
    """Extract the username from an X.com URL."""
    match = re.search(r"(?:twitter\.com|x\.com)/(\w+)/status", url)
    return match.group(1) if match else None


def fetch_x_post(url: str) -> PostContent:
    """
    Fetch a tweet via FxTwitter's free API (api.fxtwitter.com).
    No API key needed. Returns tweet text, author info, and engagement.
    Falls back to Twitter's oEmbed endpoint if FxTwitter is down.
    """
    tweet_id = _extract_tweet_id(url)
    username = _extract_username(url)
    if not tweet_id:
        raise ValueError(f"Could not extract tweet ID from URL: {url}")

    # --- Primary: FxTwitter API ---
    try:
        fx_url = f"https://api.fxtwitter.com/{username or 'i'}/status/{tweet_id}"
        resp = requests.get(fx_url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        tweet = data.get("tweet", {})
        author_data = tweet.get("author", {})

        # Engagement
        likes = tweet.get("likes", 0)
        retweets = tweet.get("retweets", 0)
        replies = tweet.get("replies", 0)
        engagement = f"{likes} likes, {retweets} retweets, {replies} replies"

        # Thread context: if it's a reply or part of a thread, the quote
        # or replied-to tweet may be included
        thread_parts = []
        if tweet.get("replying_to"):
            thread_parts.append(
                f"(replying to @{tweet['replying_to']})"
            )
        if tweet.get("quote"):
            q = tweet["quote"]
            q_author = q.get("author", {}).get("screen_name", "unknown")
            thread_parts.append(f"Quoted @{q_author}: {q.get('text', '')}")

        return PostContent(
            platform="x",
            url=url,
            author=f"@{author_data.get('screen_name', username or 'unknown')} ({author_data.get('name', '')})",
            author_bio=author_data.get("description", ""),
            content=tweet.get("text", ""),
            thread_context="\n\n".join(thread_parts),
            subreddit="",
            engagement=engagement,
        )
    except Exception:
        pass  # fall through to oEmbed

    # --- Fallback: Twitter oEmbed (official, free, unauthenticated) ---
    try:
        oembed_url = (
            f"https://publish.twitter.com/oembed"
            f"?url=https://twitter.com/{username or 'i'}/status/{tweet_id}"
            f"&omit_script=true"
        )
        resp = requests.get(oembed_url, timeout=15)
        resp.raise_for_status()
        oembed = resp.json()

        # oEmbed returns HTML - extract the text between <p> tags
        html = oembed.get("html", "")
        # Rough extraction: strip tags to get the tweet text
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        author_name = oembed.get("author_name", "unknown")

        return PostContent(
            platform="x",
            url=url,
            author=f"@{username or 'unknown'} ({author_name})",
            author_bio="",  # oEmbed doesn't include bio
            content=text,
            thread_context="",  # oEmbed doesn't include thread
            subreddit="",
            engagement="(engagement data unavailable via oEmbed)",
        )
    except Exception as e:
        raise ValueError(
            f"Could not fetch tweet from either FxTwitter or oEmbed: {e}"
        )


# ---------------------------------------------------------------------------
# Reddit fetcher (public JSON API - no auth needed)
# ---------------------------------------------------------------------------

def _normalize_reddit_url(url: str) -> str:
    """Ensure the URL uses www.reddit.com (needed for JSON endpoint)."""
    url = url.split("?")[0].rstrip("/")  # strip query params and trailing slash
    url = url.replace("old.reddit.com", "www.reddit.com")
    return url


def fetch_reddit_thread(url: str) -> PostContent:
    """
    Fetch a Reddit post and top comments using the public JSON API.
    No API key needed - just append .json to the URL.
    """
    import time

    clean_url = _normalize_reddit_url(url)
    json_url = f"{clean_url}.json"

    headers = {"User-Agent": "kimchi-reply-bot/1.0 (Python requests)"}
    data = None

    for attempt in range(3):
        resp = requests.get(json_url, headers=headers, timeout=15)
        if resp.status_code == 429:
            wait_time = 2 ** attempt
            time.sleep(wait_time)
            continue
        resp.raise_for_status()
        data = resp.json()
        break

    if data is None:
        raise ValueError(f"Failed to fetch Reddit post after 3 attempts (rate limited)")

    # data[0] = the post, data[1] = the comments
    post_data = data[0]["data"]["children"][0]["data"]
    comments_data = data[1]["data"]["children"] if len(data) > 1 else []

    # Extract post info
    author = post_data.get("author", "unknown")
    subreddit = post_data.get("subreddit", "unknown")
    title = post_data.get("title", "")
    selftext = post_data.get("selftext", "")
    score = post_data.get("score", 0)
    num_comments = post_data.get("num_comments", 0)
    author_flair = post_data.get("author_flair_text", "") or ""

    content = f"{title}\n\n{selftext}" if selftext else title

    # Extract top comments (up to 8)
    comment_lines = []
    for c in comments_data[:8]:
        if c.get("kind") != "t1":
            continue
        c_data = c["data"]
        c_author = c_data.get("author", "unknown")
        c_body = c_data.get("body", "")
        c_score = c_data.get("score", 0)
        comment_lines.append(
            f"u/{c_author} ({c_score} pts): {c_body}"
        )

    thread_context = "\n\n---\n\n".join(comment_lines)

    return PostContent(
        platform="reddit",
        url=url,
        author=f"u/{author}",
        author_bio=author_flair,
        content=content,
        thread_context=thread_context,
        subreddit=f"r/{subreddit}",
        engagement=f"{score} upvotes, {num_comments} comments",
    )


# ---------------------------------------------------------------------------
# Unified fetch
# ---------------------------------------------------------------------------

def fetch_post(url: str) -> PostContent:
    """
    Detect platform and fetch post content.
    No API keys needed - uses free public endpoints for both platforms.
    Raises ValueError if the URL isn't recognized.
    """
    platform = detect_platform(url)

    if platform == "x":
        return fetch_x_post(url)

    if platform == "reddit":
        return fetch_reddit_thread(url)

    raise ValueError(f"Unsupported URL - expected X.com or Reddit link: {url}")
