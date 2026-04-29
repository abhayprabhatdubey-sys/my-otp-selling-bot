import telebot
from telebot import types
from telethon import TelegramClient, functions, types as tel_types
import asyncio
import os
import threading
import re
from flask import Flask

# --- WEB SERVER (For 24/7 Hosting) ---
app = Flask('')
@app.route('/')
def home(): return "PRIME MASTER BOT ACTIVE"
def run(): app.run(host='0.0.0.0', port=8080)
threading.Thread(target=run, daemon=True).start()

# --- CONFIG ---
TOKEN = '8692935006:AAFGFN6aeecPubPdd821zq-CmQnZzMtySsw'
API_ID = 35155488
API_HASH = '9ee6b40363f94481d48dea8a3a871728'
OWNER_ID = 7634311488

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

db = {
    'users': {}, 
    'admins': [OWNER_ID], 
    'upi': 'abhay-op.315@ptyes',
    'stock': {}, 
    'sell_rates': {}, 
    'buy_rates': {},
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
    bot.send_message(message.chat.id, "🔥 **PRIME OTP BOT READY**", reply_markup=main_menu())

# --- DEPOSIT SYSTEM (OLD FLOW) ---
@bot.message_handler(func=lambda m: m.text == '📥 DEPOSIT')
def dep_start(message):
    msg = bot.send_message(message.chat.id, "💵 **Enter Amount to Deposit:**")
    bot.register_next_step_handler(msg, dep_utr)

def dep_utr(message):
    try:
        amt = int(message.text)
        msg = bot.send_message(message.chat.id, f"💳 **Pay to:** `{db['upi']}`\n\nSend your **12-digit UTR**:")
        bot.register_next_step_handler(msg, dep_ss, amt)
    except: bot.send_message(message.chat.id, "❌ Invalid Amount.")

def dep_ss(message, amt):
    utr = message.text.strip()
    if len(utr) != 12: return bot.send_message(message.chat.id, "❌ UTR must be 12 digits.")
    msg = bot.send_message(message.chat.id, "📸 Send **Payment Screenshot**:")
    bot.register_next_step_handler(msg, dep_final, amt, utr)

def dep_final(message, amt, utr):
    if message.content_type != 'photo': return bot.send_message(message.chat.id, "❌ Send Photo only.")
    uid = message.from_user.id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"da_{uid}_{amt}"))
    for a in db['admins']:
        bot.send_photo(a, message.photo[-1].file_id, caption=f"🔔 **DEP REQ**\nUser: `{uid}`\nAmt: ₹{amt}\nUTR: `{utr}`", reply_markup=markup)
    bot.send_message(message.chat.id, "⏳ Sent to Admin.")

# --- ADMIN PANEL ---
@bot.message_handler(commands=['admin'])
def admin_p(message):
    if not is_admin(message.from_user.id): return
    bot.send_message(message.chat.id, "👑 **ADMIN PANEL**\n\n🌍 `/addcountry COUNTRY BUY SELL` \n➕ `/addstock` \n📢 `/broadcast` \n👤 `/addadmin ID` \n📈 `/list` \n💳 `/changeupi UPI` ")

@bot.message_handler(commands=['broadcast'])
def bc_init(message):
    if not is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, "📝 Enter message:")
    bot.register_next_step_handler(msg, bc_exe)

def bc_exe(message):
    count = 0
    for u in db['users']:
        try: bot.send_message(u, f"📢 **NOTIFICATION**\n\n{message.text}"); count += 1
        except: pass
    bot.send_message(message.chat.id, f"✅ Sent to {count} users.")

@bot.message_handler(commands=['addadmin'])
def add_adm(message):
    if message.from_user.id != OWNER_ID: return
    try:
        aid = int(message.text.split()[1])
        db['admins'].append(aid)
        bot.reply_to(message, "✅ Admin added.")
    except: bot.reply_to(message, "Usage: `/addadmin ID`")

# --- STOCK & SELL LOGIC (AUTO 2FA CHANGE TO 2710) ---
def login_worker(chat_id, phone, country, mode):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    try:
        loop.run_until_complete(client.connect())
        req = loop.run_until_complete(client.send_code_request(phone))
        active_logins[chat_id] = {'client': client, 'phone': phone, 'hash': req.phone_code_hash, 'loop': loop, 'country': country, 'mode': mode}
        bot.send_message(chat_id, "📩 **OTP SENT!** Enter code:")
        bot.register_next_step_handler_by_chat_id(chat_id, verify_step)
    except Exception as e: bot.send_message(chat_id, f"❌ Error: {e}")

def verify_step(message):
    otp = message.text.strip()
    d = active_logins.get(message.chat.id)
    try:
        d['loop'].run_until_complete(d['client'].sign_in(d['phone'], otp, phone_code_hash=d['hash']))
        finalize(message, d)
    except Exception as e:
        if "password" in str(e).lower():
            bot.send_message(message.chat.id, "🔐 Enter 2FA Password:")
            bot.register_next_step_handler_by_chat_id(message.chat.id, verify_2fa)
        else: bot.send_message(message.chat.id, "❌ OTP Error.")

def verify_2fa(message):
    pwd = message.text.strip()
    d = active_logins.get(message.chat.id)
    try:
        d['loop'].run_until_complete(d['client'].sign_in(password=pwd))
        finalize(message, d, pwd)
    except: bot.send_message(message.chat.id, "❌ Wrong 2FA.")

def finalize(message, d, pwd="No Password"):
    if d['mode'] == "sell":
        try: # Purana Feature: Change 2FA to 2710
            d['loop'].run_until_complete(d['client'](functions.account.UpdatePasswordSettingsRequest(
                new_settings=tel_types.account.PasswordInputSettings(new_password="2710", hint="dob")
            )))
        except: pass
        uid = message.from_user.id
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"sa_{uid}_{d['country']}"))
        for a in db['admins']: bot.send_message(a, f"📦 **SELL REQ**\nUser: `{uid}`\nNum: `{d['phone']}`\n2FA: `2710`", reply_markup=markup)
        bot.send_message(message.chat.id, "✅ Success! 2FA set to 2710.")
    else:
        db['stock'][d['country']].append(f"{d['phone']}:PASS:{pwd}")
        bot.send_message(message.chat.id, "✅ Added to Stock.")

# --- BUY ID SYSTEM (NEW OTP & LOGOUT FEATURE) ---
@bot.message_handler(func=lambda m: m.text == '🛒 BUY ID')
def buy_menu(message):
    if not db['buy_rates']: return bot.send_message(message.chat.id, "❌ No stock.")
    markup = types.InlineKeyboardMarkup()
    for c, p in db['buy_rates'].items():
        markup.add(types.InlineKeyboardButton(f"{c} - ₹{p} ({len(db['stock'].get(c, []))})", callback_data=f"buyid_{c}"))
    bot.send_message(message.chat.id, "Select Country:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('buyid_'))
def buy_callback(call):
    country = call.data.split('_')[1]
    uid = call.from_user.id
    price = db['buy_rates'].get(country, 0)
    
    if db['users'].get(uid, {}).get('balance', 0)
