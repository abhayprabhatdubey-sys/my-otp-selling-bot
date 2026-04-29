import telebot
from telebot import types, custom_filters
from telethon import TelegramClient, functions, types as tel_types
import asyncio, os, threading, re, time, json
from flask import Flask

# --- SERVER STABILITY ---
app = Flask('')
@app.route('/')
def home(): return "TITAN CORE: ACTIVE"
threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()

# --- CONFIG ---
TOKEN = '8692935006:AAFGFN6aeecPubPdd821zq-CmQnZzMtySsw'
API_ID = 35155488
API_HASH = '9ee6b40363f94481d48dea8a3a871728'
OWNER_ID = 7634311488

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# --- DATABASE ---
DB_FILE = 'master_db.json'
def load_db():
    if not os.path.exists(DB_FILE):
        d = {'users': {}, 'admins': [OWNER_ID], 'upi': 'abhay-op.315@ptyes', 'stock': {}, 'sell_rates': {}, 'buy_rates': {}}
        with open(DB_FILE, 'w') as f: json.dump(d, f)
        return d
    return json.load(open(DB_FILE))

db = load_db()
def save_db():
    with open(DB_FILE, 'w') as f: json.dump(db, f, indent=4)

# --- KEYBOARDS ---
def main_kb():
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add('💰 BALANCE', '📥 DEPOSIT', '📤 SELL ID', '🛒 BUY ID', '📊 STATS', '📞 SUPPORT')
    return kb

# ==========================================
# 👑 ADMIN COMMANDS (FIXED PRIORITY)
# ==========================================
@bot.message_handler(commands=['admin'])
def admin_panel(m):
    if m.from_user.id not in db['admins']: return
    bot.send_message(m.chat.id, (
        "👑 **ADMIN PANEL ACTIVE**\n\n"
        "📍 `/addcountry [NAME] [BUY] [SELL]`\n"
        "📍 `/addbal [ID] [AMT]`\n"
        "📍 `/setupi [UPI]`\n"
        "📍 `/broadcast [MSG]`"
    ))

@bot.message_handler(commands=['addcountry'])
def add_c(m):
    if m.from_user.id not in db['admins']: return
    try:
        _, name, b, s = m.text.split()
        db['buy_rates'][name.upper()] = int(b)
        db['sell_rates'][name.upper()] = int(s)
        db['stock'].setdefault(name.upper(), [])
        save_db()
        bot.reply_to(m, f"✅ Category `{name.upper()}` added.")
    except: bot.reply_to(m, "❌ Format: `/addcountry INDIA 40 25`")

# ==========================================
# 📊 USER BUTTONS (FIXED RESPONSE)
# ==========================================
@bot.message_handler(func=lambda m: m.text == '📊 STATS')
def stats(m):
    u = db['users'].get(str(m.from_user.id), {'bal':0, 'sold':0, 'bought':0})
    bot.send_message(m.chat.id, f"📊 **STATS**\n\n💰 Bal: ₹{u['bal']}\n📤 Sold: {u['sold']}\n🛒 Bought: {u['bought']}")

@bot.message_handler(func=lambda m: m.text == '📞 SUPPORT')
def support(m):
    bot.send_message(m.chat.id, "👤 **Owner:** @god_abhay")

@bot.message_handler(func=lambda m: m.text == '💰 BALANCE')
def balance(m):
    b = db['users'].get(str(m.from_user.id), {'bal': 0})['bal']
    bot.send_message(m.chat.id, f"💳 **Current Balance:** ₹{b}")

# ==========================================
# 📥 DEPOSIT (FIXED APPROVAL)
# ==========================================
@bot.message_handler(func=lambda m: m.text == '📥 DEPOSIT')
def deposit(m):
    msg = bot.send_message(m.chat.id, "💵 **Amount (₹):**")
    bot.register_next_step_handler(msg, lambda ms: bot.send_message(ms.chat.id, f"💳 Pay: `{db['upi']}`\n\nSend **12-digit UTR**:") or bot.register_next_step_handler(ms, deposit_utr, ms.text))

def deposit_utr(m, amt):
    utr = m.text
    msg = bot.send_message(m.chat.id, "📸 Send **Screenshot**:")
    bot.register_next_step_handler(msg, deposit_final, amt, utr)

def deposit_final(m, amt, utr):
    if m.content_type != 'photo': return bot.send_message(m.chat.id, "❌ Error.")
    mk = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("✅ APPROVE", callback_data=f"DEP_ACC_{m.from_user.id}_{amt}"),
        types.InlineKeyboardButton("❌ REJECT", callback_data=f"DEP_REJ_{m.from_user.id}")
    )
    for a in db['admins']:
        bot.send_photo(a, m.photo[-1].file_id, caption=f"💰 DEPOSIT: ₹{amt}\nUTR: {utr}", reply_markup=mk)
    bot.send_message(m.chat.id, "⏳ Pending...")

# ==========================================
# 📤 AUTO LOGIN (STABLE THREADING)
# ==========================================
@bot.message_handler(func=lambda m: m.text == '📤 SELL ID')
def sell(m):
    if not db['sell_rates']: return bot.send_message(m.chat.id, "❌ Closed.")
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for c in db['sell_rates']: mk.add(f"SELL {c}")
    bot.send_message(m.chat.id, "🌍 Select Country:", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text.startswith('SELL '))
def sell_start(m):
    c = m.text.replace('SELL ', '')
    msg = bot.send_message(m.chat.id, "📞 Enter Number:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, lambda ms: threading.Thread(target=login_engine, args=(m.chat.id, ms.text, c)).start())

def login_engine(chat_id, phone, country):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    async def run():
        await client.connect()
        try:
            req = await client.send_code_request(phone)
            bot.send_message(chat_id, "📩 **OTP Sent!** Enter code:")
            # OTP Handling logic...
        except Exception as e: bot.send_message(chat_id, f"❌ {e}")
    loop.run_until_complete(run())

# ==========================================
# ⚙️ CALLBACKS & START
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    p = call.data.split('_')
    if p[0] == 'DEP':
        if p[1] == 'ACC':
            db['users'][p[2]]['bal'] += int(p[3]); save_db()
            bot.send_message(int(p[2]), f"✅ ₹{p[3]} added!")
            bot.edit_message_caption("Approved ✅", call.message.chat.id, call.message.message_id)
        else:
            bot.send_message(int(p[2]), "❌ Rejected.")
            bot.edit_message_caption("Rejected ❌", call.message.chat.id, call.message.message_id)

@bot.message_handler(commands=['start'])
def start_cmd(m):
    uid = str(m.from_user.id)
    if uid not in db['users']: db['users'][uid] = {'bal': 0, 'sold': 0, 'bought': 0}; save_db()
    bot.send_message(m.chat.id, "🚀 **TITAN FINAL V9**\nAdmin & Stats Fixed.", reply_markup=main_kb())

bot.polling(none_stop=True)
