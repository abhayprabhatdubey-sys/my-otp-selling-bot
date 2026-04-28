import telebot
from telebot import types
from telethon import TelegramClient
import asyncio
import os
from flask import Flask
from threading import Thread

# --- RENDER WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "BOT IS LIVE!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- CONFIGURATION ---
TOKEN = '8692935006:AAFGFN6aeecPubPdd821zq-CmQnZzMtySsw' 
API_ID = 35155488
API_HASH = '9ee6b40363f94481d48dea8a3a871728'
OWNER_ID = 7634311488 
LOG_CHANNEL_ID = -1003901746920 

bot = telebot.TeleBot(TOKEN)

# DATABASE
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
    bot.send_message(message.chat.id, "🔥 **WELCOME TO PRIME OTP BOT**\n\n**SELECT AN OPTION BELOW:**", parse_mode="Markdown", reply_markup=markup)

# --- ADMIN PANEL ---
@bot.message_handler(commands=['admin'])
def admin_p(message):
    if not is_admin(message.from_user.id): return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ **ADD COUNTRY**", callback_data="adm_add_c"),
        types.InlineKeyboardButton("❌ **DEL COUNTRY**", callback_data="adm_del_c"),
        types.InlineKeyboardButton("💰 **EDIT RATES**", callback_data="adm_rates"),
        types.InlineKeyboardButton("📢 **BROADCAST**", callback_data="adm_bc"),
        types.InlineKeyboardButton("📦 **VIEW STOCK**", callback_data="adm_view_stock"),
        types.InlineKeyboardButton("👤 **TOTAL USERS**", callback_data="adm_users")
    )
    bot.send_message(message.chat.id, "👑 **ADMIN COMMAND CENTER**\n\n**USE COMMANDS:**\n`/addbal ID AMT` | `/cutbal ID AMT`\n`/addadmin ID`", parse_mode="Markdown", reply_markup=markup)

# --- BROADCAST FEATURE ---
@bot.callback_query_handler(func=lambda call: call.data == "adm_bc")
def bc_init(call):
    msg = bot.send_message(call.message.chat.id, "📢 **ENTER MESSAGE TO BROADCAST TO ALL USERS:**")
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    text = message.text
    count = 0
    for uid in db['users'].keys():
        try:
            bot.send_message(uid, f"📢 **IMPORTANT UPDATE:**\n\n{text}", parse_mode="Markdown")
            count += 1
        except: pass
    bot.send_message(message.chat.id, f"✅ **BROADCAST SENT TO {count} USERS!**")

# --- OTHER ADMIN HANDLERS ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('adm_'))
def handle_admin_tools(call):
    uid = call.message.chat.id
    if call.data == "adm_add_c":
        msg = bot.send_message(uid, "🌍 **ENTER COUNTRY NAME:**")
        bot.register_next_step_handler(msg, lambda m: db['sell_rates'].update({m.text.upper(): 20}))
    elif call.data == "adm_rates":
        bot.send_message(uid, "🔧 **USE COMMANDS TO EDIT:**\n`/setsell COUNTRY AMT`\n`/setbuy COUNTRY AMT`")
    elif call.data == "adm_users":
        bot.send_message(uid, f"👤 **TOTAL REGISTERED USERS:** {len(db['users'])}")

# --- SELLING LOGIC (FIXED) ---
@bot.message_handler(func=lambda message: message.text == '📤 **SELL ID**')
def sell_init(message):
    countries = ", ".join(db['sell_rates'].keys())
    msg = bot.send_message(message.chat.id, f"🌍 **AVAILABLE:** `{countries}`\n\n**ENTER COUNTRY NAME:**")
    bot.register_next_step_handler(msg, sell_step_2)

def sell_step_2(message):
    country = message.text.strip().upper()
    if country not in db['sell_rates']: return bot.send_message(message.chat.id, "❌ **COUNTRY NOT SUPPORTED!**")
    msg = bot.send_message(message.chat.id, f"📞 **SEND {country} NUMBER (+...):**")
    bot.register_next_step_handler(msg, sell_step_3, country)

def sell_step_3(message, country):
    phone = message.text.strip()
    bot.send_message(message.chat.id, "⏳ **GETTING OTP...**")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
