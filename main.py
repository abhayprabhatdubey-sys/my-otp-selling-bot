import telebot
from telebot import types
from telethon import TelegramClient
import asyncio
import os
from flask import Flask
from threading import Thread

# --- WEB SERVER FOR RENDER ---
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

bot = telebot.TeleBot(TOKEN)

# --- DATABASE ---
db = {
    'users': {}, 
    'admins': [OWNER_ID], 
    'upi': 'abhay-op.315@ptyes',
    'stock': {}, # {'INDIA': [{'phone': '...', 'session': '...'}]}
    'sell_rates': {}, 
    'buy_rates': {},
    'sessions': {} # Temporary login storage
}

# --- MIDDLEWARE ---
def is_owner(uid): return uid == OWNER_ID
def is_admin(uid): return uid in db['admins'] or uid == OWNER_ID

# --- KEYBOARDS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('💰 **BALANCE**', '📥 **DEPOSIT**', '📤 **SELL ID**', '🛒 **BUY ID**', '👥 **REFERRAL**', '📞 **SUPPORT**')
    return markup

# --- START ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if uid not in db['users']:
        db['users'][uid] = {'balance': 0, 'referred_by': None}
    bot.send_message(message.chat.id, "🔥 **PRIME OTP BOT IS ONLINE**", reply_markup=main_menu())

# --- BALANCE ---
@bot.message_handler(func=lambda m: 'BALANCE' in m.text)
def bal_check(message):
    b = db['users'].get(message.from_user.id, {}).get('balance', 0)
    bot.send_message(message.chat.id, f"💳 **YOUR CURRENT BALANCE: ₹{b}**", parse_mode="Markdown")

# --- SUPPORT ---
@bot.message_handler(func=lambda m: 'SUPPORT' in m.text)
def support(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👤 **OWNER**", url="https://t.me/god_abhay"),
               types.InlineKeyboardButton("💬 **JOIN GROUP**", url="https://t.me/Team_quorum"))
    bot.send_message(message.chat.id, "🚩 **CONTACT SUPPORT BELOW:**", reply_markup=markup)

# --- DEPOSIT ---
@bot.message_handler(func=lambda m: 'DEPOSIT' in m.text)
def dep_init(message):
    msg = bot.send_message(message.chat.id, "💵 **ENTER AMOUNT TO DEPOSIT:**")
    bot.register_next_step_handler(msg, dep_step_2)

def dep_step_2(message):
    try:
        amt = int(message.text)
        bot.send_message(message.chat.id, f"💳 **PAY ₹{amt} TO:** `{db['upi']}`\n\n**SEND 12-DIGIT UTR NOW:**")
        bot.register_next_step_handler(message, dep_step_3, amt)
    except: bot.send_message(message.chat.id, "❌ **INVALID AMOUNT!**")

def dep_step_3(message, amt):
    utr = message.text.strip()
    if len(utr) != 12:
        return bot.send_message(message.chat.id, "❌ **REJECTED! UTR MUST BE EXACTLY 12 DIGITS.**")
    msg = bot.send_message(message.chat.id, "📸 **SEND PAYMENT SCREENSHOT:**")
    bot.register_next_step_handler(msg, dep_final, amt, utr)

def dep_final(message, amt, utr):
    if message.content_type != 'photo': return bot.send_message(message.chat.id, "❌ **NO PHOTO RECEIVED!**")
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ **APPROVE**", callback_data=f"d_a_{message.from_user.id}_{amt}"),
               types.InlineKeyboardButton("❌ **REJECT**", callback_data=f"d_r_{message.from_user.id}"))
    for adm in db['admins']:
        bot.send_message(adm, f"🔔 **DEPOSIT REQ**\nUSER: `{message.from_user.id}`\nAMT: ₹{amt}\nUTR: `{utr}`", reply_markup=markup)
        bot.send_photo(adm, message.photo[-1].file_id)
    bot.send_message(message.chat.id, "⏳ **PENDING APPROVAL...**")

# --- BUY ID ---
@bot.message_handler(func=lambda m: 'BUY ID' in m.text)
def buy_menu(message):
    if not db['buy_rates']:
        return bot.send_message(message.chat.id, "❌ **ALL COUNTRIES OUT OF STOCK!**")
    markup = types.InlineKeyboardMarkup()
    for c, p in db['buy_rates'].items():
        count = len(db['stock'].get(c, []))
        btn_text = f"{c} - ₹{p} ({count if count > 0 else 'OUT'})"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"buy_{c}"))
    bot.send_message(message.chat.id, "🛒 **SELECT COUNTRY:**", reply_markup=markup)

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['admin'])
def admin_p(message):
    if not is_admin(message.from_user.id): return
    bot.send_message(message.chat.id, "👑 **ADMIN PANEL**\n\n`/setbuy INDIA 40`\n`/setsell INDIA 25`\n`/addstock INDIA DATA`\n`/changeupi UPI_ID`\n`/addadmin ID`\n`/broadcast MSG`", parse_mode="Markdown")

@bot.message_handler(commands=['addadmin'])
def add_admin(message):
    if is_owner(message.from_user.id):
        try:
            aid = int(message.text.split()[1])
            db['admins'].append(aid)
            bot.reply_to(message, "✅ **ADMIN ADDED**")
        except: pass

@bot.message_handler(commands=['changeupi'])
def change_upi(message):
    if is_admin(message.from_user.id):
        db['upi'] = message.text.split()[1]
        bot.reply_to(message, f"✅ **UPI UPDATED TO:** `{db['upi']}`")

# --- CALLBACK HANDLER (APPROVE/BUY) ---
@bot.callback_query_handler(func=lambda call: True)
def handle_calls(call):
    p = call.data.split('_')
    if p[0] == 'd' and p[1] == 'a': # Deposit Approve
        uid, amt = int(p[2]), int(p[3])
        db['users'][uid]['balance'] += amt
        bot.send_message(uid, f"✅ **₹{amt} CREDITED TO YOUR BALANCE!**")
        bot.edit_message_text("✅ **APPROVED**", call.message.chat.id, call.message.message_id)

    elif p[0] == 'buy':
        country = p[1]
        uid = call.from_user.id
        price = db['buy_rates'].get(country, 9999)
        if db['users'][uid]['balance'] < price or not db['stock'].get(country):
            return bot.answer_callback_query(call.id, "❌ NO BALANCE OR OUT OF STOCK", show_alert=True)
        
        data = db['stock'][country].pop(0)
        db['users'][uid]['balance'] -= price
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 **GET CODE AGAIN**", callback_data=f"get_c_{country}"),
                   types.InlineKeyboardButton("🚪 **LOGOUT SESSION**", callback_data="logout"))
        bot.send_message(uid, f"✅ **PURCHASE SUCCESS!**\n\n🔐 **DATA:** `{data}`", reply_markup=markup)

if __name__ == "__main__":
    keep_alive()
    bot.remove_webhook()
    bot.polling(none_stop=True, skip_pending=True)
