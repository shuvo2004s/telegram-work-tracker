import os
import json
from datetime import datetime, time
from zoneinfo import ZoneInfo

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN", "PASTE_YOUR_BOT_TOKEN_HERE")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))
TZ = ZoneInfo("Asia/Bishkek")
DATA_FILE = "work_data.json"

BTN_WORKED = "✅ Worked Today"
BTN_NOT_WORKED = "❌ Didn't Work Today"
BTN_TODAY = "📅 Today's Status"
BTN_WEEK = "📊 Weekly Report"
BTN_MONTH = "📈 Monthly Report"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def allowed(update: Update):
    return ALLOWED_USER_ID == 0 or update.effective_user.id == ALLOWED_USER_ID

def keyboard():
    return ReplyKeyboardMarkup(
        [
            [BTN_WORKED, BTN_NOT_WORKED],
            [BTN_TODAY],
            [BTN_WEEK, BTN_MONTH],
        ],
        resize_keyboard=True
    )

def now():
    return datetime.now(TZ)

def weekly_report():
    today = now().date()
    monday = today.fromordinal(today.toordinal() - today.weekday())
    data = load_data()

    worked, not_worked = [], []
    for i in range(6):  # Monday-Saturday
        d = monday.fromordinal(monday.toordinal() + i)
        key = d.isoformat()
        if data.get(key) == "worked":
            worked.append(d.strftime("%d.%m.%Y"))
        elif data.get(key) == "not_worked":
            not_worked.append(d.strftime("%d.%m.%Y"))

    return (
        "📊 WEEKLY WORK REPORT\n\n"
        f"Period: {monday.strftime('%d.%m.%Y')} - "
        f"{monday.fromordinal(monday.toordinal()+5).strftime('%d.%m.%Y')}\n\n"
        f"✅ Days worked: {len(worked)}\n"
        f"❌ Days not worked: {len(not_worked)}\n"
        "💤 Sunday: Day off\n\n"
        "Worked:\n" + ("\n".join("• " + x for x in worked) if worked else "• No records") +
        "\n\nNot worked:\n" + ("\n".join("• " + x for x in not_worked) if not_worked else "• No records")
    )

def monthly_report():
    today = now()
    data = load_data()
    prefix = today.strftime("%Y-%m-")
    worked = sorted(k for k, v in data.items() if k.startswith(prefix) and v == "worked")
    not_worked = sorted(k for k, v in data.items() if k.startswith(prefix) and v == "not_worked")
    return (
        "📈 MONTHLY WORK REPORT\n\n"
        f"Month: {today.strftime('%m.%Y')}\n"
        f"✅ Days worked: {len(worked)}\n"
        f"❌ Days not worked: {len(not_worked)}\n"
        "💤 Sundays: Days off"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return
    await update.message.reply_text(
        "👋 Welcome!\n\nUse the buttons below to record your work status.",
        reply_markup=keyboard()
    )

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return

    text = update.message.text
    d = now()
    key = d.date().isoformat()
    data = load_data()

    if text == BTN_WORKED:
        data[key] = "worked"
        save_data(data)
        await update.message.reply_text(
            f"✅ Recorded: Worked today.\n📅 {d.strftime('%d.%m.%Y')}",
            reply_markup=keyboard()
        )
    elif text == BTN_NOT_WORKED:
        data[key] = "not_worked"
        save_data(data)
        await update.message.reply_text(
            f"❌ Recorded: Didn't work today.\n📅 {d.strftime('%d.%m.%Y')}",
            reply_markup=keyboard()
        )
    elif text == BTN_TODAY:
        if d.weekday() == 6:
            message = "💤 Sunday — Day off."
        else:
            value = data.get(key)
            message = {
                "worked": "✅ Today: Worked",
                "not_worked": "❌ Today: Didn't work"
            }.get(value, "⚪ No status recorded for today yet.")
        await update.message.reply_text(message, reply_markup=keyboard())
    elif text == BTN_WEEK:
        await update.message.reply_text(weekly_report(), reply_markup=keyboard())
    elif text == BTN_MONTH:
        await update.message.reply_text(monthly_report(), reply_markup=keyboard())

async def weekly_job(context: ContextTypes.DEFAULT_TYPE):
    if ALLOWED_USER_ID:
        await context.bot.send_message(
            chat_id=ALLOWED_USER_ID,
            text=weekly_report()
        )

def main():
    if TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
        raise RuntimeError("Set BOT_TOKEN environment variable first.")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    if ALLOWED_USER_ID:
        app.job_queue.run_daily(
            weekly_job,
            time=time(21, 0, tzinfo=TZ),
            days=(5,)  # Saturday
        )

    app.run_polling()

if __name__ == "__main__":
    main()
