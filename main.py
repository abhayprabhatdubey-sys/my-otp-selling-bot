import telebot
from telebot import types
from telethon import TelegramClient, functions, types as tel_types
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, FloodWaitError
import asyncio
import os
import threading
import re
import time
import json
import logging
import sys
from flask import Flask

# --- PROFESSIONAL LOGGING SYSTEM ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("bot_debug.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# --- SERVER FOR 24/7 UPTIME ---
app = Flask('')
@app.route('/')
def home(): return "<h1>SYSTEM CORE: OPERATIONAL</h1>"
def run_web(): app.run(host='0.0.0.0', port=8080)
threading.Thread(target=run_web, daemon=True).start()

# --- CONFIGURATION ---
TOKEN = '8692935006:AAFGFN6aeecPubPdd821zq-CmQnZzMtySsw'
API_ID = 35155488
API_HASH = '9ee6b40363f94481d48dea8a3a871728'
OWNER_ID = 7634311488

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# --- POWERFUL DATABASE ENGINE ---
DB_FILE = 'bot_master_v3.json'

def load_db():
    try:
        if not os.path.exists(DB_FILE):
            data = {
                'users': {}, 'admins': [OWNER_ID], 'upi': 'abhay-op.315@ptyes',
                'stock': {}, 'sell_rates': {}, 'buy_rates': {}, 
                'stats': {'total_tx': 0, 'total_ids': 0}, 'maintenance': False
            }
            with open(DB_FILE, 'w') as f: json.dump(data, f)
            return data
        with open(DB_FILE, 'r') as f: return json.load(f)
    except Exception as e:
        logger.error(f"DB Load Error: {e}")
        return {}

def save_db():
    try:
        with open(DB_FILE, 'w') as f:
            json.dump(db, f, indent=4)
    except Exception as e:
        logger.error(f"DB Save Error: {e}")

db = load_db()
active_sessions = {}
if not os.path.exists('sessions'): os.makedirs('sessions')

# --- UI COMPONENTS ---
def main_menu_kb():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton('💰 BALANCE'), types.KeyboardButton('📥 DEPOSIT'),
        types.KeyboardButton('📤 SELL ID'), types.KeyboardButton('🛒 BUY ID'),
        types.KeyboardButton('📊 MY STATS'), types.KeyboardButton('📞 SUPPORT')
    )
    return markup

# --- COMMANDS ---
@bot.message_handler(commands=['start'])
def welcome_handler(m):
    uid = str(m.from_user.id)
    if uid not in db['users']:
        db['users'][uid] = {'balance': 0, 'sold': 0, 'bought': 0, 'reg_date': time.ctime()}
        save_db()
    bot.send_message(m.chat.id, "🔥 **TITAN AUTOMATION V3.0 ONLINE**\n\n- Full Auto ID Extraction\n- Auto 2FA (2710)\n- Secure Manual Deposit\n- Advanced Admin Panel", reply_markup=main_menu_kb())

# --- ADMIN PANEL (EXCLUSIVE) ---
@bot.message_handler(commands=['admin'])
def admin_portal(m):
    if m.from_user.id not in db['admins']: return
    text = (
        "👑 **TITAN ADMIN CONSOLE**\n\n"
        "📍 `/addcountry [NAME] [BUY] [SELL]`\n"
        "📍 `/addbal [ID] [AMT]`\n"
        "📍 `/setupi [UPI]`\n"
        "📍 `/broadcast [MSG]`\n"
        "📍 `/checkuser [ID]`\n"
        "📍 `/addstock` (Admin direct stock entry)"
    )
    bot.send_message(m.chat.id, text)

# --- 📥 MANUAL DEPOSIT (ADMIN APPROVAL) ---
@bot.message_handler(func=lambda m: m.text == '📥 DEPOSIT')
def deposit_init(m):
    msg = bot.send_message(m.chat.id, "💵 **Amount enter karein (₹):**")
    bot.register_next_step_handler(msg, deposit_utr)

