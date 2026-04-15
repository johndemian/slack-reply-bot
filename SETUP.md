# Kimchi Reply Bot - Setup Guide

## 1. Create the Slack App

Go to https://api.slack.com/apps and click **Create New App** > **From scratch**.

### Enable Socket Mode
- Go to **Socket Mode** in the sidebar and toggle it ON
- Create an app-level token with scope `connections:write` - this gives you the `xapp-...` token

### Set Bot Scopes
Go to **OAuth & Permissions** and add these Bot Token Scopes:
- `app_mentions:read` - so the bot can see when it's @mentioned
- `chat:write` - so the bot can post replies
- `channels:history` - so the bot can read thread context
- `groups:history` - same but for private channels
- `im:history` - so the bot can respond to DMs
- `im:read` - so DMs work

### Enable Events
Go to **Event Subscriptions** and toggle ON. Subscribe to these bot events:
- `app_mention`
- `message.im`

### Install to Workspace
Go to **Install App** and click **Install to Workspace**. Copy the `xoxb-...` Bot User OAuth Token.

## 2. Get API Keys

### Anthropic (Claude)
- Go to https://console.anthropic.com/settings/keys
- Create an API key

### X/Twitter (optional - only if you want X.com support)
- Go to https://developer.x.com/en/portal
- Create a project and app
- Generate a Bearer Token (read-only access is sufficient)
- Basic tier ($100/mo) gives you the search endpoint for thread context

## 3. Configure and Run

```bash
cd slack-reply-bot
cp .env.example .env
# Edit .env with your actual tokens

pip install -r requirements.txt
python app.py
```

The bot runs in Socket Mode - no public URL or ngrok needed. It connects outbound to Slack's servers.

## 4. Usage

In any Slack channel where the bot is added:
1. Someone posts a message with an X.com or Reddit link
2. Reply in that thread and @mention the bot (e.g. `@kimchi-reply analyze this`)
3. The bot replies with "Thinking..." then updates with 2-3 reply options

You can also DM the bot directly with a link - no @mention needed.

## 5. Deploy (optional)

For always-on, deploy to any server that can run a Python process:

**Railway** (easiest):
```bash
railway init
railway up
```

**Fly.io**:
```bash
fly launch --no-deploy
fly secrets set SLACK_BOT_TOKEN=xoxb-... SLACK_APP_TOKEN=xapp-... ANTHROPIC_API_KEY=sk-ant-... X_BEARER_TOKEN=...
fly deploy
```

**Docker**:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

Socket Mode means the bot connects outbound - no inbound ports, no HTTPS certs, no ngrok.
