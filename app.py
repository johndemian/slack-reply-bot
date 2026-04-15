"""
Kimchi Reply Bot - Slack app that generates natural replies to social media posts.

Drop an X.com or Reddit link in any channel, mention the bot, and it will:
1. Reply with "Thinking..." immediately
2. Fetch the post content
3. Generate 2-3 reply options using Kimchi.dev AI
4. Post the options back in the thread
"""

import logging
import os
import re
import threading
import requests

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from fetchers import extract_url, fetch_post
from prompt import SYSTEM_PROMPT, build_user_prompt

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]  # xapp-... for Socket Mode
KIMCHI_API_KEY = os.environ.get("KIMCHI_API_KEY")
KIMCHI_API_URL = os.environ.get("KIMCHI_API_URL", "https://llm.kimchi.dev/openai/v1")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kimchi-reply-bot")

logger.info(f"KIMCHI_API_URL: {KIMCHI_API_URL}")
logger.info(f"KIMCHI_API_KEY: {KIMCHI_API_KEY[:10] if KIMCHI_API_KEY else 'None'}...")

# ---------------------------------------------------------------------------
# Slack app
# ---------------------------------------------------------------------------

app = App(token=SLACK_BOT_TOKEN)


def _process_mention(event: dict, say, client):
    """
    Core handler: extract URL, fetch content, call Kimchi.dev, post reply.
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

        # Step 4 - Build prompt and call Kimchi.dev
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

        # Call Kimchi.dev API
        headers = {
            "Authorization": f"Bearer {KIMCHI_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "minimax-m2.7",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": 2048
        }

        api_url = f"{KIMCHI_API_URL}/chat/completions"
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()

        reply_text = response.json()["choices"][0]["message"]["content"]

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
# HTTP health check server (keeps Render port open)
# ---------------------------------------------------------------------------

def run_health_server():
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import threading

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')

        def log_message(self, format, *args):
            pass  # Suppress logging

    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Health check server running on port {port}")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_health_server()
    logger.info("Starting Kimchi Reply Bot (Socket Mode)...")
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