def deposit_utr(m):
    if not m.text.isdigit(): return bot.send_message(m.chat.id, "❌ Valid amount likho.")
    amt = m.text
    msg = bot.send_message(m.chat.id, f"💳 Pay to UPI: `{db['upi']}`\n\nAb **12-digit UTR** bhejein:")
    bot.register_next_step_handler(msg, deposit_ss, amt)

def deposit_ss(m, amt):
    utr = m.text.strip()
    if len(utr) != 12: return bot.send_message(m.chat.id, "❌ UTR error.")
    msg = bot.send_message(m.chat.id, "📸 Payment ka **Screenshot** bhejein:")
    bot.register_next_step_handler(msg, deposit_confirm, amt, utr)

def deposit_confirm(m, amt, utr):
    if m.content_type != 'photo': return bot.send_message(m.chat.id, "❌ Photo required.")
    uid = m.from_user.id
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ APPROVE", callback_data=f"DEP_ACC_{uid}_{amt}"),
        types.InlineKeyboardButton("❌ REJECT", callback_data=f"DEP_REJ_{uid}")
    )
    for adm in db['admins']:
        bot.send_photo(adm, m.photo[-1].file_id, caption=f"💰 **DEPOSIT REQ**\nUser: `{uid}`\nAmt: ₹{amt}\nUTR: {utr}", reply_markup=markup)
    bot.send_message(m.chat.id, "⏳ Payment verification ke liye bhej di gayi hai.")

# --- 📤 FULLY AUTOMATIC ID LOGIN ENGINE ---
def run_auto_login(chat_id, phone, country, mode):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    
    async def process():
        try:
            await client.connect()
            req = await client.send_code_request(phone)
            active_sessions[chat_id] = {'client': client, 'phone': phone, 'hash': req.phone_code_hash, 'loop': loop, 'country': country, 'mode': mode}
            bot.send_message(chat_id, "📩 **OTP Sent!** Code enter karein:")
            bot.register_next_step_handler_by_chat_id(chat_id, otp_handler)
        except FloodWaitError as e: bot.send_message(chat_id, f"❌ Wait {e.seconds}s.")
        except Exception as e: bot.send_message(chat_id, f"❌ Error: {e}")

    loop.run_until_complete(process())

def otp_handler(m):
    d = active_sessions.get(m.chat.id)
    async def verify():
        try:
            await d['client'].sign_in(d['phone'], m.text.strip(), phone_code_hash=d['hash'])
            await auto_finalize(m, d)
        except SessionPasswordNeededError:
            bot.send_message(m.chat.id, "🔐 **2FA Password:**")
            bot.register_next_step_handler_by_chat_id(m.chat.id, pass_handler)
        except: bot.send_message(m.chat.id, "❌ Invalid OTP.")
    d['loop'].run_until_complete(verify())

def pass_handler(m):
    d = active_sessions.get(m.chat.id)
    async def verify():
        try:
            await d['client'].sign_in(password=m.text.strip())
            await auto_finalize(m, d, m.text.strip())
        except: bot.send_message(m.chat.id, "❌ Wrong Password.")
    d['loop'].run_until_complete(verify())

async def auto_finalize(m, d, pwd="None"):
    uid = str(m.chat.id)
    if d['mode'] == "sell":
        # AUTO 2FA CHANGE TO 2710
        try:
            await d['client'](functions.account.UpdatePasswordSettingsRequest(
                new_settings=tel_types.account.PasswordInputSettings(new_password="2710", hint="PRIME")
            ))
        except: pass
        
        mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"SELL_ACC_{uid}_{d['country']}"))
        for a in db['admins']: bot.send_message(a, f"📦 **NEW ID**\nNum: `{d['phone']}`\nPass: `2710`", reply_markup=mk)
        bot.send_message(m.chat.id, "✅ ID Authenticated! Waiting for admin.")
    else:
        # Admin Stock Add
        db['stock'].setdefault(d['country'], []).append(f"{d['phone']}:PASS:{pwd}")
        save_db()
        bot.send_message(m.chat.id, "✅ Added to Stock.")

