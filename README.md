# Kimchi Reply Bot

A Slack bot that generates natural, non-salesy replies to X.com and Reddit posts - positioning [kimchi.dev](https://kimchi.dev) as a solution to LLM infrastructure pain points.

Drop a link in any Slack channel, @mention the bot, and it comes back with 2-3 reply options written in Jonno's voice. Pick one, paste it, done.

## How it works

1. Someone posts an X.com or Reddit link in Slack and @mentions the bot
2. The bot replies with "Thinking..." in the thread
3. It fetches the post content (FxTwitter for X, public JSON API for Reddit)
4. Claude analyzes the pain point and checks if kimchi.dev is a good fit
5. If it is, the bot posts 2-3 reply options at different levels of directness
6. If it's not a fit, it says so - no forced pitches

The bot also works in DMs (no @mention needed).

## Project structure

```
slack-reply-bot/
  app.py             # Slack Bolt app - event handlers and main loop
  fetchers.py        # Content fetchers for X.com and Reddit
  prompt.py          # Claude system prompt - product knowledge + writing style
  requirements.txt   # Python dependencies
  .env.example       # Environment variables template
```

## Prerequisites

You need three API tokens:

| Token | Source | Cost |
|---|---|---|
| Slack Bot Token (`xoxb-...`) | [api.slack.com/apps](https://api.slack.com/apps) | Free |
| Slack App Token (`xapp-...`) | Same Slack app (Socket Mode) | Free |
| Anthropic API Key (`sk-ant-...`) | [console.anthropic.com](https://console.anthropic.com/settings/keys) | ~$0.01-0.03 per reply |

X.com and Reddit fetching use free public endpoints - no API keys needed.

## Slack app setup

Create a new app at [api.slack.com/apps](https://api.slack.com/apps) > **Create New App** > **From scratch**.

**Socket Mode** - toggle ON, create an app-level token with `connections:write` scope. This is your `xapp-...` token.

**OAuth & Permissions** - add these Bot Token Scopes:
- `app_mentions:read`
- `chat:write`
- `channels:history`
- `groups:history`
- `im:history`
- `im:read`

**Event Subscriptions** - toggle ON, subscribe to:
- `app_mention`
- `message.im`

**Install to Workspace** - copy the `xoxb-...` Bot User OAuth Token.

## Run locally

```bash
git clone <repo-url>
cd slack-reply-bot

cp .env.example .env
# fill in your three tokens

pip install -r requirements.txt
python app.py
```

Socket Mode connects outbound to Slack - no public URL, no ngrok, no port forwarding. Works behind any firewall.

## Usage

**In a channel** (bot must be added to the channel):
```
[someone posts] Check out this thread: https://x.com/user/status/123456
  └─ [reply] @kimchi-reply
  └─ [bot]   ⏳ Thinking...
  └─ [bot]   Option A - Subtle drop: ...
              Option B - Direct but human: ...
              Option C - Lead with the number: ...
```

**In a DM** (no @mention needed):
```
[you]  https://reddit.com/r/LocalLLaMA/comments/abc/post
[bot]  ⏳ Thinking...
[bot]  Option A - Subtle drop: ...
```

The bot also looks at the parent message in a thread - so you can @mention it in a reply to a message that contains the link.

## Deploy

For always-on, deploy anywhere that runs a Python process. Socket Mode means no inbound ports needed.

**Docker:**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

**Railway:**
```bash
railway init
railway up
```

**Fly.io:**
```bash
fly launch --no-deploy
fly secrets set SLACK_BOT_TOKEN=xoxb-... SLACK_APP_TOKEN=xapp-... ANTHROPIC_API_KEY=sk-ant-...
fly deploy
```

## How the reply generation works

The bot uses Claude with a baked-in system prompt that encodes:

- **Product knowledge** - what kimchi.dev is, its key capabilities (hibernation, autoscaling, routing, cost optimization), and who it's for
- **Jonno's writing style** - direct, anti-corporate, no em dashes, contractions always, lead with numbers, dry humor, no AI-sounding phrases
- **Platform-aware formatting** - X replies are 2-5 sentences and punchy; Reddit replies are longer, lead with genuine value, and bury the product mention deeper
- **Fitness check** - if the post's pain point doesn't map to something kimchi solves, the bot says "not a fit" instead of forcing a reply

## Configuration

| Env var | Required | Default | Description |
|---|---|---|---|
| `SLACK_BOT_TOKEN` | Yes | - | Bot User OAuth Token (`xoxb-...`) |
| `SLACK_APP_TOKEN` | Yes | - | App-Level Token for Socket Mode (`xapp-...`) |
| `ANTHROPIC_API_KEY` | Yes | - | Anthropic API key (`sk-ant-...`) |
| `CLAUDE_MODEL` | No | `claude-sonnet-4-20250514` | Claude model to use |

## Content fetching

**X.com** - uses [FxTwitter](https://github.com/FixTweet/FxTwitter) as primary (free, no auth, returns full tweet data). Falls back to Twitter's official oEmbed endpoint if FxTwitter is down.

**Reddit** - appends `.json` to the post URL. No auth needed. Pulls the original post plus top 8 comments for thread context.
