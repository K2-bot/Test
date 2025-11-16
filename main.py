from flask import Flask, request, jsonify
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import telebot

# -------------------------------
# Load environment variables
# -------------------------------
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# -------------------------------
# Initialize Telegram Bot & Supabase
# -------------------------------
bot = telebot.TeleBot(BOT_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -------------------------------
# Payment verification function
# -------------------------------
def verify_and_use_payment(transaction_id, method, amount_usd):
    try:
        print(f"Checking payment => ID: {transaction_id}, Method: {method}, Amount: {amount_usd}")

        response = supabase.table("VerifyPayment") \
            .select("*") \
            .eq("transaction_id", transaction_id) \
            .eq("method", method) \
            .eq("status", "unused") \
            .eq("amount_usd", amount_usd) \
            .maybe_single()

        print("Supabase Response =>", response)

        if response and "id" in response:
            payment_id = response["id"]

            supabase.table("VerifyPayment") \
                .update({"status": "used"}) \
                .eq("id", payment_id) \
                .execute()

            print(f"Payment Updated to USED => ID: {payment_id}")
            return True

        print("No matching unused payment found.")
        return False

    except Exception as e:
        print("verify_and_use_payment ERROR =>", e)
        return False

# -------------------------------
# Flask API Endpoint for FlutterFlow
# -------------------------------
app = Flask(__name__)

@app.route("/verify_payment", methods=["POST"])
def api_verify_payment():
    data = request.json
    transaction_id = data.get("transaction_id")
    method = data.get("method")
    amount = data.get("amount")

    if not transaction_id or not method or amount is None:
        return jsonify({"success": False, "error": "Missing parameters"}), 400

    result = verify_and_use_payment(transaction_id, method, float(amount))
    return jsonify({"success": result})

# -------------------------------
# Optional: Telegram /verify command
# -------------------------------
@bot.message_handler(commands=['verify'])
def handle_verify(message):
    try:
        parts = message.text.split()
        if len(parts) != 4:
            bot.reply_to(message,
                "❌ Usage:\n/verify transactionId method amount\n\nExample:\n/verify 123456 KBZPay 0.2222",
                parse_mode="Markdown")
            return

        transaction_id = parts[1]
        method = parts[2]
        amount = float(parts[3])

        ok = verify_and_use_payment(transaction_id, method, amount)

        if ok:
            bot.reply_to(message,
                f"✅ Payment Verified & Marked as USED\n\n"
                f"📌 Transaction ID: {transaction_id}\n"
                f"💳 Method: {method}\n"
                f"💵 Amount: {amount}",
                parse_mode="Markdown")
        else:
            bot.reply_to(message,
                "❌ No matching unused payment found.\nPlease check Transaction ID, Method, and Amount again.")

    except Exception as e:
        bot.reply_to(message, f"❌ Error processing request: {e}")

# -------------------------------
# Run both Flask & Telegram Bot
# -------------------------------
if __name__ == "__main_":
    from threading import Thread

    # Telegram polling in separate thread
    def run_telegram():
        print("Telegram Bot is running...")
        bot.infinity_polling()

    Thread(target=run_telegram).start()

    # Flask API
    print("Flask API is running on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000)
