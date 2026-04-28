import telebot
from telebot import types
from telethon import TelegramClient
import asyncio
import time
import os
from flask import Flask
from threading import Thread

# --- RENDER WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "BOT IS ONLINE!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- CONFIGURATION ---
TOKEN = '8692935006:AAFGFN6aeecPubPdd821zq-CmQnZzMtySsw' 
API_ID = 35155488
API_HASH = '9ee6b40363f94481d48dea8a3a871728'
OWNER_ID = 7634311488 
LOG_CHANNEL_ID = -1003901746920 

bot = telebot.TeleBot(TOKEN)

# DATABASE (IN-MEMORY)
db = {
    'users': {}, 
    'admins': [OWNER_ID], 
    'stock': [], 
    'sell_rates': {'INDIA': 25}, 
    'buy_rates': {'INDIA': 40}
}
active_clients = {}

def is_admin(uid): return uid in db['admins']

def post_to_logs(text):
    try: bot.send_message(LOG_CHANNEL_ID, f"📢 **SYSTEM UPDATE**\n\n{text}", parse_mode="Markdown")
    except: print("LOG ERROR!")

# --- START MENU ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if uid not in db['users']: db['users'][uid] = {'balance': 0}
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('💰 **BALANCE**', '📥 **DEPOSIT**', '📤 **SELL ID**', '🛒 **BUY ACCOUNT**', '📞 **SUPPORT**')
    bot.send_message(message.chat.id, "🔥 **PRIME OTP BOT IS READY**\n\n**SELECT AN OPTION:**", parse_mode="Markdown", reply_markup=markup)

# --- ADMIN PANEL (FULL CONTROL) ---
@bot.message_handler(commands=['admin'])
def admin_p(message):
    if not is_admin(message.from_user.id): return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ **ADD COUNTRY**", callback_data="adm_add_c"),
        types.InlineKeyboardButton("❌ **DEL COUNTRY**", callback_data="adm_del_c"),
        types.InlineKeyboardButton("💰 **EDIT SELL PRICE**", callback_data="adm_edit_sell"),
        types.InlineKeyboardButton("🛒 **EDIT BUY PRICE**", callback_data="adm_edit_buy"),
        types.InlineKeyboardButton("📦 **VIEW STOCK**", callback_data="adm_view_stock"),
        types.InlineKeyboardButton("👤 **USERS LIST**", callback_data="adm_users")
    )
    bot.send_message(message.chat.id, "👑 **PRIME ADMIN CONTROL PANEL**\n\n**USE COMMANDS OR BUTTONS:**\n`/addbal ID AMT` | `/cutbal ID AMT`", parse_mode="Markdown", reply_markup=markup)

# --- DYNAMIC ADMIN HANDLERS ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('adm_'))
def admin_callbacks(call):
    uid = call.message.chat.id
    if call.data == "adm_add_c":
        msg = bot.send_message(uid, "🌍 **ENTER COUNTRY NAME TO ADD:**")
        bot.register_next_step_handler(msg, process_add_country)
    elif call.data == "adm_del_c":
        msg = bot.send_message(uid, "🗑️ **ENTER COUNTRY NAME TO DELETE:**")
        bot.register_next_step_handler(msg, process_del_country)
    elif call.data == "adm_edit_sell":
        msg = bot.send_message(uid, "💰 **FORMAT: COUNTRY PRICE (E.G. INDIA 30)**")
        bot.register_next_step_handler(msg, process_edit_sell)
    elif call.data == "adm_edit_buy":
        msg = bot.send_message(uid, "🛒 **FORMAT: COUNTRY PRICE (E.G. INDIA 50)**")
        bot.register_next_step_handler(msg, process_edit_buy)
    elif call.data == "adm_view_stock":
        text = "📦 **CURRENT STOCK:**\n\n" + "\n".join([f"📱 {i['phone']} | {i['country']}" for i in db['stock']])
        bot.send_message(uid, text if len(db['stock']) > 0 else "📦 **STOCK IS EMPTY!**")

def process_add_country(message):
    c = message.text.strip().upper()
    db['sell_rates'][c] = 20; db['buy_rates'][c] = 40
    bot.send_message(message.chat.id, f"✅ **{c} ADDED WITH DEFAULT RATES!**")

def process_del_country(message):
    c = message.text.strip().upper()
    if c in db['sell_rates']: 
        del db['sell_rates'][c]; del db['buy_rates'][c]
        bot.send_message(message.chat.id, f"✅ **{c} REMOVED!**")
    else: bot.send_message(message.chat.id, "❌ **NOT FOUND!**")

