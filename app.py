"""
Kimchi Reply Bot - Slack app that generates natural replies to social media posts.

Drop an X.com or Reddit link in any channel, mention the bot, and it will:
1. Reply with "Thinking..." immediately
2. Fetch the post content
3. Generate 2-3 reply options using Claude (in Jonno's voice)
4. Post the options back in the thread
"""

import logging
import os
import re
import threading

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import anthropic

from fetchers import extract_url, fetch_post
from prompt import SYSTEM_PROMPT, build_user_prompt

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]  # xapp-... for Socket Mode
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kimchi-reply-bot")

# ---------------------------------------------------------------------------
# Slack app
# ---------------------------------------------------------------------------

app = App(token=SLACK_BOT_TOKEN)
claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _process_mention(event: dict, say, client):
    """
    Core handler: extract URL, fetch content, call Claude, post reply.
    Runs in a background thread so Slack gets a fast ack.
    """
    text = event.get("text", "")
    channel = event["channel"]
    thread_ts = event.get("thread_ts") or event["ts"]

    # Step 1 - Extract URL from the message (or parent message in thread)
    url = extract_url(text)

    # If no URL in the mention itself, check the parent message of the thread
    if not url and event.get("thread_ts"):
        try:
            result = client.conversations_replies(
                channel=channel, ts=event["thread_ts"], limit=1
            )
            parent_text = result["messages"][0].get("text", "")
            url = extract_url(parent_text)
        except Exception as e:
            logger.warning(f"Could not fetch parent message: {e}")

    if not url:
        client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=(
                "I don't see an X.com or Reddit link in this thread. "
                "Drop a link and mention me again."
            ),
        )
        return

    # Step 2 - Post "thinking..." placeholder
    thinking_msg = client.chat_postMessage(
        channel=channel,
        thread_ts=thread_ts,
        text=":hourglass_flowing_sand: Thinking...",
    )

    try:
        # Step 3 - Fetch post content
        post = fetch_post(url)

        # Step 4 - Build prompt and call Claude
        user_prompt = build_user_prompt(
            platform=post.platform,
            author=post.author,
            author_bio=post.author_bio,
            content=post.content,
            thread_context=post.thread_context,
            subreddit=post.subreddit,
            engagement=post.engagement,
            url=post.url,
        )

        response = claude.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        reply_text = response.content[0].text

        # Step 5 - Update the "thinking..." message with the actual reply
        client.chat_update(
            channel=channel,
            ts=thinking_msg["ts"],
            text=reply_text,
        )

    except Exception as e:
        logger.error(f"Error processing {url}: {e}", exc_info=True)
        client.chat_update(
            channel=channel,
            ts=thinking_msg["ts"],
            text=f":x: Something went wrong: {e}",
        )


@app.event("app_mention")
def handle_mention(event, say, client):
    """
    Triggered when someone @mentions the bot.
    Spawns a background thread so Slack gets a fast ack (< 3s).
    """
    thread = threading.Thread(
        target=_process_mention,
        args=(event, say, client),
        daemon=True,
    )
    thread.start()


# Also handle messages in DMs (no mention needed)
@app.event("message")
def handle_dm(event, say, client):
    """Handle direct messages to the bot - same logic, no @mention needed."""
    # Only respond in DMs (im channel type)
    if event.get("channel_type") != "im":
        return
    # Ignore bot's own messages
    if event.get("bot_id"):
        return

    thread = threading.Thread(
        target=_process_mention,
        args=(event, say, client),
        daemon=True,
    )
    thread.start()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Starting Kimchi Reply Bot (Socket Mode)...")
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
