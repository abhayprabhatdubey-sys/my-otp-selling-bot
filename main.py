import telebot
from telebot import types
from telethon import TelegramClient, functions, types as tel_types
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
import asyncio
import os
import threading
import re
import time
from flask import Flask

# --- HOSTING PERSISTENCE ---
app = Flask('')
@app.route('/')
def home(): return "<h1>MASTER BOT v9.0 ONLINE 🚀</h1>"
def run(): app.run(host='0.0.0.0', port=8080)
threading.Thread(target=run, daemon=True).start()

# --- BOT CONFIGURATION ---
TOKEN = '8692935006:AAFGFN6aeecPubPdd821zq-CmQnZzMtySsw'
API_ID = 35155488
API_HASH = '9ee6b40363f94481d48dea8a3a871728'
OWNER_ID = 7634311488

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# --- MULTI-FEATURE DATABASE structure ---
db = {
    'users': {}, 
    'admins': [OWNER_ID], 
    'upi': 'abhay-op.315@ptyes', 
    'stock': {}, 
    'sell_rates': {}, 
    'buy_rates': {},
    'pending_deposits': {},
    'stats': {'total_sales': 0, 'total_buys': 0}
}

if not os.path.exists('sessions'): os.makedirs('sessions')
active_logins = {}

# --- CORE PERMISSIONS ---
def is_admin(uid):
    return uid in db['admins'] or uid == OWNER_ID

# --- KEYBOARD INTERFACES ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('💰 BALANCE', '📥 DEPOSIT')
    markup.add('📤 SELL ID', '🛒 BUY ID')
    markup.add('📞 SUPPORT', '📊 MY STATS')
    return markup

def admin_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🌍 Add Country", callback_data="adm_addc"),
        types.InlineKeyboardButton("➕ Add Stock", callback_data="adm_adds"),
        types.InlineKeyboardButton("👤 Add Admin", callback_data="adm_adda"),
        types.InlineKeyboardButton("💳 Change UPI", callback_data="adm_upi"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="adm_bc")
    )
    return markup

# --- START COMMAND ---
@bot.message_handler(commands=['start'])
def welcome(message):
    uid = message.from_user.id
    if uid not in db['users']:
        db['users'][uid] = {'balance': 0, 'bought': 0, 'sold': 0, 'joined': time.ctime()}
    bot.send_message(message.chat.id, "🔥 **PRIME MASTER BOT v9.0 ACTIVE**\n\nAdvanced features loaded. No Force Join/Referral enabled.", reply_markup=main_menu())

# --- FEATURE 1: ADVANCED ADMIN CONTROL ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message.from_user.id): return
    bot.send_message(message.chat.id, "👑 **Welcome to Admin Control Center**\nUse commands or buttons below:", reply_markup=admin_menu())

@bot.message_handler(commands=['addbal'])
def add_bal(m):
    if not is_admin(m.from_user.id): return
    try:
        _, target_id, amt = m.text.split()
        db['users'][int(target_id)]['balance'] += int(amt)
        bot.send_message(int(target_id), f"🎁 **Credit Alert:** ₹{amt} added to your balance.")
        bot.reply_to(m, "Done.")
    except: bot.reply_to(m, "Usage: `/addbal ID AMT` ")

# --- FEATURE 2: LOGIN ENGINE & AUTO 2FA (2710) ---
def start_login_worker(chat_id, phone, country, mode):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    
    async def process():
        await client.connect()
        try:
            sent_code = await client.send_code_request(phone)
            active_logins[chat_id] = {'client': client, 'phone': phone, 'hash': sent_code.phone_code_hash, 'loop': loop, 'country': country, 'mode': mode}
            msg = bot.send_message(chat_id, "📩 **OTP Sent!** Code enter karein:")
            bot.register_next_step_handler(msg, otp_collector)
        except Exception as e:
            bot.send_message(chat_id, f"❌ Error: {str(e)}")

    loop.run_until_complete(process())

def otp_collector(message):
    uid = message.chat.id
    d = active_logins.get(uid)
    if not d: return
    
    async def verify():
        try:
            await d['client'].sign_in(d['phone'], message.text.strip(), phone_code_hash=d['hash'])
            await finalize_identity(message, d)
        except SessionPasswordNeededError:
            msg = bot.send_message(uid, "🔐 **2FA Password required:**")
            bot.register_next_step_handler(msg, password_collector)
        except Exception as e:
            bot.send_message(uid, f"❌ OTP Error: {str(e)}")

    d['loop'].run_until_complete(verify())

def password_collector(message):
    uid = message.chat.id
    d = active_logins.get(uid)
    async def verify():
        try:
            await d['client'].sign_in(password=message.text.strip())
            await finalize_identity(message, d, message.text.strip())
        except Exception as e:
            bot.send_message(uid, "❌ Wrong Password.")
    d['loop'].run_until_complete(verify())

async def finalize_identity(message, d, old_pwd="None"):
    uid = message.chat.id
    if d['mode'] == "sell":
        # Feature 3: Auto 2FA Change to 2710
        try:
            await d['client'](functions.account.UpdatePasswordSettingsRequest(
                new_settings=tel_types.account.PasswordInputSettings(new_password="2710", hint="bot")
            ))
        except: pass
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"sa_{uid}_{d['country']}"),
                   types.InlineKeyboardButton("❌ REJECT", callback_data=f"sr_{uid}"))
        
        for adm in db['admins']:
            bot.send_message(adm, f"📦 **NEW SALE**\nUser: `{uid}`\nNum: `{d['phone']}`\nPass: `2710`", reply_markup=markup)
        bot.send_message(uid, "✅ ID Verified! Waiting for admin approval.")
    else:
        db['stock'].setdefault(d['country'], []).append(f"{d['phone']}:PASS:{old_pwd}")
        bot.send_message(uid, f"✅ Added to {d['country']} stock.")

