import telebot
from telebot import types
from telethon import TelegramClient
import asyncio
import os
from flask import Flask
from threading import Thread

# --- WEB SERVER (RENDER STABILITY) ---
app = Flask('')
@app.route('/')
def home(): return "PRIME OTP BOT IS LIVE"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- CONFIGURATION ---
TOKEN = '8692935006:AAFGFN6aeecPubPdd821zq-CmQnZzMtySsw' 
API_ID = 35155488
API_HASH = '9ee6b40363f94481d48dea8a3a871728'
OWNER_ID = 7634311488 
LOG_CHANNEL_ID = -1002364843054 
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

if not os.path.exists('sessions'): os.makedirs('sessions')

def is_admin(uid): return uid in db['admins'] or uid == OWNER_ID

def check_join(uid):
    for cid in CHANNELS:
        try:
            m = bot.get_chat_member(cid, uid)
            if m.status in ['left', 'kicked']: return False
        except: return False
    return True

def send_log(text):
    try: bot.send_message(LOG_CHANNEL_ID, f"📝 **SYSTEM LOG**\n\n{text}")
    except: pass

# --- KEYBOARDS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('💰 BALANCE', '📥 DEPOSIT', '📤 SELL ID', '🛒 BUY ID', '📞 SUPPORT')
    return markup

# --- START & FORCE JOIN ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if uid not in db['users']: db['users'][uid] = {'balance': 0}
    
    if not check_join(uid):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 SUPPORT GROUP", url="https://t.me/PRIME_OTP_SUPPORT_GROUP"))
        markup.add(types.InlineKeyboardButton("👤 OWNER", url="https://t.me/god_abhay"))
        markup.add(types.InlineKeyboardButton("✅ CHECK JOIN", callback_data="check_joined"))
        return bot.send_message(message.chat.id, "⚠️ **ACCESS DENIED!**\n\nPlease join our channels to use the bot.", reply_markup=markup)
    
    bot.send_message(message.chat.id, "🔥 **PRIME OTP BOT READY**", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: call.data == "check_joined")
def check_cb(call):
    if check_join(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "✅ **ACCESS GRANTED!**", reply_markup=main_menu())
    else: bot.answer_callback_query(call.id, "❌ Join all channels first!", show_alert=True)

# --- DEPOSIT (FIXED WITH REJECT/LOGS/USERID) ---
@bot.message_handler(func=lambda m: 'DEPOSIT' in m.text)
def dep_1(message):
    if not check_join(message.from_user.id): return
    msg = bot.send_message(message.chat.id, "💵 Enter Deposit Amount:")
    bot.register_next_step_handler(msg, dep_2)

def dep_2(message):
    try:
        amt = int(message.text)
        bot.send_message(message.chat.id, f"💳 Pay here: `{db['upi']}`\n\nSend 12-digit UTR:")
        bot.register_next_step_handler(message, dep_3, amt)
    except: bot.send_message(message.chat.id, "❌ Valid amount only!")

def dep_3(message, amt):
    utr = message.text.strip()
    if len(utr) != 12: return bot.send_message(message.chat.id, "❌ Invalid UTR (12 digits required).")
    bot.send_message(message.chat.id, "📸 Send Payment Screenshot:")
    bot.register_next_step_handler(message, dep_final, amt, utr)

def dep_final(message, amt, utr):
    if message.content_type != 'photo': return bot.send_message(message.chat.id, "❌ Send a photo.")
    uid = message.from_user.id
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ APPROVE", callback_data=f"da_{uid}_{amt}"),
        types.InlineKeyboardButton("❌ REJECT", callback_data=f"dr_{uid}_{amt}")
    )
    for a in db['admins']:
        bot.send_photo(a, message.photo[-1].file_id, 
                       caption=f"🔔 **DEPOSIT REQ**\nUser: `{uid}`\nAmt: ₹{amt}\nUTR: `{utr}`", 
                       reply_markup=markup)
    bot.send_message(message.chat.id, "⏳ Sent to Admin! Please wait.")

# --- AUTO-LOGIN SELL SYSTEM ---
@bot.message_handler(func=lambda m: m.text.startswith('SELL '))
def sell_otp_req(message):
    if not check_join(message.from_user.id): return
    country = message.text.split()[1]
    msg = bot.send_message(message.chat.id, f"📞 Enter {country} Number (+...):", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, sell_otp_send, country)