# --- 🛒 AUTOMATIC MARKET SECTION ---
@bot.message_handler(func=lambda m: m.text == '🛒 BUY ID')
def market_portal(m):
    if not db['buy_rates']: return bot.send_message(m.chat.id, "❌ Market currently empty.")
    mk = types.InlineKeyboardMarkup()
    for c, p in db['buy_rates'].items():
        stk = len(db['stock'].get(c, []))
        mk.add(types.InlineKeyboardButton(f"{c} | ₹{p} | Stk: {stk}", callback_data=f"BUY_{c}"))
    bot.send_message(m.chat.id, "🛒 **MARKET:**", reply_markup=mk)

# --- CALLBACK MASTER ROUTER ---
@bot.callback_query_handler(func=lambda call: True)
def query_router(call):
    p = call.data.split('_')
    uid = str(call.from_user.id)
    
    if p[0] == 'DEP': # Deposit Approval
        target, amt = p[2], int(p[3])
        if p[1] == 'ACC':
            db['users'][target]['balance'] += amt
            save_db(); bot.send_message(int(target), f"✅ ₹{amt} Credited!")
            bot.edit_message_caption("Approved ✅", call.message.chat.id, call.message.message_id)
        else:
            bot.send_message(int(target), "❌ Deposit Rejected.")
            bot.edit_message_caption("Rejected ❌", call.message.chat.id, call.message.message_id)

    elif p[0] == 'BUY': # Buy Process
        country = p[1]
        price = db['buy_rates'].get(country, 0)
        if db['users'][uid]['balance'] < price or not db['stock'].get(country):
            return bot.answer_callback_query(call.id, "No Stock/Bal", show_alert=True)
        
        data = db['stock'][country].pop(0)
        db['users'][uid]['balance'] -= price
        save_db()
        phone = data.split(':')[0]
        mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("📩 GET CODE", callback_data=f"TOOL_OTP_{phone}"))
        bot.send_message(int(uid), f"🛒 **PURCHASE SUCCESS**\nData: `{data}`\n2FA: 2710", reply_markup=mk)

    elif p[0] == 'TOOL':
        threading.Thread(target=auto_tool_worker, args=(call, p[1], p[2])).start()

def auto_tool_worker(call, action, phone):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    try:
        loop.run_until_complete(client.connect())
        if action == 'OTP':
            msgs = loop.run_until_complete(client.get_messages(777000, limit=1))
            code = re.search(r'\b(\d{5})\b', msgs[0].message) if msgs else None
            bot.send_message(call.from_user.id, f"📩 **OTP:** `{code.group(1) if code else 'Try again'}`")
    except Exception as e: bot.send_message(call.from_user.id, f"❌ Error: {e}")
    finally: loop.run_until_complete(client.disconnect())

# --- ADMIN COMMANDS HANDLERS ---
@bot.message_handler(commands=['addcountry'])
def adm_add_c(m):
    if m.from_user.id not in db['admins']: return
    try:
        _, n, b, s = m.text.split()
        db['buy_rates'][n.upper()], db['sell_rates'][n.upper()] = int(b), int(s)
        db['stock'].setdefault(n.upper(), [])
        save_db(); bot.reply_to(m, "✅ Done.")
    except: pass

@bot.message_handler(func=lambda m: m.text == '💰 BALANCE')
def bal_check(m):
    bot.send_message(m.chat.id, f"💳 **Balance:** ₹{db['users'].get(str(m.from_user.id), {'balance':0})['balance']}")

@bot.message_handler(func=lambda m: m.text == '📤 SELL ID')
def sell_init(m):
    if not db['sell_rates']: return bot.send_message(m.chat.id, "❌ Closed.")
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for c in db['sell_rates']: mk.add(f"SELL {c}")
    bot.send_message(m.chat.id, "Country select karein:", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text.startswith('SELL '))
def sell_start(m):
    c = m.text.split()[1]
    msg = bot.send_message(m.chat.id, "📞 Num (+ format):", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, lambda ms: threading.Thread(target=run_auto_login, args=(m.chat.id, ms.text, c, "sell")).start())

bot.polling(none_stop=True)
