# Telegram Work Tracker — English

This version is designed for a free Render Web Service plus a GitHub Actions scheduled job.

Features:
- All buttons and messages are English.
- Monday–Saturday are working days.
- Sunday is automatically treated as the weekly day off.
- Record Worked / Didn't Work for each date.
- Today's Status, Weekly Report, and Monthly Report.
- GitHub Actions requests the weekly report endpoint every Saturday at 21:00 Bishkek time (15:00 UTC).

## Render settings

Create a **Web Service** from this repository.

Build Command:
`pip install -r requirements.txt`

Start Command:
`python bot.py`

Environment Variables:
- `BOT_TOKEN` = your BotFather token
- `ALLOWED_USER_ID` = `7437428206`
- `WEBHOOK_SECRET` = create a random secret string

After deployment, copy your Render service URL and set Telegram's webhook:

`https://api.telegram.org/botYOUR_TOKEN/setWebhook?url=https://YOUR-RENDER-URL/telegram/webhook&secret_token=YOUR_SECRET`

Do not put the Bot Token in GitHub files.

## GitHub Actions secrets

In repository Settings → Secrets and variables → Actions, add:
- `REPORT_URL` = `https://YOUR-RENDER-URL/send-weekly-report`
- `WEBHOOK_SECRET` = same secret used in Render

Important:
Render's free filesystem is not guaranteed to persist across restarts/redeploys. For permanent historical records, a persistent database/storage should be added later.
