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
def home(): return "BOT IS LIVE!"
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

def is_owner(uid): return uid == OWNER_ID
def is_admin(uid): return uid in db['admins'] or uid == OWNER_ID

# --- START & REFERRAL ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    args = message.text.split()
    if uid not in db['users']:
        ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
        db['users'][uid] = {'balance': 0, 'referred_by': ref}
    
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('💰 BALANCE', '📥 DEPOSIT', '📤 SELL ID', '🛒 BUY ID', '👥 REFERRAL', '📞 SUPPORT')
    bot.send_message(message.chat.id, "🔥 PRIME OTP BOT READY", reply_markup=markup)

# --- ADMIN PANEL & COMMANDS ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message.from_user.id): return
    text = (
        "👑 ADMIN CONTROLS\n\n"
        "📈 /setbuy INDIA 40 - Set Buy Price\n"
        "📉 /setsell INDIA 25 - Set Sell Price\n"
        "➕ /addstock INDIA data - Add ID to Stock\n"
        "❌ /removestock INDIA - Clear Stock\n"
        "💳 /changeupi ID - Update Payment UPI\n"
        "👤 /addadmin ID - Add New Admin\n"
        "🚫 /removeadmin ID - Remove Admin\n"
        "📢 /broadcast MSG - Send to all users\n"
        "📜 /list - View Rates & Stock"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['addadmin'])
def add_adm(message):
    if is_owner(message.from_user.id):
        try:
            nid = int(message.text.split()[1])
            if nid not in db['admins']: db['admins'].append(nid)
            bot.reply_to(message, f"✅ Admin {nid} added.")
        except: pass

@bot.message_handler(commands=['changeupi'])
def ch_upi(message):
    if is_admin(message.from_user.id):
        try:
            db['upi'] = message.text.split()[1]
            bot.reply_to(message, f"✅ UPI Updated: `{db['upi']}`")
        except: pass

# --- BUY SYSTEM (STRICT CHECK) ---
@bot.message_handler(func=lambda m: 'BUY ID' in m.text)
def buy_menu(message):
    if not db['buy_rates']:
        return bot.send_message(message.chat.id, "❌ ALL COUNTRIES OUT OF STOCK!")
    markup = types.InlineKeyboardMarkup()
    for c, p in db['buy_rates'].items():
        count = len(db['stock'].get(c, []))
        status = f"({count} left)" if count > 0 else "(OUT OF STOCK)"
        markup.add(types.InlineKeyboardButton(f"{c} - ₹{p} {status}", callback_data=f"buy_{c}"))
    bot.send_message(message.chat.id, "🛒 SELECT COUNTRY:", reply_markup=markup)

# --- SELL SYSTEM (AUTO LOGIN + ADMIN APPROVE) ---
@bot.message_handler(func=lambda m: 'SELL ID' in m.text)
def sell_init(message):
    if not db['sell_rates']:
        return bot.send_message(message.chat.id, "❌ ID SELLING IS DISABLED BY ADMIN.")
    msg = bot.send_message(message.chat.id, "📞 ENTER NUMBER (+91...):")
    bot.register_next_step_handler(msg, sell_step_otp)