def process_edit_sell(message):
    try:
        c, p = message.text.split()
        db['sell_rates'][c.upper()] = int(p)
        bot.send_message(message.chat.id, f"✅ **SELLING PRICE FOR {c.upper()} SET TO ₹{p}**")
    except: bot.send_message(message.chat.id, "❌ **FORMAT ERROR!**")

def process_edit_buy(message):
    try:
        c, p = message.text.split()
        db['buy_rates'][c.upper()] = int(p)
        bot.send_message(message.chat.id, f"✅ **BUYING PRICE FOR {c.upper()} SET TO ₹{p}**")
    except: bot.send_message(message.chat.id, "❌ **FORMAT ERROR!**")

# --- SELLING LOGIC (FIXED ASYNC) ---
@bot.message_handler(func=lambda message: message.text == '📤 **SELL ID**')
def sell_init(message):
    countries = ", ".join(db['sell_rates'].keys())
    msg = bot.send_message(message.chat.id, f"🌍 **AVAILABLE COUNTRIES:**\n`{countries}`\n\n**ENTER COUNTRY:**")
    bot.register_next_step_handler(msg, sell_step_2)

def sell_step_2(message):
    country = message.text.strip().upper()
    if country not in db['sell_rates']: return bot.send_message(message.chat.id, "❌ **WE DON'T BUY THIS COUNTRY!**")
    msg = bot.send_message(message.chat.id, f"📞 **SEND {country} NUMBER (+...):**")
    bot.register_next_step_handler(msg, sell_step_3, country)

def sell_step_3(message, country):
    phone = message.text.strip()
    bot.send_message(message.chat.id, "⏳ **CONNECTING...**")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    active_clients[message.chat.id] = {'client': client, 'phone': phone, 'country': country, 'loop': loop}
    try:
        loop.run_until_complete(client.connect())
        req = loop.run_until_complete(client.send_code_request(phone))
        active_clients[message.chat.id]['hash'] = req.phone_code_hash
        msg = bot.send_message(message.chat.id, "📩 **ENTER OTP:**")
        bot.register_next_step_handler(msg, sell_step_4)
    except Exception as e: bot.send_message(message.chat.id, f"❌ **ERROR: {str(e).upper()}**")

def sell_step_4(message):
    otp = message.text.strip()
    data = active_clients.get(message.chat.id)
    loop = data['loop']
    try:
        loop.run_until_complete(data['client'].sign_in(data['phone'], otp, phone_code_hash=data['hash']))
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ **APPROVE & PAY**", callback_data=f"sapp_{message.from_user.id}_{data['country']}_{data['phone']}"))
        for adm in db['admins']:
            bot.send_message(adm, f"🔔 **SELL REQ**\nUSER: `{message.from_user.id}`\nCOUNTRY: {data['country']}\nNUM: `{data['phone']}`", reply_markup=markup)
        bot.send_message(message.chat.id, "⏳ **VERIFIED! WAIT FOR ADMIN.**")
    except Exception as e: bot.send_message(message.chat.id, f"❌ **FAIL: {str(e).upper()}**")

# --- CALLBACKS FOR APPROVAL ---
@bot.callback_query_handler(func=lambda call: not call.data.startswith('adm_'))
def handle_approvals(call):
    p = call.data.split('_')
    if p[0] == 'sapp':
        uid, country, phone = int(p[1]), p[2], p[3]
        rate = db['sell_rates'].get(country, 25)
        db['users'][uid]['balance'] += rate
        db['stock'].append({'phone': phone, 'country': country})
        bot.send_message(uid, f"✅ **ID APPROVED! ₹{rate} ADDED.**")
        post_to_logs(f"📤 **ID SOLD**\nCOUNTRY: {country}\nPAYOUT: ₹{rate}")
        bot.edit_message_text("✅ **PAID**", call.message.chat.id, call.message.message_id)

# --- BALANCE COMMANDS ---
@bot.message_handler(commands=['addbal'])
def ab(message):
    if is_admin(message.from_user.id):
        try:
            _, u, a = message.text.split()
            db['users'][int(u)]['balance'] += int(a)
            bot.reply_to(message, "✅ **DONE**")
        except: bot.reply_to(message, "Usage: `/addbal ID AMT`")

if __name__ == "__main__":
    keep_alive()
    bot.polling(none_stop=True)
