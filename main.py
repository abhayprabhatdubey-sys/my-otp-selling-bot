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
    'users': {}, # {uid: {'balance': 0, 'referred_by': None}}
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

# --- START MENU & REFERRAL LOGIC ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    args = message.text.split()
    
    if uid not in db['users']:
        referred_by = None
        if len(args) > 1 and args[1].isdigit():
            ref_id = int(args[1])
            if ref_id != uid: referred_by = ref_id
        db['users'][uid] = {'balance': 0, 'referred_by': referred_by}

    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('💰 **BALANCE**', '📥 **DEPOSIT**', '📤 **SELL ID**', '🛒 **BUY ACCOUNT**', '👥 **REFERRAL**', '📞 **SUPPORT**')
    
    bot.send_message(message.chat.id, "🔥 **WELCOME TO THE ULTIMATE PRIME OTP BOT**\n\n**SELECT AN OPTION TO START:**", 
                     parse_mode="Markdown", reply_markup=markup)

# --- REFERRAL SYSTEM ---
@bot.message_handler(func=lambda message: message.text == '👥 **REFERRAL**')
def referral_menu(message):
    uid = message.from_user.id
    ref_link = f"https://t.me/{(bot.get_me()).username}?start={uid}"
    text = (
        "👥 **REFER & EARN SYSTEM**\n\n"
        f"🔗 **YOUR LINK:** `{ref_link}`\n\n"
        "✨ **EARN ₹3 FOR EVERY REFERRAL WHO DEPOSITS ₹100 OR MORE!**"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# --- ADMIN SUPREME PANEL ---
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
    bot.send_message(message.chat.id, "👑 **OWNER CONTROL PANEL**\n\n**MANUAL COMMANDS:**\n`/addbal ID AMT` | `/addadmin ID`", 
                     parse_mode="Markdown", reply_markup=markup)

# --- DEPOSIT WITH REFERRAL BONUS ---
@bot.message_handler(func=lambda message: message.text == '📥 **DEPOSIT**')
def dep_init(message):
    msg = bot.send_message(message.chat.id, "💵 **ENTER AMOUNT TO DEPOSIT:**")
    bot.register_next_step_handler(msg, dep_step_2)

def dep_step_2(message):
    try:
        amt = int(message.text)
        msg = bot.send_message(message.chat.id, f"💳 **PAY ₹{amt} TO:** `abhay-op.315@ptyes`\n\n**SEND 12-DIGIT UTR:**")
        bot.register_next_step_handler(msg, dep_step_3, amt)
    except: bot.send_message(message.chat.id, "❌ **INVALID AMOUNT!**")

def dep_step_3(message, amt):
    utr = message.text.strip()
    if len(utr) != 12: return bot.send_message(message.chat.id, "❌ **INVALID UTR!**")
    msg = bot.send_message(message.chat.id, "📸 **SEND PAYMENT SCREENSHOT:**")
    bot.register_next_step_handler(msg, dep_final, amt, utr)

def dep_final(message, amt, utr):
    if message.content_type != 'photo': return bot.send_message(message.chat.id, "❌ **SEND PHOTO!**")
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ **APPROVE**", callback_data=f"dapp_{message.from_user.id}_{amt}"))
    for adm in db['admins']:
        bot.send_message(adm, f"🔔 **DEPOSIT REQ**\nUSER: `{message.from_user.id}`\nAMT: ₹{amt}\nUTR: `{utr}`", reply_markup=markup)
        bot.send_photo(adm, message.photo[-1].file_id)
    bot.send_message(message.chat.id, "⏳ **DEPOSIT PENDING APPROVAL!**")

# --- CALLBACK HANDLERS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    p = call.data.split('_')
    
    if p[0] == 'dapp':
        uid, amt = int(p[1]), int(p[2])
        db['users'][uid]['balance'] += amt
        
        # Referral Bonus Logic
        ref_by = db['users'][uid].get('referred_by')
        if ref_by and amt >= 100:
            db['users'][ref_by]['balance'] += 3
            bot.send_message(ref_by, f"🎁 **REFERRAL BONUS! YOU EARNED ₹3 FROM USER {uid}**")
        
        bot.send_message(uid, f"✅ **DEPOSIT OF ₹{amt} APPROVED!**")
        post_to_logs(f"💰 **DEPOSIT SUCCESS**\n**USER:** {uid}\n**AMOUNT:** ₹{amt}")
        bot.edit_message_text("✅ **DEPOSIT APPROVED**", call.message.chat.id, call.message.message_id)

    elif p[0] == 'adm':
        if p[1] == 'bc':
            msg = bot.send_message(call.message.chat.id, "📢 **ENTER BROADCAST MESSAGE:**")
            bot.register_next_step_handler(msg, process_bc)
        elif p[1] == 'users':
            bot.send_message(call.message.chat.id, f"👤 **TOTAL USERS:** {len(db['users'])}")

def process_bc(message):
    for u in db['users'].keys():
        try: bot.send_message(u, f"📢 **IMPORTANT:**\n\n{message.text}", parse_mode="Markdown")
    except: pass
    bot.send_message(message.chat.id, "✅ **BROADCAST DONE!**")

# --- USER OPTIONS ---
@bot.message_handler(func=lambda message: message.text == '💰 **BALANCE**')
def bal(message):
    b = db['users'].get(message.from_user.id, {}).get('balance', 0)
    bot.send_message(message.chat.id, f"💳 **YOUR BALANCE: ₹{b}**", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == '📞 **SUPPORT**')
def support(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👤 **OWNER**", url="https://t.me/god_abhay"),
               types.InlineKeyboardButton("💬 **JOIN GC**", url="https://t.me/Team_quorum"))
    bot.send_message(message.chat.id, "🚩 **SUPPORT CHANNELS:**", reply_markup=markup)

if __name__ == "__main__":
    keep_alive()
    bot.polling(none_stop=True, interval=0, timeout=20)