def sell_step_otp(message):
    phone = message.text.strip()
    bot.send_message(message.chat.id, "⏳ GETTING OTP...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    active_logins[message.chat.id] = {'client': client, 'phone': phone, 'loop': loop}
    try:
        loop.run_until_complete(client.connect())
        req = loop.run_until_complete(client.send_code_request(phone))
        active_logins[message.chat.id]['hash'] = req.phone_code_hash
        msg = bot.send_message(message.chat.id, "📩 ENTER OTP:")
        bot.register_next_step_handler(msg, sell_verify)
    except: bot.reply_to(message, "❌ Connection Error.")

def sell_verify(message):
    otp = message.text.strip()
    data = active_logins.get(message.chat.id)
    try:
        data['loop'].run_until_complete(data['client'].sign_in(data['phone'], otp, phone_code_hash=data['hash']))
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ LOGIN & APPROVE", callback_data=f"sa_{message.from_user.id}_{data['phone']}"))
        for a in db['admins']:
            bot.send_message(a, f"🔔 SELL REQ: {data['phone']}\nUser: {message.from_user.id}", reply_markup=markup)
        bot.send_message(message.chat.id, "⏳ VERIFIED! WAIT FOR ADMIN APPROVAL.")
    except: bot.reply_to(message, "❌ Login Failed.")

# --- DEPOSIT (12-DIGIT UTR CHECK) ---
@bot.message_handler(func=lambda m: 'DEPOSIT' in m.text)
def dep_start(message):
    msg = bot.send_message(message.chat.id, "💵 ENTER AMOUNT:")
    bot.register_next_step_handler(msg, dep_2)

def dep_2(message):
    try:
        amt = int(message.text)
        bot.send_message(message.chat.id, f"💳 PAY TO: `{db['upi']}`\nSEND 12-DIGIT UTR:")
        bot.register_next_step_handler(message, dep_3, amt)
    except: bot.send_message(message.chat.id, "❌ Invalid Amount.")

def dep_3(message, amt):
    utr = message.text.strip()
    if len(utr) != 12: return bot.send_message(message.chat.id, "❌ REJECTED! UTR MUST BE 12 DIGITS.")
    bot.send_message(message.chat.id, "📸 SEND SCREENSHOT:")
    bot.register_next_step_handler(message, dep_final, amt, utr)

def dep_final(message, amt, utr):
    if message.content_type != 'photo': return bot.send_message(message.chat.id, "❌ Photo Required.")
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"da_{message.from_user.id}_{amt}"))
    for a in db['admins']:
        bot.send_message(a, f"🔔 DEPOSIT REQ: {amt}\nUTR: {utr}", reply_markup=markup)
        bot.send_photo(a, message.photo[-1].file_id)

# --- CALLBACKS (APPROVE/BUY) ---
@bot.callback_query_handler(func=lambda call: True)
def handle_calls(call):
    p = call.data.split('_')
    if p[0] == 'da': # Deposit
        uid, amt = int(p[1]), int(p[2])
        db['users'][uid]['balance'] += amt
        ref = db['users'][uid].get('referred_by')
        if ref and amt >= 100:
            db['users'][ref]['balance'] += 3
            bot.send_message(ref, "🎁 REFERRAL BONUS ₹3 ADDED!")
        bot.send_message(uid, f"✅ ₹{amt} ADDED!")
        bot.edit_message_text("✅ APPROVED", call.message.chat.id, call.message.message_id)
    
    elif p[0] == 'sa': # Sell
        uid, phone = int(p[1]), p[2]
        rate = db['sell_rates'].get('INDIA', 0)
        db['users'][uid]['balance'] += rate
        bot.send_message(uid, f"✅ ID APPROVED! ₹{rate} ADDED.")
        bot.edit_message_text(f"✅ PAID TO {uid}", call.message.chat.id, call.message.message_id)

    elif p[0] == 'buy':
        country = p[1]
        uid = call.from_user.id
        price = db['buy_rates'].get(country, 9999)
        if db['users'][uid]['balance'] < price or not db['stock'].get(country):
            return bot.answer_callback_query(call.id, "❌ OUT OF STOCK OR NO BALANCE", show_alert=True)
        data = db['stock'][country].pop(0)
        db['users'][uid]['balance'] -= price
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 GET CODE AGAIN", callback_data="gc"),
                   types.InlineKeyboardButton("🚪 LOGOUT", callback_data="lo"))
        bot.send_message(uid, f"✅ BOUGHT SUCCESS!\n`{data}`", reply_markup=markup)

# --- BALANCE & SUPPORT ---
@bot.message_handler(func=lambda m: 'BALANCE' in m.text)
def check_bal(message):
    b = db['users'].get(message.from_user.id, {}).get('balance', 0)
    bot.send_message(message.chat.id, f"💳 BALANCE: ₹{b}")

@bot.message_handler(func=lambda m: 'SUPPORT' in m.text)
def support(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👤 OWNER", url="https://t.me/god_abhay"),
               types.InlineKeyboardButton("💬 JOIN GC", url="https://t.me/Team_quorum"))
    bot.send_message(message.chat.id, "🚩 CONTACT SUPPORT:", reply_markup=markup)

if __name__ == "__main__":
    keep_alive()
    bot.remove_webhook()
    bot.polling(none_stop=True)