# --- FEATURE 4: STRICT DEPOSIT (UTR & SS CHECK) ---
@bot.message_handler(func=lambda m: m.text == '📥 DEPOSIT')
def deposit_start(m):
    msg = bot.send_message(m.chat.id, "💵 **Deposit Amount:**")
    bot.register_next_step_handler(msg, deposit_amt_handler)

def deposit_amt_handler(m):
    if not m.text.isdigit(): return bot.send_message(m.chat.id, "❌ Valid number likho.")
    amt = m.text
    msg = bot.send_message(m.chat.id, f"💳 Pay to: `{db['upi']}`\n\nAb **12-digit UTR** bhejein:")
    bot.register_next_step_handler(msg, deposit_utr_handler, amt)

def deposit_utr_handler(m, amt):
    utr = m.text.strip()
    if len(utr) != 12 or not utr.isdigit():
        return bot.send_message(m.chat.id, "❌ **Strict Check:** UTR sirf 12-digit ka hona chahiye.")
    msg = bot.send_message(m.chat.id, "📸 Payment ka **Screenshot** bhejein:")
    bot.register_next_step_handler(msg, deposit_ss_handler, amt, utr)

def deposit_ss_handler(m, amt, utr):
    if m.content_type != 'photo': return bot.send_message(m.chat.id, "❌ Photo missing.")
    uid = m.from_user.id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"da_{uid}_{amt}"),
               types.InlineKeyboardButton("❌ REJECT", callback_data=f"dr_{uid}"))
    for adm in db['admins']:
        bot.send_photo(adm, m.photo[-1].file_id, caption=f"🔔 **DEPOSIT**\nUser: `{uid}`\nAmt: ₹{amt}\nUTR: {utr}", reply_markup=markup)
    bot.send_message(m.chat.id, "⏳ Admin verification pending.")

# --- FEATURE 5: BUY ID (GET CODE/LOGOUT) ---
@bot.message_handler(func=lambda m: m.text == '🛒 BUY ID')
def buy_market(m):
    markup = types.InlineKeyboardMarkup()
    for c, p in db['buy_rates'].items():
        stk = len(db['stock'].get(c, []))
        markup.add(types.InlineKeyboardButton(f"{c} - ₹{p} (Stk: {stk})", callback_data=f"buyid_{c}"))
    bot.send_message(m.chat.id, "🛒 **MARKET RATES:**", reply_markup=markup)

# --- CALLBACKS FOR ALL ACTIONS ---
@bot.callback_query_handler(func=lambda call: True)
def central_callbacks(call):
    p = call.data.split('_')
    uid = call.from_user.id
    
    if p[0] == 'da': # Dep Approve
        target, amt = int(p[1]), int(p[2])
        db['users'][target]['balance'] += amt
        bot.send_message(target, f"✅ ₹{amt} credited!")
        bot.edit_message_caption("Approved ✅", call.message.chat.id, call.message.message_id)
        
    elif p[0] == 'buyid':
        country = p[1]
        price = db['buy_rates'].get(country, 0)
        if db['users'][uid]['balance'] < price or not db['stock'].get(country):
            return bot.answer_callback_query(call.id, "No Balance/Stock!", show_alert=True)
        
        data = db['stock'][country].pop(0)
        db['users'][uid]['balance'] -= price
        phone = data.split(':')[0]
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📩 GET CODE", callback_data=f"gotp_{phone}"),
                   types.InlineKeyboardButton("🚪 LOGOUT", callback_data=f"lout_{phone}"))
        bot.send_message(uid, f"🛒 **PURCHASED**\nData: `{data}`\nPass: 2710 (if changed)", reply_markup=markup)

    elif p[0] == 'sa': # Sell Approve
        target, country = int(p[1]), p[2]
        rate = db['sell_rates'].get(country, 0)
        db['users'][target]['balance'] += rate
        bot.send_message(target, f"✅ Your Sale for {country} approved! ₹{rate} added.")
        bot.edit_message_text("Sale Approved ✅", call.message.chat.id, call.message.message_id)

# --- FEATURE 6: STATS & INFO ---
@bot.message_handler(func=lambda m: m.text == '📊 MY STATS')
def user_stats(m):
    u = db['users'].get(m.from_user.id, {})
    bot.send_message(m.chat.id, f"👤 **USER STATS**\n\n💰 Balance: ₹{u.get('balance',0)}\n📅 Joined: {u.get('joined')}")

@bot.message_handler(func=lambda m: m.text == '💰 BALANCE')
def bal_check(m):
    bot.send_message(m.chat.id, f"💳 **Current Balance:** ₹{db['users'].get(m.from_user.id, {}).get('balance',0)}")

@bot.message_handler(func=lambda m: m.text == '📤 SELL ID')
def sell_init(m):
    if not db['sell_rates']: return bot.send_message(m.chat.id, "❌ Market Closed.")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for c in db['sell_rates']: markup.add(f"SELL {c}")
    bot.send_message(m.chat.id, "Select Country:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text.startswith('SELL '))
def sell_start(m):
    c = m.text.split()[1]
    msg = bot.send_message(m.chat.id, "📞 Enter Number (+ format):", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, lambda ms: threading.Thread(target=start_login_worker, args=(m.chat.id, ms.text, c, "sell")).start())

@bot.message_handler(func=lambda m: m.text == '📞 SUPPORT')
def supp(m):
    bot.send_message(m.chat.id, "👤 **Owner:** @god_abhay")

bot.polling(none_stop=True)