def sell_otp_send(message, country):
    phone = message.text.strip()
    bot.send_message(message.chat.id, "⏳ Requesting OTP...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    active_logins[message.chat.id] = {'client': client, 'phone': phone, 'loop': loop, 'country': country}
    try:
        loop.run_until_complete(client.connect())
        req = loop.run_until_complete(client.send_code_request(phone))
        active_logins[message.chat.id]['hash'] = req.phone_code_hash
        msg = bot.send_message(message.chat.id, "📩 **OTP SENT!** Enter code:")
        bot.register_next_step_handler(msg, sell_verify_otp)
    except Exception as e: bot.send_message(message.chat.id, f"❌ Error: {e}")

def sell_verify_otp(message):
    otp = message.text.strip()
    d = active_logins.get(message.chat.id)
    try:
        d['loop'].run_until_complete(d['client'].sign_in(d['phone'], otp, phone_code_hash=d['hash']))
        uid = message.from_user.id
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ APPROVE SELL", callback_data=f"sa_{uid}_{d['country']}_{d['phone']}"))
        for a in db['admins']:
            bot.send_message(a, f"📦 **SELL REQ**\nUser: `{uid}`\nNum: `{d['phone']}`\nCountry: {d['country']}", reply_markup=markup)
        bot.send_message(message.chat.id, "✅ Login success! Admin will pay soon.")
    except: bot.send_message(message.chat.id, "❌ OTP Wrong.")

# --- ADMIN POWER ---
@bot.message_handler(commands=['admin'])
def admin_p(message):
    if not is_admin(message.from_user.id): return
    bot.send_message(message.chat.id, "👑 **ADMIN PANEL**\n/setbuy C PRICE\n/setsell C PRICE\n/addstock C DATA\n/removestock C\n/list")

@bot.message_handler(commands=['setbuy', 'setsell', 'addstock', 'removestock', 'list'])
def admin_actions(message):
    if not is_admin(message.from_user.id): return
    cmd = message.text.split()
    try:
        if '/setbuy' in cmd[0]:
            db['buy_rates'][cmd[1].upper()] = int(cmd[2])
            bot.reply_to(message, "✅ Set Buy Price.")
        elif '/setsell' in cmd[0]:
            db['sell_rates'][cmd[1].upper()] = int(cmd[2])
            bot.reply_to(message, "✅ Set Sell Price.")
        elif '/addstock' in cmd[0]:
            c = cmd[1].upper()
            if c not in db['stock']: db['stock'][c] = []
            db['stock'][c].append(cmd[2])
            bot.reply_to(message, f"✅ Stock added to {c}.")
        elif '/list' in cmd[0]:
            res = "📊 **STATUS**\n\n"
            for c in db['buy_rates']:
                res += f"{c} | Buy: ₹{db['buy_rates'][c]} | Stock: {len(db['stock'].get(c, []))}\n"
            bot.send_message(message.chat.id, res if db['buy_rates'] else "Empty.")
    except: bot.reply_to(message, "❌ Format error!")

# --- CALLBACKS (LOGS INTEGRATED) ---
@bot.callback_query_handler(func=lambda call: True)
def calls(call):
    p = call.data.split('_')
    # Deposit Actions
    if p[0] == 'da':
        uid, amt = int(p[1]), int(p[2])
        db['users'][uid]['balance'] += amt
        bot.send_message(uid, f"✅ **₹{amt} CREDITED!**")
        bot.edit_message_caption(f"Approved ✅", call.message.chat.id, call.message.message_id)
        send_log(f"💰 **DEPOSIT APPROVED**\nUser: `{uid}`\nAmt: ₹{amt}")
    elif p[0] == 'dr':
        uid = int(p[1])
        bot.send_message(uid, "❌ **DEPOSIT REJECTED!**")
        bot.edit_message_caption(f"Rejected ❌", call.message.chat.id, call.message.message_id)
        send_log(f"❌ **DEPOSIT REJECTED**\nUser: `{uid}`")
    # Sell/Buy Actions
    elif p[0] == 'sa':
        uid, country, phone = int(p[1]), p[2], p[3]
        rate = db['sell_rates'].get(country, 0)
        db['users'][uid]['balance'] += rate
        bot.send_message(uid, f"✅ **ID SOLD!** ₹{rate} added.")
        bot.edit_message_text(f"Paid ₹{rate} to `{uid}` ✅", call.message.chat.id, call.message.message_id)
        send_log(f"📤 **ID SOLD**\nUser: `{uid}`\nCountry: {country}\nPrice: ₹{rate}")
    elif p[0] == 'buy':
        c = p[1]
        uid = call.from_user.id
        price = db['buy_rates'].get(c, 0)
        if db['users'].get(uid, {}).get('balance', 0) < price or not db['stock'].get(c):
            return bot.answer_callback_query(call.id, "No Balance/Stock!", show_alert=True)
        data = db['stock'][c].pop(0)
        db['users'][uid]['balance'] -= price
        bot.send_message(uid, f"✅ **BUY SUCCESS!**\n\n`{data}`")
        send_log(f"🛒 **ID BOUGHT**\nUser: `{uid}`\nCountry: {c}\nPrice: ₹{price}")

# --- BALANCE & SUPPORT ---
@bot.message_handler(func=lambda m: 'BALANCE' in m.text)
def check_bal(message):
    b = db['users'].get(message.from_user.id, {}).get('balance', 0)
    bot.send_message(message.chat.id, f"💳 Balance: ₹{b}")

@bot.message_handler(func=lambda m: 'SUPPORT' in m.text)
def sup(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👤 OWNER", url="https://t.me/god_abhay"),
               types.InlineKeyboardButton("📢 SUPPORT GROUP", url="https://t.me/PRIME_OTP_SUPPORT_GROUP"))
    bot.send_message(message.chat.id, "🚩 Support:", reply_markup=markup)

if __name__ == "__main__":
    keep_alive()
    bot.polling(none_stop=True)
