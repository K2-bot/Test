import os
import time
from datetime import datetime
from supabase import create_client, Client
import telebot
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
NEWS_GROUP_ID = os.getenv("NEWS_GROUP_ID")  # <-- News Group ID
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL_SECONDS", 10))

# Initialize clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Track last processed ID
last_id = 0

# Fetch new rows
def fetch_new_support_rows():
    global last_id
    try:
        res = supabase.table("SupportBox") \
            .select("*") \
            .gt("id", last_id) \
            .order("id", ascending=True) \
            .execute()
        rows = res.data or []
        if rows:
            last_id = rows[-1]["id"]
        return rows
    except Exception as e:
        print(f"❌ Supabase fetch error: {e}")
        return []

# Send message to Telegram
def send_to_telegram(row):
    try:
        msg = (
            f"📰 News ✍\n\n"
            f"ID - {row['id']}\n"
            f"User Email - {row['email']}\n"
            f"Subject - {row.get('subject','')}\n"
            f"Order ID - {row.get('order_id','')}\n"
            f"Massage 👇\n{row['message']}\n\n"
            f"/Answer {row['id']} Reply Massage\n"
            f"/Close {row['id']}"
        )
        bot.send_message(NEWS_GROUP_ID, msg)  # <-- Use News Group ID here
        print(f"✅ Sent SupportBox ID {row['id']} to News Group")
    except Exception as e:
        print(f"❌ Telegram send error: {e}")

# Command handler and main loop remain same...
@bot.message_handler(commands=['Answer', 'Close'])
def handle_commands(message):
    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 2:
            bot.reply_to(message, "❌ Invalid command format.")
            return
        cmd = parts[0].lower()
        row_id = int(parts[1])
        reply_msg = parts[2] if len(parts) == 3 else None

        # Fetch row
        res = supabase.table("SupportBox").select("*").eq("id", row_id).execute()
        if not res.data:
            bot.reply_to(message, f"❌ ID {row_id} not found.")
            return
        row = res.data[0]

        updates = {}
        if cmd == '/answer' and reply_msg:
            updates = {
                "status": "Answered",
                "reply_message": reply_msg,
                "replied_at": datetime.utcnow().isoformat()
            }
            supabase.table("SupportBox").update(updates).eq("id", row_id).execute()
            bot.reply_to(message, f"✅ Answered ID {row_id}")
        elif cmd == '/close':
            updates = {
                "status": "Closed",
                "replied_at": datetime.utcnow().isoformat()
            }
            supabase.table("SupportBox").update(updates).eq("id", row_id).execute()
            bot.reply_to(message, f"✅ Closed ID {row_id}")
        else:
            bot.reply_to(message, "❌ Invalid command usage.")

    except Exception as e:
        print(f"❌ Error handling command: {e}")
        bot.reply_to(message, "❌ Error occurred.")

# --------------------------
# Main loop: fetch + notify
# --------------------------
def main_loop():
    print("🚀 SupportBox Telegram Notifier Started...")
    while True:
        new_rows = fetch_new_support_rows()
        for row in new_rows:
            send_to_telegram(row)
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    import threading
    # Run Telegram bot polling in separate thread
    bot_thread = threading.Thread(target=bot.polling, kwargs={"none_stop": True})
    bot_thread.start()
