import os
import json
import threading
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests
from flask import Flask, request, jsonify

BOT_TOKEN = os.environ["BOT_TOKEN"]
ALLOWED_USER_ID = int(os.environ.get("ALLOWED_USER_ID", "0"))
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
TZ = ZoneInfo("Asia/Bishkek")
DATA_FILE = "work_data.json"

BTN_WORKED = "✅ Worked Today"
BTN_NOT_WORKED = "❌ Didn't Work Today"
BTN_TODAY = "📅 Today's Status"
BTN_WEEK = "📊 Weekly Report"
BTN_MONTH = "📈 Monthly Report"

app = Flask(__name__)
lock = threading.Lock()

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_data(data):
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)

def is_allowed(user_id):
    return ALLOWED_USER_ID == 0 or int(user_id) == ALLOWED_USER_ID

def keyboard():
    return {
        "keyboard": [
            [BTN_WORKED, BTN_NOT_WORKED],
            [BTN_TODAY],
            [BTN_WEEK, BTN_MONTH],
        ],
        "resize_keyboard": True
    }

def send_message(chat_id, text):
    return requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text, "reply_markup": keyboard()},
        timeout=20,
    )

def answer_callback(callback_id):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",
        json={"callback_query_id": callback_id},
        timeout=20,
    )

def weekly_report(date=None):
    today = date or datetime.now(TZ).date()
    monday = today - timedelta(days=today.weekday())
    saturday = monday + timedelta(days=5)
    data = load_data()

    worked, not_worked = [], []
    for i in range(6):
        d = monday + timedelta(days=i)
        value = data.get(d.isoformat())
        line = d.strftime("%A, %d.%m.%Y")
        if value == "worked":
            worked.append(line)
        elif value == "not_worked":
            not_worked.append(line)

    return (
        "📊 WEEKLY WORK REPORT\n\n"
        f"Period: {monday.strftime('%d.%m.%Y')} - {saturday.strftime('%d.%m.%Y')}\n\n"
        f"✅ Days worked: {len(worked)}/6\n"
        f"❌ Days not worked: {len(not_worked)}\n"
        "💤 Sunday: Day off\n\n"
        "WORKED:\n" + ("\n".join("• " + x for x in worked) if worked else "• No records") +
        "\n\nNOT WORKED:\n" + ("\n".join("• " + x for x in not_worked) if not_worked else "• No records")
    )

def monthly_report():
    today = datetime.now(TZ)
    prefix = today.strftime("%Y-%m-")
    data = load_data()
    worked = [k for k,v in data.items() if k.startswith(prefix) and v == "worked"]
    not_worked = [k for k,v in data.items() if k.startswith(prefix) and v == "not_worked"]
    return (
        "📈 MONTHLY WORK REPORT\n\n"
        f"Month: {today.strftime('%B %Y')}\n"
        f"✅ Days worked: {len(worked)}\n"
        f"❌ Days not worked: {len(not_worked)}\n"
        "💤 Sundays: Days off"
    )

def process_update(update):
    message = update.get("message", {})
    user = message.get("from", {})
    chat = message.get("chat", {})
    user_id = user.get("id")
    chat_id = chat.get("id")
    text = message.get("text", "")

    if not user_id or not chat_id or not is_allowed(user_id):
        return

    today = datetime.now(TZ)
    key = today.date().isoformat()

    if text == "/start":
        send_message(chat_id, "👋 Welcome!\n\nUse the English buttons below to record your work status.")
        return

    with lock:
        data = load_data()

        if text == BTN_WORKED:
            data[key] = "worked"
            save_data(data)
            send_message(chat_id, f"✅ Recorded: Worked today.\n📅 {today.strftime('%A, %d.%m.%Y')}")
        elif text == BTN_NOT_WORKED:
            data[key] = "not_worked"
            save_data(data)
            send_message(chat_id, f"❌ Recorded: Didn't work today.\n📅 {today.strftime('%A, %d.%m.%Y')}")
        elif text == BTN_TODAY:
            if today.weekday() == 6:
                reply = "💤 Sunday — Day off."
            else:
                value = data.get(key)
                reply = {"worked":"✅ Today: Worked","not_worked":"❌ Today: Didn't work"}.get(
                    value, "⚪ No status recorded for today yet."
                )
            send_message(chat_id, reply)
        elif text == BTN_WEEK:
            send_message(chat_id, weekly_report())
        elif text == BTN_MONTH:
            send_message(chat_id, monthly_report())

@app.get("/")
def home():
    return "Telegram Work Tracker is running."

@app.get("/health")
def health():
    return jsonify({"status": "ok"})

@app.post("/telegram/webhook")
def telegram_webhook():
    if WEBHOOK_SECRET and request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
        return "Forbidden", 403
    process_update(request.get_json(silent=True) or {})
    return "OK"

@app.post("/send-weekly-report")
def send_weekly_report():
    if WEBHOOK_SECRET and request.headers.get("X-Weekly-Secret") != WEBHOOK_SECRET:
        return "Forbidden", 403
    if not ALLOWED_USER_ID:
        return "ALLOWED_USER_ID is not set", 500
    r = send_message(ALLOWED_USER_ID, weekly_report())
    return jsonify({"telegram_status": r.status_code})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
