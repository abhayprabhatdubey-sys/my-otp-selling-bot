import telebot
from telebot import types
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
import asyncio
import time
import os
from flask import Flask
from threading import Thread

# --- RENDER WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "BOT IS ONLINE!"
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
    'stock': [], # [{'phone': '...', 'country': '...', 'buy_price': 40}]
    'sell_rates': {'INDIA': 25, 'USA': 40}, 
    'buy_rates': {'INDIA': 40, 'USA': 60}
}
active_clients = {}

def is_admin(uid): return uid in db['admins']

# --- LOGS FUNCTION ---
def post_to_logs(text):
    try: bot.send_message(LOG_CHANNEL_ID, f"📢 **SYSTEM UPDATE**\n\n{text}", parse_mode="Markdown")
    except Exception as e: print(f"LOG ERROR: {e}")

# --- START MENU ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if uid not in db['users']: db['users'][uid] = {'balance': 0}
    
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('💰 **BALANCE**', '📥 **DEPOSIT**')
    markup.add('📤 **SELL ID**', '🛒 **BUY ACCOUNT**')
    markup.add('📞 **SUPPORT**')
    
    bot.send_message(message.chat.id, "🔥 **WELCOME TO PRIME OTP BOT**\n\n**SELECT AN OPTION BELOW TO CONTINUE:**", 
                     parse_mode="Markdown", reply_markup=markup)

# --- USER SUPPORT ---
@bot.message_handler(func=lambda message: message.text == '📞 **SUPPORT**')
def support(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👤 **OWNER**", url="https://t.me/god_abhay"),
               types.InlineKeyboardButton("💬 **JOIN GC**", url="https://t.me/Team_quorum"))
    bot.send_message(message.chat.id, "🚩 **NEED HELP? CONTACT OWNER OR JOIN OUR GC:**", reply_markup=markup)

# --- BALANCE ---
@bot.message_handler(func=lambda message: message.text == '💰 **BALANCE**')
def check_balance(message):
    bal = db['users'].get(message.from_user.id, {}).get('balance', 0)
    bot.send_message(message.chat.id, f"💳 **YOUR CURRENT BALANCE:**\n\n💰 **₹{bal}**", parse_mode="Markdown")

# --- DEPOSIT (MANUAL) ---
@bot.message_handler(func=lambda message: message.text == '📥 **DEPOSIT**')
def dep_1(message):
    msg = bot.send_message(message.chat.id, "💵 **ENTER AMOUNT (MIN ₹10):**")
    bot.register_next_step_handler(msg, dep_2)

def dep_2(message):
    try:
        amt = int(message.text)
        msg = bot.send_message(message.chat.id, f"💳 **PAY ₹{amt} TO:** `abhay-op.315@ptyes`\n\n**SEND 12-DIGIT UTR:**")
        bot.register_next_step_handler(msg, dep_3, amt)
    except: bot.send_message(message.chat.id, "❌ **INVALID AMOUNT!**")

def dep_3(message, amt):
    utr = message.text.strip()
    if len(utr) != 12: return bot.send_message(message.chat.id, "❌ **UTR MUST BE 12 DIGITS!**")
    msg = bot.send_message(message.chat.id, "📸 **SEND PAYMENT SCREENSHOT:**")
    bot.register_next_step_handler(msg, dep_to_admin, amt, utr)

def dep_to_admin(message, amt, utr):
    if message.content_type != 'photo': return bot.send_message(message.chat.id, "❌ **SEND A PHOTO!**")
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ **APPROVE**", callback_data=f"depapp_{message.from_user.id}_{amt}"),
               types.InlineKeyboardButton("❌ **REJECT**", callback_data=f"deprej_{message.from_user.id}"))
    for adm in db['admins']:
        bot.send_message(adm, f"🔔 **DEPOSIT REQUEST**\nUSER: `{message.from_user.id}`\nAMT: ₹{amt}\nUTR: `{utr}`", reply_markup=markup)
        bot.send_photo(adm, message.photo[-1].file_id)
    bot.send_message(message.chat.id, "⏳ **PENDING APPROVAL!**")

