import os
import time
import requests
from dotenv import load_dotenv
from supabase import create_client, Client
import telebot

# Load .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_GROUP_ID = os.getenv("TELEGRAM_GROUP_ID")
SMMGEN_API_KEY = os.getenv("SMMGEN_API_KEY")
SMMGEN_API_URL = os.getenv("SMMGEN_API_URL")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL_SECONDS", 60))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 100))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
RETRY_DELAY = int(os.getenv("RETRY_DELAY_SECONDS", 5))

# Initialize clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

def get_next_batch(last_id):
    """Fetch the next batch of existing SMMGEN orders after last_id"""
    try:
        res = supabase.table("WebsiteOrders") \
            .select("*") \
            .eq("supplier_name", "smmgen") \
            .gt("id", last_id) \
            .order("id", ascending=True) \
            .limit(BATCH_SIZE) \
            .execute()
        return res.data or []
    except Exception as e:
        print(f"❌ Supabase fetch error: {e}")
        return []

def check_smmgen_status(supplier_order_ids):
    """Call SMMGEN multiple status API with retry"""
    if not supplier_order_ids:
        return {}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            payload = {
                "key": SMMGEN_API_KEY,
                "action": "status",
                "orders": ",".join(supplier_order_ids)
            }
            response = requests.post(SMMGEN_API_URL, data=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"⚠️ Attempt {attempt} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
            else:
                print("❌ Max retries reached, skipping this batch.")
                return {}

def update_orders_and_notify(smmgen_data):
    """Update Supabase orders & notify Telegram if data changed"""
    for supplier_order_id, data in smmgen_data.items():
        if "error" in data:
            print(f"⚠️ Error for order {supplier_order_id}: {data['error']}")
            continue

        # Fetch order from Supabase
        try:
            res = supabase.table("WebsiteOrders") \
                .select("*") \
                .eq("supplier_order_id", supplier_order_id) \
                .execute()
            if not res.data:
                continue
            order = res.data[0]

            updates = {}
            changed = False

            if order.get("status") != data.get("status"):
                updates["status"] = data.get("status")
                changed = True
            if order.get("remain") != int(data.get("remains", 0)):
                updates["remain"] = int(data.get("remains", 0))
                changed = True
            if order.get("start_count") != int(data.get("start_count", 0)):
                updates["start_count"] = int(data.get("start_count", 0))
                changed = True
            if order.get("buy_charge") != float(data.get("charge", 0)):
                updates["buy_charge"] = float(data.get("charge", 0))
                changed = True

            if changed:
                supabase.table("WebsiteOrders").update(updates) \
                    .eq("supplier_order_id", supplier_order_id).execute()

                msg = (
                    f"📦 Order Update:\n"
                    f"Supplier Order ID: {supplier_order_id}\n"
                    f"Service: {order['service']}\n"
                    f"Status: {data.get('status')}\n"
                    f"Start Count: {data.get('start_count')}\n"
                    f"Remain: {data.get('remains')}\n"
                    f"Charge: {data.get('charge')} USD"
                )
                for attempt in range(1, MAX_RETRIES + 1):
                    try:
                        bot.send_message(TELEGRAM_GROUP_ID, msg)
                        break
                    except Exception as e:
                        print(f"⚠️ Telegram send attempt {attempt} failed: {e}")
                        if attempt < MAX_RETRIES:
                            time.sleep(RETRY_DELAY)
                        else:
                            print("❌ Max Telegram retries reached.")
        except Exception as e:
            print(f"❌ Error updating order {supplier_order_id}: {e}")

def main_loop():
    print("🚀 SMMGEN Order Checker Started...")

    last_id = 0
    while True:
        batch = get_next_batch(last_id)
        if not batch:
            last_id = 0  # reset to start from lowest existing ID
            print(f"ℹ️ No new batch found. Restarting from beginning after {CHECK_INTERVAL}s...")
            time.sleep(CHECK_INTERVAL)
            continue

        supplier_order_ids = [o["supplier_order_id"] for o in batch if o.get("supplier_order_id")]
        if supplier_order_ids:
            smmgen_status_data = check_smmgen_status(supplier_order_ids)
            if smmgen_status_data:
                update_orders_and_notify(smmgen_status_data)

        last_id = batch[-1]["id"]  # move to next batch
        time.sleep(CHECK_INTERVAL)
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

if __name__ == "__main__":
    main_loop()
