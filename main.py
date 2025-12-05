import os
import logging
import json
import asyncio
from aiohttp import web
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, Application
from supabase import create_client, Client

# ၁။ Environment Variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
PORT = int(os.environ.get("PORT", 10000)) # Render က ပေးမယ့် Port

# Supabase ချိတ်ဆက်ခြင်း
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ၂။ Dummy Web Server (Render မအိပ်အောင် Port ဖွင့်ပေးခြင်း)
async def health_check(request):
    return web.Response(text="Bot is running alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logging.info(f"🕸️ Web Server started on port {PORT}")

# ၃။ Bot Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # User မှတ်ပုံတင်ခြင်း
    try:
        supabase.table('users').upsert({
            "telegram_id": user.id,
            "full_name": user.full_name
        }).execute()
    except Exception as e:
        print(f"User Register Error: {e}")

    await update.message.reply_text(
        f"မင်္ဂလာပါ {user.full_name} ခင်ဗျာ! 👋\n"
        "ဈေးဝယ်ရန် အောက်ပါ *'Shop Now'* ခလုတ်ကို နှိပ်ပါ 👇",
        parse_mode='Markdown'
    )

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    raw_data = update.effective_message.web_app_data.data
    data = json.loads(raw_data)
    
    cart_items = data.get('cart', [])
    user_info = data.get('user_info', {})

    if not cart_items: return

    await update.message.reply_text("🔄 Order ကို စစ်ဆေးနေပါသည်...")

    total_amount = 0
    valid_items = []

    # ဖုန်းနှင့် လိပ်စာ Update လုပ်ခြင်း
    if user_info:
        try:
            supabase.table('users').update({
                "phone_number": user_info.get('phone'),
                "address": user_info.get('address')
            }).eq("telegram_id", user.id).execute()
        except: pass

    # ဈေးနှုန်း စစ်ဆေးခြင်း
    for item in cart_items:
        db_res = supabase.table('products').select("*").eq('id', item['id']).execute()
        if db_res.data:
            real_price = db_res.data[0]['base_price']
            total_amount += real_price * item['quantity']
            valid_items.append({
                "product_id": item['id'],
                "quantity": item['quantity'],
                "price_at_booking": real_price
            })

    # Order သိမ်းခြင်း
    try:
        order_res = supabase.table('orders').insert({
            "user_id": user.id,
            "total_amount": total_amount,
            "status": "Pending Payment",
            "contact_phone": user_info.get('phone'),
            "shipping_address": user_info.get('address')
        }).execute()
        
        if order_res.data:
            new_order_id = order_res.data[0]['id']
            for item in valid_items:
                item['order_id'] = new_order_id
                supabase.table('order_items').insert(item).execute()

            await update.message.reply_text(
                f"✅ *Order အောင်မြင်ပါသည်!*\n🆔 Order ID: `#{str(new_order_id)[:8]}`\n💰 ကျသင့်ငွေ: *{total_amount:,} Ks*\n\n🏧 KPay: `09123456789` သို့ ငွေလွှဲပြီး Screenshot ပို့ပေးပါ။",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Order Error")

    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text("❌ System Error")

# ၄။ Init Function (Bot စ run ချိန်မှာ Web Server ပါ တွဲ run မည်)
async def post_init(application: Application):
    asyncio.create_task(start_web_server())

if __name__ == '__main__':
    # Build Application
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    
    print("Bot is starting...")
    app.run_polling()
