import telebot
from telebot import types
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
import asyncio
import time
import os
from flask import Flask
from threading import Thread

# --- RENDER WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- CONFIGURATION ---
TOKEN = '8692935006:AAFGFN6aeecPubPdd821zq-CmQnZzMtySsw' 
API_ID = 35155488
API_HASH = '9ee6b40363f94481d48dea8a3a871728'
OWNER_ID = 7634311488 # Your ID

bot = telebot.TeleBot(TOKEN)

db = {
    'users': {}, 
    'admins': [OWNER_ID], 
    'stock': [], # [{'phone': '...', 'price': 20}]
    'linked_bots': [] # Sub-bots data
}

def is_admin(uid): return uid in db['admins']

# --- START MENU ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if uid not in db['users']: db['users'][uid] = {'balance': 0}
    
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('💰 **BALANCE**', '📥 **DEPOSIT**')
    markup.add('📤 **SELL ID**', '🛒 **BUY ACCOUNT**')
    markup.add('📞 **SUPPORT**')
    
    bot.send_message(message.chat.id, "🔥 **WELCOME TO PRIME OTP BOT**\n\n**Select an option below to continue:**", 
                     parse_mode="Markdown", reply_markup=markup)

# --- USER FEATURES ---
@bot.message_handler(func=lambda message: message.text == '💰 **BALANCE**')
def check_balance(message):
    bal = db['users'].get(message.from_user.id, {}).get('balance', 0)
    bot.send_message(message.chat.id, f"💳 **YOUR CURRENT BALANCE:**\n\n💰 **₹{bal}**", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == '📞 **SUPPORT**')
def support(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💬 Contact Owner", url="https://t.me/PRIME_OTP_SUPPROT"))
    bot.send_message(message.chat.id, "🚩 **NEED HELP? CONTACT OUR SUPPORT TEAM:**", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '📥 **DEPOSIT**')
def deposit_start(message):
    msg = bot.send_message(message.chat.id, "💵 **ENTER AMOUNT TO DEPOSIT (Min ₹10):**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, deposit_utr)

def deposit_utr(message):
    try:
        amt = int(message.text)
        msg = bot.send_message(message.chat.id, f"💳 **PAY ₹{amt} TO:** `abhay-op.315@ptyes`\n\n**NOW SEND 12-DIGIT UTR NUMBER:**", parse_mode="Markdown")
        bot.register_next_step_handler(msg, deposit_screenshot, amt)
    except: bot.send_message(message.chat.id, "❌ **INVALID AMOUNT!**")

def deposit_screenshot(message, amt):
    utr = message.text.strip()
    if len(utr) != 12:
        return bot.send_message(message.chat.id, "❌ **INVALID UTR! MUST BE 12 DIGITS.**")
    msg = bot.send_message(message.chat.id, "📸 **SEND PAYMENT SCREENSHOT:**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, deposit_to_admin, amt, utr)

def deposit_to_admin(message, amt, utr):
    if message.content_type != 'photo': return bot.send_message(message.chat.id, "❌ **PLEASE SEND A PHOTO!**")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{message.from_user.id}_{amt}"),
               types.InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{message.from_user.id}"))
    
    for adm in db['admins']:
        bot.send_message(adm, f"🔔 **NEW DEPOSIT**\n**User ID:** `{message.from_user.id}`\n**Amount:** ₹{amt}\n**UTR:** `{utr}`", parse_mode="Markdown")
        bot.send_photo(adm, message.photo[-1].file_id, reply_markup=markup)
    bot.send_message(message.chat.id, "⏳ **DEPOSIT PENDING! WAIT FOR ADMIN APPROVAL.**", parse_mode="Markdown")

# --- BUYING & SESSION CONTROL ---
@bot.message_handler(func=lambda message: message.text == '🛒 **BUY ACCOUNT**')
def buy_account(message):
    uid = message.from_user.id
    if not db['stock']: return bot.send_message(message.chat.id, "❌ **STOCK EMPTY!**")
    
    # Simple logic: Sell first item for ₹20
    if db['users'][uid]['balance'] < 20:
        return bot.send_message(message.chat.id, "❌ **INSUFFICIENT BALANCE!**")
    
    db['users'][uid]['balance'] -= 20
    acc = db['stock'].pop(0)
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔄 GET OTP AGAIN", callback_data=f"getotp_{acc}"),
               types.InlineKeyboardButton("🚪 LOGOUT SESSION", callback_data=f"logout_{acc}"))
    
    bot.send_message(message.chat.id, f"✅ **PURCHASE SUCCESS!**\n\n📱 **NUMBER:** `{acc}`\n\n**USE BUTTONS BELOW FOR OTP:**", 
                     parse_mode="Markdown", reply_markup=markup)
    # Notify Admin
    for adm in db['admins']:
        bot.send_message(adm, f"📤 **USER {uid} BOUGHT ID:** `{acc}`")

# --- OWNER & ADMIN COMMANDS ---
@bot.message_handler(commands=['admin'])
def admin_menu(message):
    if not is_admin(message.from_user.id): return
    text = (
        "👑 **ADMIN CONTROL PANEL**\n\n"
        "✨ `/addbal ID Amt` | `/cutbal ID Amt`\n"
        "✨ `/addaccount Number` | `/removeaccount Number`\n"
        "✨ `/addadmin ID` (Owner Only)\n"
        "✨ `/linkbot UPI Token UID` (Setup Sub-bot)"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(commands=['addadmin'])
def add_admin(message):
    if message.from_user.id == OWNER_ID:
        try:
            new_adm = int(message.text.split()[1])
            db['admins'].append(new_adm)
            bot.reply_to(message, f"✅ **{new_adm} IS NOW AN ADMIN!**")
        except: bot.reply_to(message, "Usage: `/addadmin ID`")

@bot.message_handler(commands=['linkbot'])
def link_subbot(message):
    if is_admin(message.from_user.id):
        try:
            # Format: /linkbot UPI TOKEN UID
            _, upi, token, suid = message.text.split()
            db['linked_bots'].append({'upi': upi, 'token': token, 'uid': suid})
            bot.reply_to(message, f"✅ **BOT LINKED SUCCESSFULLY!**")
        except: bot.reply_to(message, "Usage: `/linkbot UPI TOKEN USERID`")

# --- RUN ---
if __name__ == "__main__":
    keep_alive()
    bot.polling(none_stop=True)
