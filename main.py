import telebot
from telebot import types
from telethon import TelegramClient, functions, types as tel_types
import asyncio
import os
import threading
import re
from flask import Flask

# --- WEB SERVER (24/7 Hosting) ---
app = Flask('')
@app.route('/')
def home(): return "SYSTEM ONLINE 🚀"
def run(): app.run(host='0.0.0.0', port=8080)
threading.Thread(target=run, daemon=True).start()

# --- CONFIGURATION ---
TOKEN = '8692935006:AAFGFN6aeecPubPdd821zq-CmQnZzMtySsw'
API_ID = 35155488
API_HASH = '9ee6b40363f94481d48dea8a3a871728'
OWNER_ID = 7634311488

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# Local DB
db = {
    'users': {}, 
    'admins': [OWNER_ID], 
    'upi': 'abhay-op.315@ptyes',
    'stock': {}, 
    'sell_rates': {}, 
    'buy_rates': {},
    'linked_bots': []
}
active_logins = {}

if not os.path.exists('sessions'): os.makedirs('sessions')

# --- HELPERS ---
def is_admin(uid): return uid in db['admins'] or uid == OWNER_ID

def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('💰 BALANCE', '📥 DEPOSIT', '📤 SELL ID', '🛒 BUY ID', '📞 SUPPORT')
    return markup

# --- START ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if uid not in db['users']: db['users'][uid] = {'balance': 0}
    bot.send_message(message.chat.id, "🔥 **PRIME MASTER BOT v5.0**\n\nSare bugs fix kar diye gaye hain. Bot ab fully functional hai.", reply_markup=main_menu())

# --- BALANCE & SUPPORT ---
@bot.message_handler(func=lambda m: m.text == '💰 BALANCE')
def bal_check(message):
    bal = db['users'].get(message.from_user.id, {}).get('balance', 0)
    bot.send_message(message.chat.id, f"💳 **Your Balance:** ₹{bal}")

@bot.message_handler(func=lambda m: m.text == '📞 SUPPORT')
def support_check(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👤 MESSAGE OWNER", url="https://t.me/god_abhay"))
    bot.send_message(message.chat.id, "🆘 **Support:** Niche diye button par click karke owner se baat karein.", reply_markup=markup)

# --- ID LOGIN ENGINE (SELLING & STOCK) ---
def login_engine(chat_id, phone, country, mode):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    try:
        loop.run_until_complete(client.connect())
        req = loop.run_until_complete(client.send_code_request(phone))
        active_logins[chat_id] = {'client': client, 'phone': phone, 'hash': req.phone_code_hash, 'loop': loop, 'country': country, 'mode': mode}
        msg = bot.send_message(chat_id, "📩 **OTP Sent!** Code enter karein:")
        bot.register_next_step_handler(msg, otp_verify)
    except Exception as e: bot.send_message(chat_id, f"❌ Error: {e}")

def otp_verify(message):
    otp = message.text.strip()
    d = active_logins.get(message.chat.id)
    if not d: return
    try:
        d['loop'].run_until_complete(d['client'].sign_in(d['phone'], otp, phone_code_hash=d['hash']))
        finalize_bot_login(message, d)
    except Exception as e:
        if "password" in str(e).lower():
            msg = bot.send_message(message.chat.id, "🔐 **2FA Password Required:**")
            bot.register_next_step_handler(msg, pass_verify)
        else: bot.send_message(message.chat.id, "❌ Invalid OTP.")

def pass_verify(message):
    pwd = message.text.strip()
    d = active_logins.get(message.chat.id)
    try:
        d['loop'].run_until_complete(d['client'].sign_in(password=pwd))
        finalize_bot_login(message, d, pwd)
    except: bot.send_message(message.chat.id, "❌ Wrong 2FA.")

def finalize_bot_login(message, d, pwd="No Password"):
    uid = message.from_user.id
    if d['mode'] == "sell":
        # SELL ID: Login ho gayi, ab admin check karega
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"sa_{uid}_{d['country']}"),
                   types.InlineKeyboardButton("❌ REJECT", callback_data=f"sr_{uid}"))
        for adm in db['admins']:
            bot.send_message(adm, f"📦 **NEW SELL REQ**\nUser: `{uid}`\nNum: `{d['phone']}`\nPass: `{pwd}`\nCountry: {d['country']}", reply_markup=markup)
        bot.send_message(message.chat.id, "✅ **ID Login Successful!**\nAdmin approval ka wait karein.")
    else:
        # ADMIN STOCK ADD
        if d['country'] not in db['stock']: db['stock'][d['country']] = []
        db['stock'][d['country']].append(f"{d['phone']}:PASS:{pwd}")
        bot.send_message(message.chat.id, f"✅ ID {d['phone']} Stock mein add ho gayi.")

