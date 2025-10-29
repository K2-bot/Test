import os
from telebot import TeleBot
from dotenv import load_dotenv
from builder_agent import BuilderAgent

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

bot = TeleBot(BOT_TOKEN)
agent = BuilderAgent(api_key=GEMINI_KEY)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(
        message,
        "👋 Hi! I'm your AI Builder Agent.\n"
        "Use /build <goal> to create something.\n"
        "Use /deploy to deploy generated bot."
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

bot.infinity_polling()
