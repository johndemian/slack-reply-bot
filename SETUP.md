# Detailed Slack App Setup

Step-by-step walkthrough for creating the Slack app. See README.md for the full picture.

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

## 2. Get Kimchi.dev API Key

- Go to your kimchi.dev account dashboard
- Create an API key
- Note the API endpoint URL (usually `https://api.kimchi.dev/v1/chat/completions`)

## 3. Configure and Run

```bash
cd slack-reply-bot
cp .env.example .env
# Edit .env with your actual tokens

pip install -r requirements.txt
python app.py
```

The bot runs in Socket Mode - no public URL or ngrok needed. It connects outbound to Slack's servers.