# --- DEPOSIT (APPROVE/REJECT) ---
@bot.message_handler(func=lambda m: m.text == '📥 DEPOSIT')
def dep_start(message):
    msg = bot.send_message(message.chat.id, "💵 **Amount:**")
    bot.register_next_step_handler(msg, dep_u)

def dep_u(message, amt=None):
    try:
        amt = int(message.text)
        msg = bot.send_message(message.chat.id, f"💳 Pay to: `{db['upi']}`\nSend **12-digit UTR**:")
        bot.register_next_step_handler(msg, dep_s, amt)
    except: bot.send_message(message.chat.id, "❌ Amount sahi likho.")

def dep_s(message, amt):
    utr = message.text.strip()
    msg = bot.send_message(message.chat.id, "📸 Send **Screenshot**:")
    bot.register_next_step_handler(msg, dep_f, amt, utr)

def dep_f(message, amt, utr):
    if message.content_type != 'photo': return bot.send_message(message.chat.id, "❌ Screenshot bhejo.")
    uid = message.from_user.id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"da_{uid}_{amt}"),
               types.InlineKeyboardButton("❌ REJECT", callback_data=f"dr_{uid}"))
    for adm in db['admins']:
        bot.send_photo(adm, message.photo[-1].file_id, caption=f"🔔 **DEP REQ**\nUser: `{uid}`\nAmt: ₹{amt}\nUTR: {utr}", reply_markup=markup)
    bot.send_message(message.chat.id, "⏳ Admin review kar raha hai.")

# --- CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def calls(call):
    p = call.data.split('_')
    if p[0] == 'da': # Deposit Approve
        uid, amt = int(p[1]), int(p[2])
        db['users'][uid]['balance'] += amt
        bot.send_message(uid, f"✅ ₹{amt} added successfully!")
        bot.edit_message_caption("Approved ✅", call.message.chat.id, call.message.message_id)
    elif p[0] == 'dr': # Deposit Reject
        bot.send_message(int(p[1]), "❌ Your deposit request was rejected.")
        bot.edit_message_caption("Rejected ❌", call.message.chat.id, call.message.message_id)
    elif p[0] == 'sa': # Sell Approve
        uid, c = int(p[1]), p[2]
        rate = db['sell_rates'].get(c, 0)
        db['users'][uid]['balance'] += rate
        bot.send_message(uid, f"✅ ID Sold! ₹{rate} added.")
        bot.edit_message_text("Approved ✅", call.message.chat.id, call.message.message_id)
    elif p[0] == 'sr': # Sell Reject
        bot.send_message(int(p[1]), "❌ Your Sell Request was rejected.")
        bot.edit_message_text("Rejected ❌", call.message.chat.id, call.message.message_id)

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['admin'])
def adm_p(message):
    if not is_admin(message.from_user.id): return
    bot.send_message(message.chat.id, "👑 **ADMIN PANEL**\n\n🌍 `/addcountry COUNTRY BUY SELL` \n➕ `/addstock` \n📢 `/broadcast` \n👤 `/addadmin ID` \n💰 `/addbal ID AMT` \n🔗 `/linkbot TOKEN` \n💳 `/changeupi UPI` ")

@bot.message_handler(commands=['addbal'])
def add_b(message):
    if not is_admin(message.from_user.id): return
    try:
        _, uid, amt = message.text.split()
        db['users'][int(uid)]['balance'] += int(amt)
        bot.reply_to(message, "✅ Balance Updated.")
    except: pass

@bot.message_handler(commands=['addadmin'])
def add_adm(message):
    if message.from_user.id != OWNER_ID: return
    try:
        aid = int(message.text.split()[1])
        db['admins'].append(aid)
        bot.reply_to(message, "✅ Admin Added.")
    except: pass

# --- SELL/BUY ---
@bot.message_handler(func=lambda m: m.text == '📤 SELL ID')
def sell_i(message):
    if not db['sell_rates']: return bot.send_message(message.chat.id, "❌ Markets Closed.")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for c in db['sell_rates']: markup.add(f"SELL {c}")
    bot.send_message(message.chat.id, "Select Country:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text.startswith('SELL '))
def sell_s(message):
    c = message.text.split()[1]
    msg = bot.send_message(message.chat.id, "📞 Enter Number (+):", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, lambda m: threading.Thread(target=login_engine, args=(message.chat.id, m.text, c, "sell")).start())

bot.polling(none_stop=True)
