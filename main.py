import telebot
from telebot import types
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
import asyncio
import time

# --- CONFIGURATION ---
API_ID = 35155488
API_HASH = '9ee6b40363f94481d48dea8a3a871728'
BOT_TOKEN = '8692935006:AAF3uUPWZbd9f4NuiUZPbWYycUDrfsEY1tQ'

# --- MULTI-ADMIN SYSTEM ---
# Yahan tum aur apne dosto ki ID add kar sakte ho
ADMIN_IDS = [7634311488] 

# --- FORCE JOIN CONFIG ---
CHANNEL_USERNAME = "@PRIME_OTP_STORE" # Apne channel ka username dalo (बिना @ के भी चलेगा)
CHANNEL_LINK = "https://t.me/PRIME_OTP_STORE" # Channel ka link

bot = telebot.TeleBot(BOT_TOKEN)
user_sessions = {}
db = {'users': {}} # Database

# --- DETAILS ---
UPI_ID = "abhay-op.315@ptyes"
SUPPORT = "@PRIME_OTP_SUPPROT"

# --- FORCE JOIN CHECK ---
def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(f"@{CHANNEL_USERNAME.replace('@','')}", user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return True # Agar bot admin nahi hai channel mein toh check skip karega

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    
    # Force Join Check
    if not is_subscribed(uid):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK))
        markup.add(types.InlineKeyboardButton("✅ I have Joined", callback_data="check_join"))
        return bot.send_message(message.chat.id, f"Bhai, pehle hamare channel ko join karo tabhi bot chalega!", reply_markup=markup)

    if uid not in db['users']: db['users'][uid] = {'balance': 0}
    
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1, btn2 = types.KeyboardButton('📲 Start Login'), types.KeyboardButton('💰 Balance')
    btn3, btn4 = types.KeyboardButton('📥 Deposit'), types.KeyboardButton('📞 Support')
    markup.add(btn1, btn2, btn3, btn4)
    bot.send_message(message.chat.id, f"Welcome! Prime OTP Bot is Live 🚀", reply_markup=markup)

# --- ADVANCED DEPOSIT SYSTEM ---
@bot.message_handler(func=lambda message: message.text == '📥 Deposit')
def deposit_step1(message):
    msg = bot.send_message(message.chat.id, "💰 Kitna amount deposit karna hai? (Sirf number likho, e.g. 100)")
    bot.register_next_step_handler(msg, deposit_step2)

def deposit_step2(message):
    try:
        amount = int(message.text)
        text = f"💳 *Payment Details:*\n\nAmount: {amount} INR\nUPI ID: `{UPI_ID}`\n\n👉 Payment karne ke baad uska **UTR Number** yahan bhejein:"
        msg = bot.send_message(message.chat.id, text, parse_mode="Markdown")
        bot.register_next_step_handler(msg, deposit_step3, amount)
    except:
        bot.send_message(message.chat.id, "❌ Galat amount! Phir se Deposit par click karein.")

def deposit_step3(message, amount):
    utr = message.text
    msg = bot.send_message(message.chat.id, "📸 Ab payment ka Screenshot bhejein:")
    bot.register_next_step_handler(msg, deposit_final, amount, utr)

def deposit_final(message, amount, utr):
    if message.content_type == 'photo':
        # Admin ko details bhejna
        for admin in ADMIN_IDS:
            bot.send_message(admin, f"🔔 *Naya Deposit Request!*\n\nUser: {message.from_user.id}\nAmount: {amount}\nUTR: {utr}")
            bot.forward_message(admin, message.chat.id, message.message_id)
        bot.send_message(message.chat.id, "✅ Details submit ho gayi hain! Admin verify karke 5-10 min mein balance add kar dega.")
    else:
        bot.send_message(message.chat.id, "❌ Screenshot nahi mila! Phir se koshish karein.")

# --- MULTI-ADMIN COMMANDS ---
@bot.message_handler(commands=['addbal'])
def add_balance(message):
    if message.from_user.id in ADMIN_IDS:
        try:
            _, target_id, amt = message.text.split()
            target_id, amt = int(target_id), int(amt)
            if target_id not in db['users']: db['users'][target_id] = {'balance': 0}
            db['users'][target_id]['balance'] += amt
            bot.send_message(target_id, f"✅ Admin ne aapke account mein {amt} INR add kar diye hain!")
            bot.reply_to(message, "Done!")
        except:
            bot.reply_to(message, "Usage: `/addbal ID Amount`")

# --- LOGIN & 2FA SYSTEM (Same as before) ---
@bot.message_handler(func=lambda message: message.text == '📲 Start Login')
def login_start(message):
    msg = bot.send_message(message.chat.id, "📞 Apna Number bhejein (With Country Code):")
    bot.register_next_step_handler(msg, process_number)

# ... (process_number, process_otp, process_2fa functions carry forward here)
# Copy remaining Telethon logic from previous script to handle OTP/2FA

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_callback(call):
    if is_subscribed(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Thank you! Ab aap bot use kar sakte hain.")
        start(call.message)
    else:
        bot.answer_callback_query(call.id, "❌ Abhi tak join nahi kiya!", show_alert=True)

bot.polling(none_stop=True)
