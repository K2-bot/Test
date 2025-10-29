import os
import threading
from flask import Flask
from telebot import TeleBot
from dotenv import load_dotenv
from builder_agent import BuilderAgent

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

bot = TeleBot(BOT_TOKEN)
agent = BuilderAgent(api_key=GEMINI_KEY)
app = Flask(__name__)

# Telegram Bot Commands
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(
        message,
        "👋 Hi! I'm your AI Builder Agent.\n"
        "Use /build <goal> to create a script.\n"
        "Use /deploy to deploy your generated code."
    )

@bot.message_handler(commands=['build'])
def build(message):
    goal = message.text.replace("/build", "").strip()
    if not goal:
        bot.reply_to(message, "❗️ Example: /build calculator bot")
        return
    bot.reply_to(message, f"🧠 Building your project: {goal} ...")
    result = agent.build(goal)
    bot.reply_to(message, result)

@bot.message_handler(commands=['deploy'])
def deploy(message):
    folder = message.text.replace("/deploy", "").strip() or "."
    bot.reply_to(message, f"🚀 Deploying folder: {folder} ...")
    result = agent.deploy_to_render(folder)
    bot.reply_to(message, result)

# Web endpoint for health check
@app.route("/")
def index():
    return "🤖 Telegram Bot + Builder Agent is running on Render!"

if __name__ == "__main__":
    # Run Telegram bot in background thread
    threading.Thread(target=bot.infinity_polling, daemon=True).start()

    # Run Flask server on Render port
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