# --- SELL ID (WITH LOGIN & APPROVAL) ---
@bot.message_handler(func=lambda message: message.text == '📤 **SELL ID**')
def sell_start(message):
    msg = bot.send_message(message.chat.id, "🌍 **WHICH COUNTRY ID? (E.G. INDIA):**")
    bot.register_next_step_handler(msg, sell_step_2)

def sell_step_2(message):
    country = message.text.strip().upper()
    msg = bot.send_message(message.chat.id, f"📞 **SEND {country} NUMBER (+...):**")
    bot.register_next_step_handler(msg, sell_step_3, country)

def sell_step_3(message, country):
    phone = message.text.strip()
    bot.send_message(message.chat.id, "⏳ **CONNECTING TO TELEGRAM...**")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(None, API_ID, API_HASH, loop=loop)
    active_clients[message.chat.id] = {'client': client, 'phone': phone, 'country': country}
    try:
        loop.run_until_complete(client.connect())
        req = loop.run_until_complete(client.send_code_request(phone))
        active_clients[message.chat.id]['hash'] = req.phone_code_hash
        msg = bot.send_message(message.chat.id, "📩 **ENTER OTP:**")
        bot.register_next_step_handler(msg, sell_step_4)
    except Exception as e: bot.send_message(message.chat.id, f"❌ **ERROR: {str(e).upper()}**")

def sell_step_4(message):
    otp = message.text.strip()
    data = active_clients.get(message.chat.id)
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(data['client'].sign_in(data['phone'], otp, phone_code_hash=data['hash']))
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ **APPROVE & PAY**", callback_data=f"selapp_{message.from_user.id}_{data['country']}_{data['phone']}"),
                   types.InlineKeyboardButton("❌ **REJECT**", callback_data=f"selrej_{message.from_user.id}"))
        for adm in db['admins']:
            bot.send_message(adm, f"🔔 **SELL REQUEST**\nUSER: `{message.from_user.id}`\nCOUNTRY: {data['country']}\nNUM: `{data['phone']}`", reply_markup=markup)
        bot.send_message(message.chat.id, "⏳ **VERIFIED! WAITING FOR ADMIN APPROVAL.**")
    except Exception as e: bot.send_message(message.chat.id, f"❌ **LOGIN FAIL: {str(e).upper()}**")

# --- CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    p = call.data.split('_')
    # Deposit Approval
    if p[0] == 'depapp':
        uid, amt = int(p[1]), int(p[2])
        db['users'][uid]['balance'] += amt
        bot.send_message(uid, f"✅ **DEPOSIT OF ₹{amt} APPROVED!**")
        post_to_logs(f"💰 **NEW DEPOSIT**\n**AMOUNT:** ₹{amt}\n**STATUS:** SUCCESS")
        bot.edit_message_text("✅ **APPROVED**", call.message.chat.id, call.message.message_id)
    
    # Sell Approval
    elif p[0] == 'selapp':
        uid, country, phone = int(p[1]), p[2], p[3]
        rate = db['sell_rates'].get(country, 25)
        db['users'][uid]['balance'] += rate
        db['stock'].append({'phone': phone, 'country': country})
        bot.send_message(uid, f"✅ **ID APPROVED! ₹{rate} ADDED.**")
        post_to_logs(f"📤 **ID SOLD**\n**COUNTRY:** {country}\n**PAYOUT:** ₹{rate}")
        bot.edit_message_text("✅ **PAID & ADDED**", call.message.chat.id, call.message.message_id)

# --- ADMIN PANEL ---
@bot.message_handler(commands=['admin'])
def admin_p(message):
    if not is_admin(message.from_user.id): return
    text = (
        "👑 **ADMIN PANEL**\n\n"
        "✨ `/addbal ID Amt` | `/users`\n"
        "✨ `/setrate Country Amt` (Selling Rate)\n"
        "✨ `/addadmin ID` | `/viewstock`"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

if __name__ == "__main__":
    keep_alive()
    bot.polling(none_stop=True)
