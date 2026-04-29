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

db = {
    'users': {}, 
    'admins': [OWNER_ID], 
    'stock': {}, # {'INDIA': ['id1', 'id2']}
    'sell_rates': {'INDIA': 25}, 
    'buy_rates': {'INDIA': 40}
}

def is_admin(uid): return uid in db['admins']

def post_to_logs(text):
    try: bot.send_message(LOG_CHANNEL_ID, f"📢 **SYSTEM UPDATE**\n\n{text}", parse_mode="Markdown")
    except: pass

# --- START MENU ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    args = message.text.split()
    if uid not in db['users']:
        ref_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
        db['users'][uid] = {'balance': 0, 'referred_by': ref_id}
    
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('💰 **BALANCE**', '📥 **DEPOSIT**', '📤 **SELL ID**', '🛒 **BUY ID**', '👥 **REFERRAL**', '📞 **SUPPORT**')
    bot.send_message(message.chat.id, "🔥 **PRIME OTP BOT READY HAI!**", parse_mode="Markdown", reply_markup=markup)

# --- BUYING LOGIC (NEW) ---
@bot.message_handler(func=lambda message: message.text == '🛒 **BUY ID**')
def buy_init(message):
    markup = types.InlineKeyboardMarkup()
    for country in db['buy_rates'].keys():
        markup.add(types.InlineKeyboardButton(f"{country} - ₹{db['buy_rates'][country]}", callback_data=f"buy_{country}"))
    bot.send_message(message.chat.id, "🌍 **KONSI COUNTRY KI ID CHAHIYE?**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def process_buy(call):
    uid = call.from_user.id
    country = call.data.split('_')[1]
    price = db['buy_rates'].get(country, 999)
    user_bal = db['users'][uid].get('balance', 0)

    if user_bal < price:
        return bot.answer_callback_query(call.id, "❌ INSUFFICIENT BALANCE!", show_alert=True)
    
    if not db['stock'].get(country):
        return bot.answer_callback_query(call.id, "❌ STOCK EMPTY FOR THIS COUNTRY!", show_alert=True)

    # Success Buy
    id_data = db['stock'][country].pop(0)
    db['users'][uid]['balance'] -= price
    bot.send_message(uid, f"✅ **PURCHASE SUCCESS!**\n🌍 **COUNTRY:** {country}\n🔐 **ID DATA:** `{id_data}`\n💰 **DEBITED:** ₹{price}")
    post_to_logs(f"🛒 **ID BOUGHT:** {country} by {uid}")
    bot.delete_message(call.message.chat.id, call.message.message_id)

# --- SELLING LOGIC (APPROVAL BASED) ---
@bot.message_handler(func=lambda message: message.text == '📤 **SELL ID**')
def sell_init(message):
    msg = bot.send_message(message.chat.id, "📞 **ID DETAILS BHEJO (NUMBER:OTP YA LOGIN DATA):**")
    bot.register_next_step_handler(msg, sell_req)

def sell_req(message):
    data = message.text
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ APPROVE & PAY", callback_data=f"selapp_{message.from_user.id}_{data}"))
    for adm in db['admins']:
        bot.send_message(adm, f"🔔 **NEW SELL REQ**\nUSER: `{message.from_user.id}`\nDATA: `{data}`", reply_markup=markup)
    bot.send_message(message.chat.id, "⏳ **SENT! ADMIN APPROVE KARTE HI FUND ADD HO JAYEGA.**")

@bot.callback_query_handler(func=lambda call: call.data.startswith('selapp_'))
def approve_sell(call):
    _, uid, data = call.data.split('_', 2)
    uid = int(uid)
    rate = 25 # Default sell rate
    db['users'][uid]['balance'] += rate
    # Stock mein add karo
    if 'INDIA' not in db['stock']: db['stock']['INDIA'] = []
    db['stock']['INDIA'].append(data)
    
    bot.send_message(uid, f"✅ **SELL APPROVED! ₹{rate} ADDED TO YOUR BOT FUND.**")
    bot.edit_message_text("✅ **APPROVED & PAID**", call.message.chat.id, call.message.message_id)

# --- DEPOSIT & ADMIN ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('dapp_'))
def approve_dep(call):
    _, uid, amt = call.data.split('_')
    uid, amt = int(uid), int(amt)
    db['users'][uid]['balance'] += amt
    bot.send_message(uid, f"✅ **₹{amt} DEPOSIT APPROVED!**")
    bot.delete_message(call.message.chat.id, call.message.message_id)

# --- BROADCAST ---
@bot.message_handler(commands=['broadcast'])
def do_bc(message):
    if not is_admin(message.from_user.id): return
    text = message.text.replace('/broadcast', '').strip()
    for u in db['users'].keys():
        try: bot.send_message(u, f"📢 **UPDATE:**\n\n{text}")
        except: pass
    bot.send_message(message.chat.id, "✅ **DONE**")

if __name__ == "__main__":
    keep_alive()
    bot.remove_webhook()
    bot.polling(none_stop=True)
